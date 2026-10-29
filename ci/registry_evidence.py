"""Strict structural validation for NovaCart registry evidence."""

import re

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
DIGEST_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


def validate_evidence(evidence, expected_sha, expected_build):
    """Return True only for structurally valid, matching evidence."""

    if not isinstance(evidence, dict):
        return False

    if set(evidence) != {
        "schema_version", "source_sha", "build_number", "images"
    }:
        return False

    if type(evidence["schema_version"]) is not int:
        return False

    if evidence["schema_version"] != 1:
        return False

    if not isinstance(expected_sha, str):
        return False

    if not SHA_RE.fullmatch(expected_sha):
        return False

    if evidence["source_sha"] != expected_sha:
        return False

    if type(expected_build) is not int or expected_build <= 0:
        return False

    if type(evidence["build_number"]) is not int:
        return False

    if evidence["build_number"] != expected_build:
        return False

    images = evidence["images"]

    if not isinstance(images, dict):
        return False

    if set(images) != {"frontend", "payment"}:
        return False

    for name in ("frontend", "payment"):
        image = images[name]

        if not isinstance(image, dict):
            return False

        if set(image) != {"digest"}:
            return False

        digest = image["digest"]

        if not isinstance(digest, str):
            return False

        if not DIGEST_RE.fullmatch(digest):
            return False

    return True

def verify_registry_digest(image_name, expected_digest, inspect=None):
    """Check digest-addressed OCI manifest accessibility; fail closed."""

    import json
    import subprocess

    if image_name not in (
        "ghcr.io/dgsuma/novacart-frontend",
        "ghcr.io/dgsuma/novacart-payment",
    ):
        return False

    if not isinstance(expected_digest, str):
        return False

    if not DIGEST_RE.fullmatch(expected_digest):
        return False

    reference = f"{image_name}@{expected_digest}"

    if inspect is None:
        def inspect(ref):
            return subprocess.run(
                ["docker", "manifest", "inspect", ref],
                capture_output=True,
                check=False,
                timeout=30,
            )

    try:
        result = inspect(reference)

        if result.returncode != 0:
            return False

        manifest = json.loads(result.stdout)

        if not isinstance(manifest, dict):
            return False

        if manifest.get("schemaVersion") != 2:
            return False

        if manifest.get("mediaType") not in (
            "application/vnd.oci.image.manifest.v1+json",
            "application/vnd.docker.distribution.manifest.v2+json",
        ):
            return False

        return True

    except (
        OSError,
        ValueError,
        TypeError,
        AttributeError,
        subprocess.TimeoutExpired,
    ):
        return False

PUSH_RESULT_RE = re.compile(
    r"^[^\s:]+:\s+digest:\s+(sha256:[0-9a-f]{64})\s+size:\s+[0-9]+\s*$"
)


def parse_push_digest(push_output, expected_tag):
    """Extract one registry digest from a Docker push result; fail closed."""

    if not isinstance(push_output, str):
        return None

    if not isinstance(expected_tag, str):
        return None

    if not re.fullmatch(r"[0-9a-f]{40}", expected_tag):
        return None

    matches = []

    for line in push_output.splitlines():
        match = PUSH_RESULT_RE.fullmatch(line.strip())

        if match is None:
            continue

        prefix = line.strip().split(":", 1)[0]

        if prefix != expected_tag:
            return None

        matches.append(match.group(1))

    if len(matches) != 1:
        return None

    return matches[0]


def build_push_evidence(source_sha, build_number, frontend_output, payment_output):
    """Build validated evidence from two successful push outputs."""

    if not isinstance(source_sha, str) or not SHA_RE.fullmatch(source_sha):
        return None

    if type(build_number) is not int or build_number <= 0:
        return None

    frontend_digest = parse_push_digest(frontend_output, source_sha)
    payment_digest = parse_push_digest(payment_output, source_sha)

    if frontend_digest is None or payment_digest is None:
        return None

    evidence = {
        "schema_version": 1,
        "source_sha": source_sha,
        "build_number": build_number,
        "images": {
            "frontend": {"digest": frontend_digest},
            "payment": {"digest": payment_digest},
        },
    }

    if not validate_evidence(evidence, source_sha, build_number):
        return None

    return evidence


def main():
    """Generate validated JSON evidence from successful Docker pushes."""

    import argparse
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--build-number", required=True, type=int)
    parser.add_argument("--frontend-log", required=True)
    parser.add_argument("--payment-log", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    try:
        frontend_output = Path(args.frontend_log).read_text(
            encoding="utf-8"
        )
        payment_output = Path(args.payment_log).read_text(
            encoding="utf-8"
        )

        evidence = build_push_evidence(
            args.source_sha,
            args.build_number,
            frontend_output,
            payment_output,
        )

        if evidence is None:
            return 1

        for name in ("frontend", "payment"):
            image_name = f"ghcr.io/dgsuma/novacart-{name}"
            digest = evidence["images"][name]["digest"]

            if not verify_registry_digest(image_name, digest):
                return 1

        output = Path(args.output)
        output.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        print("Registry evidence generated and validated.")
        return 0

    except (OSError, ValueError, TypeError):
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
