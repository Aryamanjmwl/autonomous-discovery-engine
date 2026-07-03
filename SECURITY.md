# Security Policy

ADE is currently a local research and engineering project. It does not provide hosted authentication, authorization, tenant isolation, or compliance guarantees.

## Reporting Security Issues

Do not open public issues for suspected vulnerabilities involving private datasets, credentials, or deployment details. Use a private communication channel with the repository owner.

## Data Handling

Do not commit:

- Private datasets
- Secrets or credentials
- Generated reports from sensitive data
- Run metadata from sensitive data
- Proprietary model outputs

## Current Scope

The current implementation reads local input folders and writes local reports. It does not upload data or call remote model APIs.

## Compliance

ADE does not currently claim SOC 2, HIPAA, GDPR, or other compliance status.
