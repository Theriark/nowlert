# Contributing

Thanks for contributing to Nowlert CE.

Contributions should keep implementation, tests, documentation, and release
behavior aligned.

## Branch model

`development` is the cumulative integration branch for active CE work.

- Start normal feature/fix work from the current `development` branch.
- Open pull requests back to `development` unless maintainers explicitly request
  another target.
- `stage` is an environment approval pointer and should be advanced by the Stage
  promotion workflow, not by ordinary feature pull requests.
- `main` represents Stage-approved release source and is fast-forwarded as part
  of the release process. Do not use `main` as the default target for active
  feature development.

## Getting started

1. Fork the repository or create a permitted working branch.
2. Update local refs and branch from `development`.
3. Make one focused change.
4. Add/update tests.
5. Update relevant current documentation for user-visible behavior.
6. Run the local validation suite.
7. Open a pull request targeting `development`.

Example:

```bash
git fetch origin
git switch development
git pull --ff-only origin development
git switch -c feature/my-change
```

## Validation

Install development dependencies and run:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python tools/validate_current_documentation.py
```

If the change affects container/runtime behavior, also build the image locally
or rely on the repository CI Docker build before merge.

## Coding style

- Follow the established Python style and PEP 8 conventions.
- Keep functions focused and bounded.
- Preserve security/ownership/error boundaries.
- Write meaningful commit messages.
- Prefer small, independently testable pull requests.
- Do not weaken secret redaction or credential handling to simplify tests.

## Documentation

User-visible behavior changes should update the matching current guide under
`docs/` and, when appropriate, README/Docker Hub/release notes.

UI screenshots must come from the candidate being documented and must not expose
credentials, API/setup tokens, private URLs, email addresses, or personal data.

Historical release notes and acceptance checklists are version records; do not
rewrite old files to describe new behavior.

## Reporting issues

Include:

- Nowlert version;
- image tag/digest when available;
- deployment type;
- Python/Docker versions when relevant;
- steps to reproduce;
- expected behavior;
- actual behavior; and
- sanitized logs/evidence.

Never paste credential values, destination webhook URLs, setup tokens, or
private secrets into an issue.

## Feature requests

Check for an existing issue first. New work should define an independently
testable outcome, compatibility/security boundary, and expected validation
level.

## Release integrity

Development, Stage, main, release tags, and stable images are bound to explicit
source commits/digests. Do not bypass promotion checks or rebuild a release
image from a tag after Stage approval.

See [docs/deployment.md](docs/deployment.md) for the release flow.
