## Reporting a Vulnerability

If you find a security issue, please **do not** open a public issue with sensitive details.

- **Preferred**: Open a private GitHub Security Advisory (Security → Advisories → “Report a vulnerability”).
- If that’s not available, open a GitHub issue with a high-level description and ask for a private channel.

## Security Model (What this tool can access)

- **Google Drive**: OAuth 2.0 with scope `drive.readonly` (downloads Takeout zips).
- **macOS Photos / iCloud Photos**:
  - Recommended method uses **PhotoKit** (writes to local Photos library; macOS sync handles iCloud).
  - Alternative API method uses `pyicloud` (less reliable; relies on cookies/session).

## Secrets and Sensitive Files

Never commit these:

- **`credentials.json`**: Contains an OAuth **client secret** (treat as sensitive).
- **`token.json`**: Contains OAuth access/refresh tokens (treat as sensitive).
- **`.env`**: Environment secrets (Apple ID password, GitHub token, etc.).
- **`config.yaml`**: May include personal paths/IDs; keep it private.
- **Logs**: May contain PII (paths, filenames, Apple ID email).

This repo’s `.gitignore` is configured to ignore common secret/log files. If you ever accidentally commit one:

1. Remove from git history (e.g. `git filter-repo`), and
2. Rotate/revoke the credential (Google OAuth client / refresh token / GitHub PAT).

## Recommended Safe Operating Practices

- **Run on a dedicated macOS user** (or temporary user) when migrating large libraries.
- **Use a dedicated Photos library** (optionally on external SSD) for safer rollback.
- **Prefer PhotoKit (`--use-sync`)** to avoid storing Apple passwords in configs.
- **Keep tokens on disk with restrictive permissions**.

## Dependency / Supply Chain Recommendations

This project currently uses version ranges in `requirements.txt` (e.g. `package>=x.y`).

For stronger supply-chain hygiene:

- **Generate a lock file** (e.g. `pip-tools` → `requirements.lock.txt`) for reproducible builds.
- **Use `pip-audit`** to scan for known vulnerabilities:
  ```bash
  pip install pip-audit
  pip-audit -r requirements.txt
  ```
- **Enable GitHub Dependabot** to receive automated security alerts.
- **Prefer virtual environments** and avoid running as root.
- **Keep dependencies updated** but test changes before deploying to production.

## Security Best Practices

### Token Storage
- OAuth tokens are stored in `~/.config/google-photos-icloud-migration/token.json` (default) with permissions 0600.
- Legacy `token.json` in project directory is supported but less secure.
- Never commit token files to git (already in `.gitignore`).

### File Permissions
- Token files: 0600 (owner read/write only)
- Config directory: 0700 (owner access only)
- Extracted/processed files: Use default umask (typically 0644/0755)

### Logging
- No passwords, tokens, or secrets are logged.
- Log files may contain file paths and Apple ID email addresses.
- Log files are gitignored but keep them private in production.

### Path Security
- All file paths are validated to prevent traversal attacks.
- Zip slip protection is implemented in the extractor.
- Subprocess calls use list arguments (no shell=True) to prevent injection.


