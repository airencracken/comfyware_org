#!/usr/bin/env python3
"""Test the deploy script against throwaway document roots."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "site" / "deploy.sh"
SITE = ROOT / "site"


def deploy(target, dry_run=False):
    env = {k: v for k, v in os.environ.items() if k != "DRY_RUN"}
    if dry_run:
        env["DRY_RUN"] = "1"
    return subprocess.run(["sh", str(SCRIPT), str(target)], capture_output=True, text=True,
                          env=env, timeout=60)


def tree(root):
    return sorted(str(p.relative_to(root)) for p in Path(root).rglob("*") if p.is_file())


@unittest.skipUnless(shutil.which("rsync"), "rsync is not installed")
class DeployTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.target = Path(directory.name) / "www"
        self.target.mkdir()

    def test_publishes_an_exact_copy_and_removes_stale_files(self):
        (self.target / "old-page.html").write_text("removed from site/")
        (self.target / "assets").mkdir()
        (self.target / "assets" / "old.png").write_bytes(b"stale")
        result = deploy(self.target)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(tree(self.target), tree(SITE))
        self.assertEqual((self.target / "index.html").read_bytes(), (SITE / "index.html").read_bytes())

    def test_files_are_world_readable_for_the_web_server(self):
        self.assertEqual(deploy(self.target).returncode, 0)
        for path in self.target.rglob("*"):
            mode = path.stat().st_mode & 0o777
            self.assertEqual(mode, 0o755 if path.is_dir() else 0o644, path)

    def test_dry_run_changes_nothing(self):
        (self.target / "keep.html").write_text("still here")
        result = deploy(self.target, dry_run=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry run only", result.stdout)
        self.assertEqual(tree(self.target), ["keep.html"])

    def test_refuses_dangerous_or_mistyped_destinations(self):
        inside = Path(tempfile.mkdtemp(dir=ROOT))
        self.addCleanup(shutil.rmtree, inside)
        outer = self.target.parent
        cases = {
            "": "empty",
            "relative/www": "absolute path",
            "/": "refusing to publish to /",
            str(outer / "missing"): "does not exist",
            str(inside): "inside the repository",
            str(ROOT): "inside the repository",
            str(ROOT.parent): "repository is inside the document root",
        }
        for target, message in cases.items():
            with self.subTest(target=target):
                result = deploy(target)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)
        self.assertEqual(tree(inside), [])

    def test_symlinked_destination_is_checked_where_it_points(self):
        link = self.target.parent / "link"
        link.symlink_to(ROOT)
        result = deploy(link)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("inside the repository", result.stderr)

    def test_deploy_target_runs_the_content_checks_first(self):
        makefile = (ROOT / "Makefile").read_text()
        self.assertIn("\ndeploy: test-content\n", makefile)
        self.assertIn('sh scripts/site/deploy.sh "$(DEPLOY_DIR)"', makefile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
