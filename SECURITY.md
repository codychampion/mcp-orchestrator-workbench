# Security Policy

## Reporting security issues

Do not open public issues for suspected secrets, credentials, private endpoints, or deployment vulnerabilities.

Report sensitive findings privately to the repository owner.

## Handling secrets

This project expects provider keys and deployment credentials to come from local environment variables or platform secret stores.

- Do not commit `.env` files, access tokens, API keys, tenant-specific credentials, or cloud service connection secrets.
- Use mock mode for local development when model credentials are not available.
- Review deployment templates for environment-specific values before adapting them.
