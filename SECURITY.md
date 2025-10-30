# Security Policy

## Security Status: ✅ SECURE

Last security audit: October 30, 2025

## What's Protected

### Credentials NOT in Repository ✅
The following sensitive files are properly excluded via `.gitignore`:
- `config.json` - Contains all API keys, passwords, and tokens
- `.env` - Environment variables
- `*.log` - Log files (may contain data)
- `detected_aircraft.txt` - Detection history
- `emergency_events.json` - Emergency event logs

### What IS in Repository ✅
- `config.example.json` - Template with placeholder values
- Source code (no hardcoded credentials)
- Documentation
- Aircraft database (public information)

## Security Scan Results

```
✅ config.json: NOT tracked in git
✅ Credential patterns: NONE found in tracked files
✅ .gitignore: Properly configured
✅ config.example.json: Only contains placeholders
```

## Required Credentials

FlightTrak requires the following credentials (stored locally in `config.json`):

### Required
1. **Gmail SMTP** (`email_config.password`)
   - Gmail app password (not regular password)
   - Requires 2FA enabled on account
   - Generate at: https://myaccount.google.com/apppasswords

### Optional
2. **FlightAware API** (`flightaware_config.flightaware_api_key`)
   - Free tier available
   - Enriches alerts with flight plan data

3. **Twitter/X API** (if using Twitter integration)
   - `api_key`, `api_secret`, `access_token`, `access_secret`, `bearer_token`
   - Required for automated posting

4. **Intelligence APIs** (if using enhanced features)
   - NewsAPI, Mapbox, HERE Maps, What3Words
   - All optional

## Setup Instructions

### First-Time Setup

1. **Copy example config**:
   ```bash
   cp config.example.json config.json
   ```

2. **Edit config.json** with your credentials:
   ```bash
   nano config.json  # or your preferred editor
   ```

3. **Verify .gitignore**:
   ```bash
   cat .gitignore | grep config.json
   # Should show: config.json
   ```

4. **Test before committing**:
   ```bash
   git status
   # config.json should appear under "Untracked files" NOT "Changes to be committed"
   ```

### Best Practices

✅ **DO**:
- Keep config.json local only
- Use environment variables for production
- Rotate credentials periodically
- Use app-specific passwords (Gmail)
- Review .gitignore before commits

❌ **DON'T**:
- Commit config.json to git
- Share config.json via email/chat
- Use regular passwords (use app passwords)
- Hardcode credentials in source code
- Push credentials to public repos

## Exposed Information

### Public Information (Intentionally Shared)
The following information is public and safe to share:
- Aircraft ICAO codes (public ADS-B data)
- Aircraft owners/descriptions (public information)
- Home coordinates (in config.example.json as example)
- System architecture and code

### Private Information (Keep Secret)
- API keys and tokens
- Email passwords/app passwords
- Specific alert recipients
- Your actual home coordinates (in config.json)

## If Credentials Are Exposed

If you accidentally commit credentials to git:

### Immediate Actions
1. **Rotate ALL exposed credentials immediately**
   - Gmail: Generate new app password
   - APIs: Generate new keys
   - Twitter: Regenerate tokens

2. **Remove from git history**:
   ```bash
   # Remove config.json from all history
   git filter-branch --force --index-filter \
     "git rm --cached --ignore-unmatch config.json" \
     --prune-empty --tag-name-filter cat -- --all

   # Force push (WARNING: rewrites history)
   git push origin --force --all
   ```

3. **Verify removal**:
   ```bash
   git log --all --full-history -- config.json
   # Should return nothing
   ```

4. **Update .gitignore if needed**:
   ```bash
   echo "config.json" >> .gitignore
   git add .gitignore
   git commit -m "Ensure config.json is ignored"
   ```

## Security Monitoring

### Regular Checks
- Review git status before commits
- Scan for credential patterns periodically
- Check .gitignore is working
- Audit API key usage

### Automated Scanning
Run the security scan script:
```bash
./security_scan.sh
```

Expected output:
```
✅ SAFE: config.json is NOT tracked
✅ SAFE: No credential patterns found in tracked files
✅ SAFE: config.json is in .gitignore
```

## Reporting Security Issues

If you find a security issue:
1. **DO NOT** open a public GitHub issue
2. Contact repository owner directly
3. Provide details about the vulnerability
4. Allow time for remediation before disclosure

## Security Checklist

Before pushing to GitHub:
- [ ] Run `git status` and verify config.json is NOT staged
- [ ] Check `git diff --cached` doesn't show credentials
- [ ] Run `./security_scan.sh` and verify all checks pass
- [ ] Review commit message doesn't contain credentials
- [ ] Verify .gitignore includes config.json

## Additional Resources

- [GitHub's guide to removing sensitive data](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)
- [Git-secrets tool](https://github.com/awslabs/git-secrets)
- [Gmail App Passwords](https://support.google.com/accounts/answer/185833)

---

**Last Updated**: October 30, 2025
**Security Audit**: PASS ✅
**Credentials Exposed**: NONE ✅
