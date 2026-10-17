# NovaCart Frontend OpenTelemetry Security Hardening — Phase 5

**Completed:** 2026-10-17
**Status:** Completed and runtime-verified
**Repository:** `dgsuma/NovaCart`
**Pull request:** [#19](https://github.com/dgsuma/NovaCart/pull/19)

## 1. Summary

Phase 5 remediated four HIGH-severity OpenTelemetry dependency findings in the NovaCart frontend while preserving application functionality and distributed tracing.

The remediation updated compatible OpenTelemetry packages and their transitive dependencies without changing frontend application code, Kubernetes manifests, or Jenkins security policy.

## 2. Source Changes

- Feature branch: `security/frontend-opentelemetry`
- Remediation commit: `026cc05d`
- Main merge commit: `0c935f4566ec6be89fff57cf19a2d7851ed0cc32`
- Files modified:
  - `src/frontend/package.json`
  - `src/frontend/package-lock.json`

The OpenTelemetry dependency family was aligned to compatible versions, including:

| Package | Version |
|---|---|
| OpenTelemetry SDK core family | 2.9.0 |
| `@opentelemetry/sdk-node` | 0.220.0 |
| `@opentelemetry/auto-instrumentations-node` | 0.78.0 |
| `@opentelemetry/auto-instrumentations-web` | 0.65.0 |
| Nested `minimatch` | 9.0.9 |
| Nested `brace-expansion` | 2.1.7 |

## 3. Security Validation

Local validation included:

- Dependency installation and Next.js production build.
- Frontend Docker image build using the existing distroless Node.js runtime.
- Local HTTP smoke test returning HTTP 200.
- Trivy frontend dependency lockfile scan: zero HIGH and CRITICAL findings.
- Trivy production frontend image scan: zero HIGH and CRITICAL findings.

The existing Jenkins image security gate remained unchanged:

`trivy image --scanners vuln --severity CRITICAL --exit-code 1`

Jenkins CRITICAL-only scans passed. These results reflect the vulnerability database and dependency state at validation time, not a permanent guarantee against newly disclosed vulnerabilities.

## 4. Jenkins CI/CD Verification

The feature branch and merged main commit both passed Jenkins.

Verified stages included:

- Payment syntax validation.
- Payment unit tests: 6/6 passed.
- Frontend and payment Docker builds.
- Trivy CRITICAL-only vulnerability scans.
- GHCR publishing and image-pull verification on main.
- Automated GitOps image updates on main.

The successful main build used commit `0c935f45`.

## 5. Jenkins Agent Disk Exhaustion and Recovery

During the initial feature-branch build, the Jenkins agent exhausted its root filesystem while building the frontend Docker image.

### Failure evidence

- Host: `jenkins-agent-01`
- Agent address at the time: `192.168.1.214`
- Root filesystem reached 100% usage.
- Jenkins reported `java.io.IOException: No space left on device`.
- The Docker build stalled near its final image layer.
- Subsequent Jenkins stages were skipped.

### Recovery

Docker image cleanup reclaimed sufficient disk capacity. The agent was subsequently verified with:

- Approximately 43–46 GB available on the root filesystem.
- Active Docker and containerd services.
- Running Jenkins Java remoting process (`remoting.jar`).

The feature-branch pipeline was rerun successfully, followed by a successful main pipeline.

### Preventive actions

- Monitor filesystem utilization on the Jenkins agent.
- Establish a reviewed Docker image-retention policy.
- Avoid indiscriminate volume deletion or pruning during active builds.
- Consider disk-capacity alerting and scheduled cleanup during maintenance windows.

## 6. GitOps and Kubernetes Deployment

The Jenkins main pipeline published the new container images and updated the GitOps repository.

- GitOps repository: `dgsuma/dgs-private-cloud`
- GitOps commit: `fef68ad`
- Flux GitRepository: Ready=True
- Flux Kustomization: Ready=True
- Kubernetes namespace: `novacart`

Both frontend and payment were deployed with image tag:

`0c935f4566ec6be89fff57cf19a2d7851ed0cc32`

Both Kubernetes deployments reported successful rollouts and 1/1 available replicas. Newly started frontend and payment pods had zero restarts at the time of verification.

## 7. Checkout and Payment Validation

A real checkout workflow was exercised through the deployed NovaCart demo.

Payment logs confirmed:

- `Charge request received.`
- `Transaction complete.`

The successful transaction used trace ID:

`1a7048f4c4bcef787d51e3fbad9145ab`

A subsequent five-minute payment log check found no matches for `Transaction failed`, `ECONNREFUSED`, or `UNAVAILABLE`.

## 8. Grafana Tempo Distributed Tracing

The checkout trace was found in Grafana Tempo with the following details:

| Metric | Observed result |
|---|---|
| Trace ID | `1a7048f4c4bcef787d51e3fbad9145ab` |
| HTTP status | 200 |
| Services | 12 |
| Spans | 53 |
| Duration | 2.57 seconds |

The trace demonstrated propagation across the frontend, checkout, payment, Flagd, and supporting services.

This confirmed that the upgraded frontend OpenTelemetry dependencies preserved distributed tracing for the tested checkout workflow.

## 9. Known Nonblocking Startup Warnings

Two warnings were observed after deployment:

1. `MetadataLookupWarning: All promises were rejected` — consistent with unsuccessful cloud metadata discovery in an on-premises environment; the cause was not independently isolated.
2. `flagd provider not ready at startup; continuing while it reconnects` — a startup connection warning in the payment service.

A subsequent checkout and Flagd-related trace completed successfully. These observations do not establish that every startup warning is permanently resolved.

## 10. Final Outcome

Phase 5 was completed and verified across the full delivery workflow:

**Feature branch → Jenkins → PR #19 → main → Jenkins → GHCR → GitOps → Flux → Kubernetes → checkout → Grafana Tempo.**

No uncontrolled dependency upgrades, Jenkins security-gate changes, or manual Kubernetes deployment modifications were required.

## References

- [NovaCart PR #19](https://github.com/dgsuma/NovaCart/pull/19)
- [NovaCart source repository](https://github.com/dgsuma/NovaCart)
- [GitOps repository](https://github.com/dgsuma/dgs-private-cloud)
