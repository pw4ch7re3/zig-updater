import sys
import shutil
import tarfile
import zipfile
import platform
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

import requests

# Constants
ZIG_URL = 'https://ziglang.org/download/index.json'
DEFAULT_ZIG_DIR = Path('~/zig/').expanduser()
DEFAULT_CACHE_DIR = Path('~/.zig-cache/').expanduser()

logger = logging.getLogger("zig_updater")

def setup_logging(log_file: Path):
    """Set up logging to both console and a file."""
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def get_os_arch() -> str:
    """Normalize OS and Architecture to match Zig's JSON keys."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == 'darwin':
        system = 'macos'
    
    if machine in ('amd64', 'x86_64'):
        machine = 'x86_64'
    elif machine in ('arm64', 'aarch64'):
        machine = 'aarch64'

    return f"{machine}-{system}"

def get_zig_data() -> dict:
    """Fetch the latest release JSON from Zig."""
    try:
        response = requests.get(ZIG_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch Zig release data: {e}")
        sys.exit(1)

def get_current_version(bin_dir: Path) -> str | None:
    """Check the installed version of Zig directly from the target folder."""
    zig_exe = bin_dir / ('zig.exe' if platform.system().lower() == 'windows' else 'zig')
    
    if not zig_exe.exists():
        return None # First time install!

    try:
        result = subprocess.run(
            [str(zig_exe), "version"], capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None

def extract_archive(archive_path: Path, dest_dir: Path):
    """Safely extract either .zip or .tar.xz/.tar.gz archives."""
    if archive_path.suffix == '.zip':
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
    else:
        with tarfile.open(archive_path, 'r:*') as tar_ref:
            if hasattr(tarfile, 'data_filter'):
                tar_ref.extractall(dest_dir, filter='data')
            else:
                tar_ref.extractall(dest_dir)

def update_zig(mode: str, zig_dir: Path, backup_dir: Path):
    """Main update logic."""
    logger.info("Checking for Zig updates...")
    
    # Ensure our base directories exist right away
    zig_dir.mkdir(parents=True, exist_ok=True)
    backup_dir.mkdir(parents=True, exist_ok=True)

    data = get_zig_data()
    os_arch = get_os_arch()

    if mode == 'master':
        target_info = data.get('master')
    else:
        stable_versions = [k for k in data.keys() if k != 'master']
        version_key = stable_versions[0] if mode == 'latest' else mode
        target_info = data.get(version_key)

    if not target_info or os_arch not in target_info:
        logger.error(f"Failed to find a Zig release for {mode} on {os_arch}")
        sys.exit(1)

    target_version = target_info['version']
    bin_dir = zig_dir / 'bin'
    current_version = get_current_version(bin_dir)

    if current_version == target_version:
        logger.info(f"Zig is already up to date (Version: {target_version}).")
        return

    logger.info(f"Updating Zig: {current_version or 'Not Installed'} -> {target_version}...")

    # Backup existing installation if it exists
    if bin_dir.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        current_backup_dir = backup_dir / timestamp
        shutil.copytree(bin_dir, current_backup_dir)
        logger.info(f"Backed up current installation to {current_backup_dir}")

    # Download
    url = target_info[os_arch]['tarball']
    filename = url.split('/')[-1]
    archive_path = zig_dir / filename

    logger.info(f"Downloading {filename}...")
    with requests.get(url, stream=True, timeout=30) as response:
        response.raise_for_status()
        with open(archive_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)

    # Extract
    logger.info("Extracting archive...")
    extract_archive(archive_path, zig_dir)

    # Find the extracted directory name
    extracted_dir_name = filename
    for suffix in ['.tar.xz', '.tar.gz', '.zip', '.tar']:
        extracted_dir_name = extracted_dir_name.replace(suffix, '')
    
    extracted_dir = zig_dir / extracted_dir_name

    # Replace bin directory
    if bin_dir.exists():
        shutil.rmtree(bin_dir)
    extracted_dir.rename(bin_dir)

    # Cleanup
    if archive_path.exists():
        archive_path.unlink()
        
    logger.info("Installation complete!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="A tool to install and update the Zig compiler.")
    parser.add_argument("--mode", default="latest", help="Version to install: 'latest', 'master', or a specific version.")
    parser.add_argument("--dir", type=Path, default=DEFAULT_ZIG_DIR, help="Installation directory.")
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE_DIR, help="Cache directory.")
    
    args = parser.parse_args()

    args.dir = args.dir.expanduser()
    args.backup_dir = args.backup_dir.expanduser()

    setup_logging(args.dir / 'zig_updater.log')
    update_zig(args.mode, args.dir, args.backup_dir)
