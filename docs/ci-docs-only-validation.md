# CI Documentation-Only Validation

This document validates NovaCart Phase 6 documentation-only
change detection.

Validation objectives:
- Confirm the historical full-CI baseline is SCM-verified.
- Confirm a documentation-only commit is classified correctly.
- Keep Docker builds, Trivy scans, GHCR publishing and GitOps enabled.

This test does not enable CI stage skipping.
