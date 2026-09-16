# Demo Repository - Project Doctor Test Codebase

> **DEMO ONLY**: This repository contains deliberate, pedagogical code defects to demonstrate and evaluate the full diagnostic capabilities of **Project Doctor**.
> Do NOT use this code in production systems.

### Detected Defect Profile
- **Security**: Hardcoded AWS credentials, SQL injection vulnerability, dynamic code evaluation (`eval`), insecure MD5 hashing.
- **Code Quality**: High cyclomatic complexity (`M > 10`), long function (`> 50 lines`), duplicate code patterns, unhandled TODO comments.
- **Dependencies**: Outdated/vulnerable packages (`flask==0.12.0`, `requests==2.18.4`).
- **Architecture**: Multi-tier architecture (Presentation, Service, Data) with intentional circular dependency cycle between `auth_service` and `user_service`.
