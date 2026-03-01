# Security Policy

## Supported Versions

Only the latest release is supported with security updates. Please ensure
you are running the most recent version before reporting a vulnerability.

## Reporting a Vulnerability

**Do not open a public issue for security vulnerabilities.**

Instead, please use
[GitHub Private Security Advisories](https://github.com/antoinededaran/rag_bible/security/advisories/new)
to report vulnerabilities.

### What to include

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to expect

- **Acknowledgment** within 7 days of your report.
- We will work with you to understand and validate the issue.
- A fix will be developed privately and released as a patch.
- You will be credited in the release notes (unless you prefer otherwise).

### Scope

The following are in scope:

- The FastAPI backend (`app.py`, `rag/` package)
- Dependencies with known CVEs that affect this project
- Data injection or query manipulation via the `/search` endpoint

The following are **out of scope**:

- The static frontend (HTML/CSS/JS served as-is, no user-generated content)
- Self-hosted deployment misconfigurations
- Denial-of-service attacks against local/development instances

## Preferred Languages

We accept vulnerability reports in English or French.
