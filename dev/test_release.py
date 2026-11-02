"""Regression tests for public release boundaries; synthetic fixtures only."""
from pathlib import Path
import tempfile
import unittest

from validate_release import ROOT, public_files, skill_files, validate


class ReleaseTests(unittest.TestCase):
    def make_fixture(self, root):
        (root / "SKILL.md").write_text(
            '---\nname: eodhd-financial-applications-skill\ndescription: "Build financial systems"\n---\n')
        (root / "README.md").write_text("# Example\n\n[Instructions](SKILL.md)\n")
        (root / "LICENSE").write_text((ROOT / "LICENSE").read_text())
        (root / ".gitignore").write_text("captures/\n")
        for name in (".github/workflows/validate.yml",):
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Fixture\n")

    def test_research_parent_and_local_captures_are_never_packaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            (parent / "FAQ-financial.txt").write_text("Private research fixture")
            root = parent / "skill"
            root.mkdir()
            self.make_fixture(root)
            (root / "captures").mkdir()
            (root / "captures" / "response.body").write_text("Private local capture")
            (root / "scripts").mkdir()
            (root / "scripts" / "__pycache__").mkdir()
            (root / "scripts" / "__pycache__" / "helper.pyc").write_bytes(b"fixture")
            self.assertEqual(validate(root), [])
            names = [str(path.relative_to(root)) for path in public_files(root)]
            self.assertFalse(any("captures" in name or "FAQ" in name or "pycache" in name for name in names))
            (root / "FAQ-financial.txt").write_text("Misplaced private research")
            self.assertTrue(any("root entry" in error for error in validate(root)))

    def test_skill_package_excludes_repository_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            for name in ("dev/validate_release.py", "scripts/eodhd_request.py", "references/a.md"):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_text("# Fixture\n")
            self.assertEqual(validate(root), [])
            names = {str(path.relative_to(root)) for path in skill_files(root)}
            self.assertEqual(names, {"SKILL.md", "LICENSE", "scripts/eodhd_request.py", "references/a.md"})

    def test_tooling_in_scripts_and_codex_metadata_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            (root / "scripts").mkdir()
            (root / "scripts" / "test_helpers.py").write_text("# Fixture\n")
            (root / "agents").mkdir()
            (root / "agents" / "openai.yaml").write_text("interface: {}\n")
            errors = validate(root)
            self.assertTrue(any("belongs in dev/" in error for error in errors))
            self.assertTrue(any("root entry: agents" in error for error in errors))

    def test_skill_cannot_link_to_repository_only_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            (root / "references").mkdir()
            (root / "references" / "a.md").write_text("[Install](../README.md)\n")
            self.assertTrue(any("repository-only" in error for error in validate(root)))

    def test_private_email_and_missing_license_fail_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            (root / "README.md").write_text("Example " + "private-person" + "@" + "mail.invalid")
            (root / "LICENSE").unlink()
            errors = validate(root)
            self.assertTrue(any("Missing release file: LICENSE" in error for error in errors))
            self.assertTrue(any("synthetic" in error for error in errors))

    def test_local_links_cannot_escape_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            (root / "README.md").write_text("[Private material](../outside.md)")
            self.assertTrue(any("escapes package" in error for error in validate(root)))

    def test_authentication_example_must_not_echo_secret(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.make_fixture(root)
            path = root / "references/api/general/authentication.md"
            path.parent.mkdir(parents=True)
            path.write_text("echo " + "$" + "EODHD_API_TOKEN\n")
            self.assertTrue(any("must not print" in error for error in validate(root)))


if __name__ == "__main__":
    unittest.main()
