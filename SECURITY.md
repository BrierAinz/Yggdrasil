# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 4.x     | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

We take security seriously. If you discover a vulnerability in Yggdrasil or any of its components, please report it responsibly.

**Do NOT open a public GitHub issue for security vulnerabilities.**

Instead, please:

1. **Email**: Send details to the repository owner via GitHub's private vulnerability reporting feature
2. **GitHub Security Advisory**: Use the [Security Advisories](https://github.com/BrierAinz/Yggdrasil/security/advisories/new) page
3. **Include the following**:
   - Type of vulnerability (XSS, injection, data exposure, etc.)
   - Full path or URL of the affected component
   - Steps to reproduce
   - Potential impact
   - Any suggested mitigations

## Response Timeline

- **Acknowledgment**: Within 48 hours
- **Initial assessment**: Within 7 days
- **Fix or mitigation**: Within 30 days (dependent on severity)
- **Public disclosure**: After a fix is released

## Security Considerations

Since Yggdrasil includes a Telegram bot and local AI agent:

- **Never commit API keys, tokens, or `.env` files** — they are gitignored by default
- **The Telegram bot owner check must remain active** — only the configured chat ID can issue commands
- **LM Studio connections are local-only** by design (`localhost:1234`)
- **Vector memory databases** may contain conversation data — handle with care
- **The Gateway API** should not be exposed to the public internet without authentication

Thank you for helping keep Yggdrasil and its users safe.
