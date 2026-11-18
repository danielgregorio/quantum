# Releasing Quantum

Publishing a new version is driven entirely by a git tag. The
`.github/workflows/release.yml` workflow does the rest, and **nothing is
published unless CI passes first on the tagged commit**: the release's gate is
`ci.yml` itself, every job of it, and the publish job depends on it.

## One-time setup: PyPI trusted publisher

The workflow publishes to PyPI with **OIDC trusted publishing** — no API token
is stored in the repo. You configure the trust on PyPI once.

Because `quantum-framework` has not been published yet, use a **pending
publisher** (PyPI supports configuring one before the project exists):

1. Sign in to <https://pypi.org> → *Your account* → *Publishing*.
2. Under *Add a new pending publisher*, fill in:
   - **PyPI project name:** `quantum-framework`
   - **Owner:** `danielgregorio`
   - **Repository name:** `quantum`
   - **Workflow name:** `release.yml`
   - **Environment name:** *(leave blank)*
3. Save. The first successful run of the workflow claims the project and
   publishes it; subsequent releases reuse the same trust.

(Recommended to dry-run on <https://test.pypi.org> first with the same steps.)

## Cutting a release

1. In a pull request:
   - bump `project.version` in `pyproject.toml` (e.g. `1.1.0`). The workflow
     **refuses to publish if the tag does not match this value**;
   - rename `## Unreleased` in `CHANGELOG.md` to the version (`## 1.1.0`),
     with a few lines on top that say what the release is. The workflow
     **refuses a version without its section**, and the GitHub Release's text
     is that section (`scripts/release-notes.py`);
   - run `python scripts/generate-site-pages.py`, which writes the version's
     page under `docs/changelog/` (a test checks the newest version there is
     the one in `pyproject.toml`).
2. Merge it when CI is green.
3. Tag the merge commit on `main` and push the tag:

   ```bash
   git fetch origin main
   git tag v1.1.0 origin/main
   git push origin v1.1.0
   ```

That triggers, in order:

| Job              | What it does                                              |
|------------------|-----------------------------------------------------------|
| `ci`             | The whole of `ci.yml` on the tagged commit — the gate.    |
| `build`          | Checks the tag matches `pyproject` and has a CHANGELOG section, builds sdist + wheel, `twine check`, installs the wheel alone in a clean venv and runs it. |
| `publish`        | Uploads to PyPI via OIDC (only if `ci` and `build` passed). |
| `github-release` | Creates a GitHub Release with the version's CHANGELOG section + the artifacts. |

If a job fails, the tag is still there but nothing is published — fix, delete
the tag (`git push --delete origin v1.1.0`), and re-tag.

## After the first publish

`pip install quantum-framework` works, and you can add the PyPI badge back to
`README.md`:

```markdown
[![PyPI](https://img.shields.io/pypi/v/quantum-framework)](https://pypi.org/project/quantum-framework/)
```
