# Security Model

ADE is currently a local research and engineering project. It does not provide hosted authentication, authorization, tenant isolation, or compliance controls.

## Current Local Model

- Users provide local input folders.
- ADE reads supported files from the configured input folder.
- ADE writes local reports, assets, run metadata, and run index files.
- ADE does not upload data.
- ADE does not call remote model APIs.

## Future Hosted Model

A hosted ADE deployment would require:

- Authentication
- Authorization
- Project and workspace isolation
- Object storage access controls
- Audit logs
- API keys
- Rate limits
- Secret management
- Retention policies
- Backup and restore

## Data Handling Guidance

Do not commit private datasets, generated reports from sensitive data, secrets, credentials, or proprietary model outputs.

Do not claim compliance with SOC 2, HIPAA, GDPR, or other regimes until the system has been designed, implemented, and reviewed for those requirements.
