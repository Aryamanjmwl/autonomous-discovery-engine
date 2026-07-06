# Enterprise Readiness

ADE is not enterprise-ready today. This document records the requirements that would make it suitable for enterprise deployment later.

## Required Capabilities

- Stable API service
- Dataset registry
- Persistent storage
- Job queue
- User, team, and project model
- RBAC
- API keys
- SSO/OIDC
- Audit logs
- Usage limits
- Billing hooks
- Monitoring
- Backup and restore
- Retention policies
- Object storage
- PostgreSQL
- Deployment templates

## Current Status

The current implementation is a local visual-data-first engine. It writes local reports and run metadata. It does not provide user accounts, hosted uploads, RBAC, audit guarantees, or production compliance controls.

## Explicit Non-Claims

- No SOC 2 claim.
- No HIPAA claim.
- No regulated medical diagnosis support.
- No financial advice support.
- No production security certification.
