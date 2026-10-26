"""Tests for conservative documentation-only detection."""

import unittest

from detect_docs_only import classify, is_documentation


DOCS_BASE = "0c935f4566ec6be89fff57cf19a2d7851ed0cc32"
PREVIOUS_CODE = "41902fc4d30b9ff0b711a390334399d622e97e78"
DOCS_HEAD = "099037c834f894782f43485a49aa821fd90abdb0"


class DocumentationPathTests(unittest.TestCase):

    def test_allowed_documentation_paths(self):
        for path in (
            "README.md",
            "CHANGELOG.md",
            "CONTRIBUTING.md",
            "docs/security/hardening.md",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_documentation(path))

    def test_non_documentation_paths(self):
        for path in (
            "Jenkinsfile",
            "ci/detect_docs_only.py",
            "src/frontend/package.json",
            "src/frontend/Dockerfile",
            "package-lock.json",
            ".github/workflows/build.yml",
        ):
            with self.subTest(path=path):
                self.assertFalse(is_documentation(path))


class GitClassificationTests(unittest.TestCase):

    def test_historical_documentation_only_merge(self):
        self.assertEqual(
            classify(DOCS_BASE, DOCS_HEAD),
            "DOCS_ONLY",
        )

    def test_mixed_code_and_documentation(self):
        self.assertEqual(
            classify(PREVIOUS_CODE, DOCS_HEAD),
            "FULL_CI",
        )

    def test_identical_revisions(self):
        self.assertEqual(
            classify(DOCS_HEAD, DOCS_HEAD),
            "FULL_CI",
        )

    def test_abbreviated_identical_revisions(self):
        self.assertEqual(
            classify("099037c8", DOCS_HEAD),
            "FULL_CI",
        )

    def test_invalid_revision(self):
        self.assertEqual(
            classify("invalid-revision", DOCS_HEAD),
            "FULL_CI",
        )

    def test_reversed_ancestry(self):
        self.assertEqual(
            classify(DOCS_HEAD, DOCS_BASE),
            "FULL_CI",
        )


if __name__ == "__main__":
    unittest.main()

class TemporaryRepositoryTests(unittest.TestCase):

    def test_application_file_moved_to_docs(self):
        import os
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def run(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            import subprocess

            run("init", "-q")
            run("config", "user.name", "CI Test")
            run("config", "user.email", "ci@example.test")

            (repo / "src").mkdir()
            (repo / "src" / "example.md").write_text("example")
            run("add", ".")
            run("commit", "-qm", "initial")
            base = run("rev-parse", "HEAD")

            (repo / "docs").mkdir()
            run("mv", "src/example.md", "docs/example.md")
            run("commit", "-qm", "move into docs")
            head = run("rev-parse", "HEAD")

            with patch.dict(os.environ, {"GIT_DIR": str(repo / ".git")}):
                self.assertEqual(classify(base, head), "FULL_CI")

    def test_code_change_reverted_before_docs_update(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def run(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            run("init", "-q")
            run("config", "user.name", "CI Test")
            run("config", "user.email", "ci@example.test")

            (repo / "src").mkdir()
            (repo / "src" / "app.py").write_text("value = 1\n")
            (repo / "README.md").write_text("Initial docs\n")
            run("add", ".")
            run("commit", "-qm", "initial")
            base = run("rev-parse", "HEAD")

            (repo / "src" / "app.py").write_text("value = 2\n")
            run("commit", "-qam", "modify application")

            (repo / "src" / "app.py").write_text("value = 1\n")
            run("commit", "-qam", "revert application")

            (repo / "README.md").write_text("Updated docs\n")
            run("commit", "-qam", "update documentation")
            head = run("rev-parse", "HEAD")

            with patch.dict(os.environ, {"GIT_DIR": str(repo / ".git")}):
                self.assertEqual(classify(base, head), "FULL_CI")

    def test_multiple_documentation_only_commits(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def run(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            run("init", "-q")
            run("config", "user.name", "CI Test")
            run("config", "user.email", "ci@example.test")

            (repo / "README.md").write_text("Initial documentation\n")
            run("add", ".")
            run("commit", "-qm", "initial")
            base = run("rev-parse", "HEAD")

            (repo / "README.md").write_text("Updated documentation\n")
            run("commit", "-qam", "update readme")

            (repo / "docs").mkdir()
            (repo / "docs" / "guide.md").write_text("Guide\n")
            run("add", ".")
            run("commit", "-qm", "add guide")
            head = run("rev-parse", "HEAD")

            with patch.dict(os.environ, {"GIT_DIR": str(repo / ".git")}):
                self.assertEqual(classify(base, head), "DOCS_ONLY")

    def test_missing_git_revision(self):
        self.assertEqual(
            classify("0000000000000000000000000000000000000000",
                     DOCS_HEAD),
            "FULL_CI",
        )

    def test_real_documentation_only_pr_merge(self):
        self.assertEqual(
            classify(
                "83703dfa20da462c758fcbd6ad32dc67a1cdf710",
                "d9bf21894ceee85e1bc5d7981ba58e2810253a1a",
            ),
            "DOCS_ONLY",
        )

    def test_merge_containing_application_change(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def run(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            run("init", "-q")
            run("config", "user.name", "CI Test")
            run("config", "user.email", "ci@example.test")

            (repo / "src").mkdir()
            (repo / "docs").mkdir()
            (repo / "src" / "app.py").write_text("value = 1\n")
            run("add", ".")
            run("commit", "-qm", "initial")
            base = run("rev-parse", "HEAD")

            run("checkout", "-qb", "feature")
            (repo / "src" / "app.py").write_text("value = 2\n")
            run("commit", "-qam", "modify application")

            run("checkout", "-q", "-")
            (repo / "docs" / "guide.md").write_text("Documentation\n")
            run("add", ".")
            run("commit", "-qm", "add documentation")

            run("merge", "--no-ff", "-m", "merge feature", "feature")
            head = run("rev-parse", "HEAD")

            with patch.dict(os.environ, {"GIT_DIR": str(repo / ".git")}):
                self.assertEqual(classify(base, head), "FULL_CI")

    def test_merge_reverts_hidden_application_change(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def run(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            run("init", "-q")
            run("config", "user.name", "CI Test")
            run("config", "user.email", "ci@example.test")

            (repo / "src").mkdir()
            (repo / "docs").mkdir()
            app = repo / "src" / "app.py"
            app.write_text("value = 1\n")

            run("add", ".")
            run("commit", "-qm", "initial")
            base = run("rev-parse", "HEAD")

            run("checkout", "-qb", "feature")
            app.write_text("value = 2\n")
            run("commit", "-qam", "change application")

            run("checkout", "-q", "-")
            (repo / "docs" / "guide.md").write_text("Documentation\n")
            run("add", ".")
            run("commit", "-qm", "add documentation")

            run("merge", "--no-ff", "--no-commit", "-s", "ours", "feature")
            run("commit", "-qm", "merge feature without application change")
            head = run("rev-parse", "HEAD")

            self.assertEqual(
                run("diff", "--name-only", base, head),
                "docs/guide.md",
            )

            with patch.dict(os.environ, {"GIT_DIR": str(repo / ".git")}):
                self.assertEqual(classify(base, head), "FULL_CI")

    def test_merge_resolution_introduces_application_change(self):
        import os
        import subprocess
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)

            def run(*args):
                return subprocess.run(
                    ["git", *args],
                    cwd=repo,
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.strip()

            run("init", "-q")
            run("config", "user.name", "CI Test")
            run("config", "user.email", "ci@example.test")

            (repo / "src").mkdir()
            (repo / "docs").mkdir()
            app = repo / "src" / "app.py"
            app.write_text("value = 1\n")
            run("add", ".")
            run("commit", "-qm", "initial")
            base = run("rev-parse", "HEAD")

            run("checkout", "-qb", "feature")
            (repo / "docs" / "feature.md").write_text("Feature docs\n")
            run("add", ".")
            run("commit", "-qm", "feature documentation")

            run("checkout", "-q", "-")
            (repo / "docs").mkdir(exist_ok=True)
            (repo / "docs" / "main.md").write_text("Main docs\n")
            run("add", ".")
            run("commit", "-qm", "main documentation")

            run("merge", "--no-ff", "--no-commit", "feature")

            app.write_text("value = 2\n")
            run("add", ".")
            run("commit", "-qm", "merge with application change")
            head = run("rev-parse", "HEAD")

            with patch.dict(os.environ, {"GIT_DIR": str(repo / ".git")}):
                self.assertEqual(classify(base, head), "FULL_CI")
