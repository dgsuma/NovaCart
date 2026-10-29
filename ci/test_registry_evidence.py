"""Tests for NovaCart registry evidence validation."""

import copy
import unittest

from registry_evidence import validate_evidence


SHA = "a" * 40
FRONTEND_DIGEST = "sha256:" + "b" * 64
PAYMENT_DIGEST = "sha256:" + "c" * 64


def valid_evidence():
    return {
        "schema_version": 1,
        "source_sha": SHA,
        "build_number": 41,
        "images": {
            "frontend": {"digest": FRONTEND_DIGEST},
            "payment": {"digest": PAYMENT_DIGEST},
        },
    }


class RegistryEvidenceTests(unittest.TestCase):

    def test_valid_evidence(self):
        self.assertTrue(validate_evidence(valid_evidence(), SHA, 41))

    def test_wrong_source_sha(self):
        self.assertFalse(
            validate_evidence(valid_evidence(), "d" * 40, 41)
        )

    def test_wrong_build_number(self):
        self.assertFalse(
            validate_evidence(valid_evidence(), SHA, 40)
        )

    def test_missing_image(self):
        evidence = valid_evidence()
        del evidence["images"]["payment"]
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_invalid_digest(self):
        evidence = valid_evidence()
        evidence["images"]["frontend"]["digest"] = "sha256:invalid"
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_unexpected_field(self):
        evidence = valid_evidence()
        evidence["approved"] = True
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_invalid_schema_version(self):
        evidence = valid_evidence()
        evidence["schema_version"] = 2
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_boolean_build_number(self):
        evidence = valid_evidence()
        evidence["build_number"] = True
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_missing_evidence(self):
        self.assertFalse(validate_evidence(None, SHA, 41))

    def test_invalid_expected_sha(self):
        self.assertFalse(validate_evidence(valid_evidence(), "invalid", 41))

    def test_invalid_expected_build(self):
        self.assertFalse(validate_evidence(valid_evidence(), SHA, 0))

    def test_extra_image(self):
        evidence = copy.deepcopy(valid_evidence())
        evidence["images"]["other"] = {"digest": FRONTEND_DIGEST}
        self.assertFalse(validate_evidence(evidence, SHA, 41))


    def test_non_dictionary_evidence(self):
        self.assertFalse(validate_evidence([], SHA, 41))

    def test_unexpected_image_field(self):
        evidence = valid_evidence()
        evidence["images"]["frontend"]["tag"] = SHA
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_uppercase_digest(self):
        evidence = valid_evidence()
        evidence["images"]["payment"]["digest"] = (
            "sha256:" + "A" * 64
        )
        self.assertFalse(validate_evidence(evidence, SHA, 41))

    def test_boolean_expected_build(self):
        self.assertFalse(validate_evidence(valid_evidence(), SHA, True))

class RegistryDigestTests(unittest.TestCase):

    def fake_result(self, returncode=0, payload=None):
        from types import SimpleNamespace
        import json

        if payload is None:
            payload = {
                "schemaVersion": 2,
                "mediaType": "application/vnd.oci.image.manifest.v1+json",
            }

        return SimpleNamespace(
            returncode=returncode,
            stdout=json.dumps(payload).encode(),
        )

    def test_valid_digest_reference(self):
        from registry_evidence import verify_registry_digest

        expected = "ghcr.io/dgsuma/novacart-frontend@" + FRONTEND_DIGEST

        def inspect(reference):
            self.assertEqual(reference, expected)
            return self.fake_result()

        self.assertTrue(
            verify_registry_digest(
                "ghcr.io/dgsuma/novacart-frontend",
                FRONTEND_DIGEST,
                inspect=inspect,
            )
        )

    def test_invalid_digest_rejected(self):
        from registry_evidence import verify_registry_digest

        self.assertFalse(
            verify_registry_digest(
                "ghcr.io/dgsuma/novacart-frontend",
                "sha256:invalid",
                inspect=lambda _: self.fake_result(),
            )
        )

    def test_unapproved_image_rejected(self):
        from registry_evidence import verify_registry_digest

        self.assertFalse(
            verify_registry_digest(
                "ghcr.io/other/image",
                FRONTEND_DIGEST,
                inspect=lambda _: self.fake_result(),
            )
        )

    def test_registry_failure(self):
        from registry_evidence import verify_registry_digest

        self.assertFalse(
            verify_registry_digest(
                "ghcr.io/dgsuma/novacart-payment",
                PAYMENT_DIGEST,
                inspect=lambda _: self.fake_result(returncode=1),
            )
        )

    def test_invalid_json(self):
        from types import SimpleNamespace
        from registry_evidence import verify_registry_digest

        self.assertFalse(
            verify_registry_digest(
                "ghcr.io/dgsuma/novacart-payment",
                PAYMENT_DIGEST,
                inspect=lambda _: SimpleNamespace(
                    returncode=0,
                    stdout=b"not-json",
                ),
            )
        )

    def test_unexpected_manifest_type(self):
        from registry_evidence import verify_registry_digest

        self.assertFalse(
            verify_registry_digest(
                "ghcr.io/dgsuma/novacart-payment",
                PAYMENT_DIGEST,
                inspect=lambda _: self.fake_result(
                    payload={
                        "schemaVersion": 2,
                        "mediaType": "unexpected/type",
                    }
                ),
            )
        )

class PushDigestParserTests(unittest.TestCase):

    def setUp(self):
        from registry_evidence import parse_push_digest

        self.parse = parse_push_digest
        self.tag = "a" * 40
        self.digest = "sha256:" + "b" * 64
        self.line = (
            f"{self.tag}: digest: {self.digest} size: 2418"
        )

    def test_valid_push_result(self):
        output = (
            "The push refers to repository [ghcr.io/dgsuma/novacart-frontend]\n"
            "layer1: Layer already exists\n"
            + self.line + "\n"
        )
        self.assertEqual(
            self.parse(output, self.tag),
            self.digest,
        )

    def test_missing_digest(self):
        self.assertIsNone(
            self.parse("Layer already exists\n", self.tag)
        )

    def test_incorrect_tag(self):
        self.assertIsNone(
            self.parse(self.line, "c" * 40)
        )

    def test_duplicate_digest_lines(self):
        self.assertIsNone(
            self.parse(self.line + "\n" + self.line, self.tag)
        )

    def test_malformed_digest(self):
        output = f"{self.tag}: digest: sha256:invalid size: 2418"
        self.assertIsNone(self.parse(output, self.tag))

    def test_invalid_expected_tag(self):
        self.assertIsNone(
            self.parse(self.line, "invalid-tag")
        )

class PushEvidenceBuilderTests(unittest.TestCase):

    def setUp(self):
        from registry_evidence import build_push_evidence

        self.build = build_push_evidence
        self.sha = "a" * 40
        self.frontend_digest = "sha256:" + "b" * 64
        self.payment_digest = "sha256:" + "c" * 64

        self.frontend_output = (
            f"{self.sha}: digest: {self.frontend_digest} size: 2418"
        )
        self.payment_output = (
            f"{self.sha}: digest: {self.payment_digest} size: 2400"
        )

    def test_valid_evidence_generation(self):
        evidence = self.build(
            self.sha, 42,
            self.frontend_output,
            self.payment_output,
        )

        self.assertIsNotNone(evidence)
        self.assertEqual(evidence["source_sha"], self.sha)
        self.assertEqual(evidence["build_number"], 42)
        self.assertEqual(
            evidence["images"]["frontend"]["digest"],
            self.frontend_digest,
        )
        self.assertEqual(
            evidence["images"]["payment"]["digest"],
            self.payment_digest,
        )

    def test_missing_frontend_push(self):
        self.assertIsNone(
            self.build(self.sha, 42, "", self.payment_output)
        )

    def test_missing_payment_push(self):
        self.assertIsNone(
            self.build(self.sha, 42, self.frontend_output, "")
        )

    def test_wrong_frontend_tag(self):
        wrong_output = self.frontend_output.replace(
            self.sha, "d" * 40
        )
        self.assertIsNone(
            self.build(self.sha, 42, wrong_output, self.payment_output)
        )

    def test_invalid_source_sha(self):
        self.assertIsNone(
            self.build(
                "invalid", 42,
                self.frontend_output,
                self.payment_output,
            )
        )

    def test_invalid_build_number(self):
        self.assertIsNone(
            self.build(
                self.sha, 0,
                self.frontend_output,
                self.payment_output,
            )
        )

if __name__ == "__main__":
    unittest.main()
