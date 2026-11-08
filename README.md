# release-workflows

Reusable GitHub Actions workflows that WPTK's Python command-line and terminal apps share, so a binary build, a
release and its check are written once. Each app keeps a short `release.yml` that calls them.

| Workflow | What it does |
| --- | --- |
| [`build-binaries.yml`](.github/workflows/build-binaries.yml) | Builds a one-file PyInstaller binary on Windows, Linux (x86_64, arm64) and macOS (arm64, x86_64), smoke-tests each, checks the Linux glibc floor, names the files and uploads `binary-<platform>` artifacts. |
| [`publish-release.yml`](.github/workflows/publish-release.yml) | Checks the build produced exactly the expected files, writes `SHA256SUMS`, confirms the tag still points at the built commit and creates the GitHub release. |
| [`verify-published.yml`](.github/workflows/verify-published.yml) | After a release: downloads every file from its public URL, checks `SHA256SUMS` and each attestation, and runs each binary on its own kind of runner. |

Every command the apps need (install, build, smoke test) is an input, so nothing app-specific lives here. All
third-party actions are pinned to a commit SHA. The workflows hold no secrets and never publish to PyPI.

## What stays in the app repository

- **Attestation.** A certificate made inside a called workflow names the *called* workflow as its signer, which would
  break `gh attestation verify --signer-workflow OWNER/app/.github/workflows/release.yml`. So the app's own
  `release.yml` attests, in a job between the build and the publish.
- **PyPI trusted publishing.** PyPI matches the caller's workflow file name and environment, so the `pypi` job and its
  environment stay in the app.
- **Tag, version and changelog checks**, and anything else that depends on the app.

## Using it

Pin a full commit SHA (with the tag in a comment), not a branch.

```yaml
jobs:
  build:
    uses: WPTK/release-workflows/.github/workflows/build-binaries.yml@<sha> # v0.1.0
    with:
      app: myapp
      asset-prefix: myapp-${{ needs.verify.outputs.version }}
      linux-container: python:3.12-bullseye@sha256:7cc929040c5e8cf6036c5099d62a83708427c131fb7a7c965b5ba51e995eea1c
      install-command: python -m pip install . "pyinstaller>=6.22,<7"
      build-command: python -m PyInstaller --noconfirm --clean --onefile --name myapp src/myapp/__main__.py
      smoke-command: |
        "$BIN" --version
        "$BIN" --selftest

  attest:
    needs: [build, dist]
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
      attestations: write
    steps:
      - uses: actions/download-artifact@<sha> # v8
        with: {pattern: "binary-*", merge-multiple: true, path: release}
      - uses: actions/download-artifact@<sha> # v8
        with: {name: dist, path: release}
      - uses: actions/attest-build-provenance@<sha> # v4
        with:
          subject-path: release/*

  publish:
    needs: [verify, build, attest]
    permissions:
      contents: write
    uses: WPTK/release-workflows/.github/workflows/publish-release.yml@<sha> # v0.1.0
    with:
      expected-files: |
        myapp-0.2.0-py3-none-any.whl
        myapp-0.2.0.tar.gz
        myapp-0.2.0-windows-x86_64.exe
        myapp-0.2.0-linux-x86_64.tar.gz
        myapp-0.2.0-linux-arm64.tar.gz
        myapp-0.2.0-macos-arm64.tar.gz
        myapp-0.2.0-macos-x86_64.tar.gz
```

Asset names are `<asset-prefix>-<platform>`, with `.exe` on Windows and `.tar.gz` elsewhere (the archive holds one file
named after the app, with its executable bit). Pass `unix-archive: false` for bare binaries. `publish-release.yml` takes
`dry-run: true` to do everything except create the release.

Build-time details worth knowing:

- Linux builds run in the container you pass, because a PyInstaller binary needs at least the glibc of the machine that
  built it. `glibc-floor` (default 2.31) fails the build if a binary needs anything newer.
- `macos-15-intel` is GitHub's last Intel Mac image. When it goes (announced for fall 2027), the `macos-x86_64` entry in
  `build-binaries.yml` and `verify-published.yml` is removed in one place for every app.
- macOS binaries are not signed or notarized.

## Changing this repository

A change here changes every app that calls it, but only when the app moves its pinned SHA. `ci.yml` lints the
workflows with actionlint, builds a stand-in app (`tests/hello`) on all five platforms and runs `publish-release.yml` in
dry-run mode on the result. `verify-published.yml` can only be exercised by a real release, so CI checks its syntax.

Tags are `v0.MINOR.PATCH`. A call should pin the SHA the tag points at.

## License

MIT, see [LICENSE](LICENSE).
