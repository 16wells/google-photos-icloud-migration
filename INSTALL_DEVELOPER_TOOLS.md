# Installing Developer Tools on macOS

The migration script requires Xcode Command Line Tools, which provide essential development tools like `git`, compilers, and other utilities needed for Python packages.

## Quick Install

Open Terminal and run:

```bash
xcode-select --install
```

This will show a popup window. Click **"Install"** and wait for the installation to complete (typically 5-10 minutes).

## Verify Installation

After installation completes, verify it worked:

```bash
xcode-select -p
```

You should see a path like `/Library/Developer/CommandLineTools` or `/Applications/Xcode.app/Contents/Developer`.

## What Gets Installed

Xcode Command Line Tools includes:
- `git` - Version control (needed for cloning the repo)
- `gcc` / `clang` - Compilers (needed for some Python packages)
- `make` - Build tool
- `python3` - Python interpreter (though we'll install via Homebrew for latest version)
- Other essential development utilities

## Alternative: Full Xcode (Not Required)

You can install the full Xcode app from the App Store, but it's **not necessary** for this migration. The Command Line Tools are sufficient and much smaller (~500MB vs ~10GB).

## Troubleshooting

### Installation Stuck or Failed

1. **Check internet connection** - Installation downloads from Apple's servers
2. **Try again** - Sometimes the first attempt fails, just run `xcode-select --install` again
3. **Manual download** - Visit [developer.apple.com](https://developer.apple.com/download/all/) and download Command Line Tools manually

### "Can't install the software because it is not currently available"

This usually means:
- Apple's servers are temporarily unavailable
- Your macOS version is too old
- Network/firewall issues

**Solution:** Wait a bit and try again, or download manually from Apple Developer site.

### Already Installed?

If you see:
```
xcode-select: error: command line tools are already installed
```

You're all set! No need to install again.

## After Installation

Once Command Line Tools are installed, you can proceed with:

1. **Installing Homebrew** (if needed)
2. **Running the setup script**: `./setup-macbook.sh`

The setup script will check for Command Line Tools and prompt you to install if missing.

## Why This Is Needed

Some Python packages (like `pyicloud` dependencies) may need to compile native extensions, which requires the compilers provided by Command Line Tools. Even if not strictly required for this project, it's good practice to have them installed on any development machine.

