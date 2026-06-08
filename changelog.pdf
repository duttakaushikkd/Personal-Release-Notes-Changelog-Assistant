# Product Changelog

## Version 3.2.0 (March 15, 2026)
### Added
- Added support for AWS OpenSearch serverless connections.
- Introduced `pyproject.toml` native dependency management for the CLI plugin.

## Version 3.1.0 (January 10, 2026)
### Changed
- Refactored backend authentication flow to use OAuth2 by default.
### Breaking Changes
- The old `v1/auth/login` endpoint is now deprecated and will return a 410 Gone status. Developers must migrate to `v2/tokens`.
- The configuration variable `AUTH_SECRET_KEY` has been renamed to `SECURITY_JWT_SECRET`.

## Version 3.0.0 (November 05, 2025)
### Major Release
- Complete rewrite of the database indexing layer.
### Breaking Changes
- Removed native support for Python 3.8. The minimum required version is now Python 3.10.
