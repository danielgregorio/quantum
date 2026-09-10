# Releasing Quantum

Publishing a new version is driven entirely by a git tag. The
`.github/workflows/release.yml` workflow does the rest, and **nothing is
published unless the full test suite passes first** (the publish job depends
on the test job).

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

1. Bump `project.version` in `pyproject.toml` (e.g. `0.9.1`). The workflow
   **refuses to publish if the tag does not match this value.**
2. Commit the bump.
3. Tag and push:

   ```bash
   git tag v0.9.1
   git push origin v0.9.1
   ```

That triggers, in order:

| Job              | What it does                                              |
|------------------|-----------------------------------------------------------|
| `test`           | Full declared suite on Python 3.12 — the gate.             |
| `build`          | Checks the tag matches `pyproject`, builds sdist + wheel, `twine check`. |
| `publish`        | Uploads to PyPI via OIDC (only if `test` and `build` passed). |
| `github-release` | Creates a GitHub Release with generated notes + the artifacts. |

If tests fail, the tag is still there but nothing is published — fix, delete
the tag (`git push --delete origin v0.9.1`), and re-tag.

## After the first publish

`pip install quantum-framework` works, and you can add the PyPI badge back to
`README.md`:

```markdown
[![PyPI](https://img.shields.io/pypi/v/quantum-framework)](https://pypi.org/project/quantum-framework/)
```
