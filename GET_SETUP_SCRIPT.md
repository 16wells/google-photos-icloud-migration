# Getting the Setup Script

The `setup-macbook.sh` script has been added to the repository. If you already cloned the repo, you need to pull the latest changes.

## Option 1: Pull Latest Changes (If Already Cloned)

On the new MacBook, in the repository directory:

```bash
cd ~/google-photos-icloud-migration
git pull origin main
```

Then you can run:
```bash
chmod +x setup-macbook.sh
./setup-macbook.sh
```

## Option 2: Re-clone the Repository

If you prefer to start fresh:

```bash
cd ~
rm -rf google-photos-icloud-migration  # Remove old clone if exists
git clone https://github.com/16wells/google-photos-icloud-migration.git
cd google-photos-icloud-migration
chmod +x setup-macbook.sh
./setup-macbook.sh
```

## Verify the Script Exists

After pulling, verify the file is there:

```bash
ls -la setup-macbook.sh
```

You should see:
```
-rwxr-xr-x  1 user  staff  2963 Nov 25 22:52 setup-macbook.sh
```

## Quick Commands

```bash
# Navigate to repo
cd ~/google-photos-icloud-migration

# Pull latest changes
git pull

# Make script executable (if needed)
chmod +x setup-macbook.sh

# Run the setup
./setup-macbook.sh
```

## Troubleshooting

### "fatal: not a git repository"

You're not in the repository directory. Make sure you're in the cloned repo:
```bash
cd ~/google-photos-icloud-migration
```

### "Already up to date"

The repo is already up to date. Try:
```bash
git pull origin main
```

Or check if the file exists:
```bash
ls -la setup-macbook.sh
```

### "Permission denied"

Make the script executable:
```bash
chmod +x setup-macbook.sh
```


