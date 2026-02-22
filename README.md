# zig-updater

## Installation

You can download `zig_updater.py` using `wget` or `curl`. We recommend saving the file as `zig_updater.py` in your home directory:

```bash
# Using wget
wget -O ~/zig_updater.py https://github.com/pw4ch7re3/zig-updater/blob/main/zig_updater.py?raw=true

# Using curl
curl -L -o ~/zig_updater.py https://github.com/pw4ch7re3/zig-updater/blob/main/zig_updater.py?raw=true
```

## Recommendation

To use the updater conveniently, add the following lines to your ~/.bashrc. This creates a wrapper that handles zig update separately while passing all other commands to the actual Zig binary:

```bash
export PATH="$HOME/zig/bin:$PATH"

# Zig Wrapper Function
zig() {
    if [ "$1" = "update" ]; then
        # Drop the "update" argument and pass the rest to the Python script
        shift
        python3 ~/zig_updater.py "$@"
    else
        # Run the actual zig binary for all other commands
        command zig "$@"
    fi
}
```

Don't forget to run source ~/.bashrc to apply the changes.

# References

[1] https://ziggit.dev/t/update-your-zig-installation-automatically-to-the-newest-master-version-python-3-x-needed/963
