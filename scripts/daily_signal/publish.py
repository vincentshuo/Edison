"""Publish only the reading feed to Edison's existing GitHub Pages branch."""
from pathlib import Path
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[2]
SITE = REPO / "surfaces/gui/public/youtube"
PAGES_BRANCH = "codex/oauth-public-pages"


def publish():
    subprocess.run(["git", "fetch", "origin", PAGES_BRANCH], cwd=REPO, check=True)
    revision = subprocess.check_output(["git", "rev-parse", "FETCH_HEAD"], cwd=REPO, text=True).strip()
    with tempfile.TemporaryDirectory() as temp:
        checkout = Path(temp) / "pages"
        subprocess.run(["git", "worktree", "add", "--quiet", "--detach", checkout, revision], cwd=REPO, check=True)
        try:
            target = checkout / "youtube"
            # Snapshot the committed feed, including deletions, independent of concurrent edits.
            if target.exists():
                shutil.rmtree(target)
            target.mkdir()
            with tempfile.TemporaryFile() as archive:
                subprocess.run(["git", "archive", "HEAD:surfaces/gui/public/youtube"], cwd=REPO, stdout=archive, check=True)
                archive.seek(0)
                subprocess.run(["tar", "-xf", "-", "-C", target], stdin=archive, check=True)
            (checkout / ".nojekyll").touch()
            subprocess.run(["git", "add", "--", "youtube", ".nojekyll"], cwd=checkout, check=True)
            if subprocess.run(["git", "diff", "--cached", "--quiet"], cwd=checkout).returncode:
                subprocess.run(["git", "commit", "-qm", "Publish Edison YouTube reports"], cwd=checkout, check=True)
                subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{PAGES_BRANCH}"], cwd=checkout, check=True)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", checkout], cwd=REPO, check=True)


if __name__ == "__main__":
    publish()
