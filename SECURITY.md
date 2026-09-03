# Security Policy

## Reporting a vulnerability

Do not report security vulnerabilities in public issues.

Please contact the repository maintainer privately with:

- a concise description of the issue;
- the affected component or endpoint;
- reproduction steps or a proof of concept; and
- the likely impact.

Do not include live tokens, credentials, or other secrets in a report. Revoke any credential that may have been exposed before reporting it.

## Deployment basics

- Keep `infra/.env` outside Git and restrict its permissions.
- Set a strong `TV_WEBHOOK_SECRET` before exposing the webhook endpoint.
- Put the service behind HTTPS and an appropriate reverse proxy.
- Do not expose SQLite, Docker, or internal service ports publicly.
