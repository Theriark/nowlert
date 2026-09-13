# Container deployment and release flow

Nowlert CE uses one source commit and one immutable image digest through its
release chain. Development builds the image once; Stage is the final runtime
acceptance gate; Finalize CE Release validates the Stage-approved candidate,
fast-forwards `main`, publishes stable GHCR/Docker Hub aliases, and creates the
annotated tag, GitHub Release, and release evidence. No image rebuild occurs
during promotion or finalization.

The release chain is:

```text
Development -> Stage -> Finalize CE Release
                              |-> main
                              `-> stable aliases + tag + GitHub Release
```

Stage promotion never updates `main`. Finalize CE Release owns the only
Stage -> `main` promotion.

## Local development checkout

Create private configuration outside Git-tracked files:

```bash
cp config/config.example.yaml config/config.yaml
nano config/config.yaml
```

Build and start the local development Compose service:

```bash
docker compose -f docker-compose.yml up -d --build
docker compose -f docker-compose.yml ps
docker logs --tail 100 nowlert-ce-dev
```

The development Compose definition builds the checked-out source and uses the
development host ports documented in that file.

## Production host preparation

```bash
cp .env.example .env
cp config/config.example.yaml config/config.yaml
mkdir -p logs/emails secrets state external-backups
chmod 600 .env config/config.yaml
chmod 700 logs logs/emails secrets state external-backups
id -u
id -g
```

Set `NOWLERT_UID` and `NOWLERT_GID` in `.env` to the identity that owns the
mounted directories.

Validate and start the production Compose definition:

```bash
docker compose -f compose.production.yaml config
docker compose -f compose.production.yaml pull
docker compose -f compose.production.yaml up -d
docker compose -f compose.production.yaml ps
docker logs --tail 100 nowlert-ce
```

The base production definition runs non-root, drops Linux capabilities,
prevents privilege escalation, uses a read-only root filesystem, and persists
only the explicitly mounted configuration/state/log/backup paths.

## Portainer stacks

Use absolute host paths in `.env`, for example:

```dotenv
NOWLERT_CONFIG_DIR=/docker/nowlert-ce/config
NOWLERT_LOG_DIR=/docker/nowlert-ce/logs
NOWLERT_SECRETS_DIR=/docker/nowlert-ce/secrets
NOWLERT_STATE_DIR=/docker/nowlert-ce/state
NOWLERT_EXTERNAL_BACKUP_DIR=/mnt/nowlert-backups
```

Pin a versioned image for production rather than relying only on `latest`.

## Persistent recovery boundary

Before an upgrade, keep a matched backup of:

- `config`;
- `state`;
- external `secrets`, when used;
- the deployment definition; and
- the currently running image reference/digest.

v3.1.6 keeps schema 9, so upgrading from v3.1.5 does not require a database
migration. A matched backup is still required for safe rollback after state has
changed.

---

# Repository environment model

The release branches represent approved source state:

| Branch | Meaning |
|---|---|
| `development` | cumulative active work; CI builds/deploys the Development candidate |
| `stage` | exact source commit approved by the final runtime acceptance gate |
| `main` | exact source of the last successfully finalized public release |

Before release finalization, the required invariant is:

```text
development SHA == stage SHA == image source SHA
```

`main` may intentionally lag behind Stage until Finalize CE Release succeeds.
After finalization, `main` equals the released Stage-approved source commit.
The runtime image is additionally pinned by immutable digest.

## Development

A push to `development` runs Continuous Integration. After the CI test/build job
passes, the same Continuous Integration workflow directly builds and publishes
the Development candidate and deploys the resulting immutable digest to CE
Development. There is no standalone Development Image workflow.

Continuous Integration does not run for ordinary pushes to `main`; `main` is a
release result, not another test environment.

Record from the successful development Continuous Integration run:

```text
SOURCE_COMMIT=<40-char development SHA>
FINAL_IMAGE=ghcr.io/theriark/nowlert-ce@sha256:<digest>
DEVELOPMENT_RUN_ID=<successful development Continuous Integration run id>
```

Do not replace the immutable digest with a mutable tag for later promotions.

## Stage

Stage promotion is manually dispatched from `development` with:

- `ce_image` — the exact Development immutable image;
- `source_commit` — the exact source SHA that built it; and
- `change_reference` — issue/release reference.

The workflow:

1. requires the source commit to equal current `development`;
2. runs the full test gate in a network-isolated namespace;
3. deploys the exact digest to Stage;
4. runs a passive notification-silent live smoke;
5. records desired state in the release ledger; and
6. advances only the `stage` branch to the approved source SHA using a guarded
   fast-forward-only ref update with propagation-safe verification.

Stage promotion never reads, advances, or otherwise modifies `main`. No rebuild
is performed. A successful Stage promotion is the final runtime acceptance
decision for the candidate.

Example CLI:

```bash
gh workflow run promote-stage.yml \
  --repo Theriark/nowlert-ce \
  --ref development \
  -f ce_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f change_reference="v3.1.6"
```

After success, record:

```text
STAGE_PROMOTION_RUN_ID=<successful Promote CE to Stage run id>
```

At this point stop. `main` must still represent the previous finalized release.
Do not fast-forward `main` manually.

## Release finalization

Finalize CE Release is manually dispatched from the Stage-approved branch and
completes the public CE release. It does not deploy or rebuild the application.
The finalizer requires `source_commit == stage`, proves current `main` can
fast-forward to that source without force, verifies the requested tag matches
`src/version.py`, requires the matching release notes and QA checklist, verifies
the immutable image is the Stage-approved runtime image, and validates the
successful Development Continuous Integration and Stage promotion evidence.

After all Stage/evidence checks pass, the finalizer advances `main` to the exact
Stage-approved source with `force=false`, waits for ref propagation, and verifies
the result. Only Finalize CE Release performs this Stage -> `main` promotion.
Because normal CI is not triggered by pushes to `main`, this does not start a
second redundant Continuous Integration run.

Inputs include the source commit, final immutable image, development Continuous
Integration run ID, Stage promotion run ID, and human-readable release notes.

Example for v3.1.6:

```bash
gh workflow run finalize-release.yml \
  --repo Theriark/nowlert-ce \
  --ref stage \
  -f version="v3.1.6" \
  -f final_image="$FINAL_IMAGE" \
  -f source_commit="$SOURCE_COMMIT" \
  -f development_run_id="$DEVELOPMENT_RUN_ID" \
  -f stage_promotion_run_id="$STAGE_PROMOTION_RUN_ID" \
  -f release_notes="Nowlert CE v3.1.6 release automation consolidation"
```

The workflow refuses an existing tag/release, verifies current Stage matches the
requested source, verifies the live Stage digest and Stage ledger, validates the
promotion evidence, and verifies `main` is fast-forward-safe. It then advances
`main` and publishes/verifies all four stable aliases from the already-approved
immutable digest:

```text
ghcr.io/theriark/nowlert-ce:3.1.6
ghcr.io/theriark/nowlert-ce:latest
docker.io/theriark/nowlert-ce:3.1.6
docker.io/theriark/nowlert-ce:latest
```

Every alias must resolve to the approved Stage digest. After registry
verification, the workflow creates the annotated tag and GitHub Release, writes
the release ledger record, and uploads the release evidence. There is **no image
rebuild** and no second Docker-alias workflow to run.

For Community Edition this stable registry publication is the production
release boundary. There is no additional CE Dokploy `Production` deployment
workflow; operators consume the released stable image from GHCR/Docker Hub.

## Watching workflow runs from CLI

List recent runs:

```bash
gh run list --repo Theriark/nowlert-ce --limit 20
```

Watch a known run and return non-zero on failure:

```bash
gh run watch "$RUN_ID" \
  --repo Theriark/nowlert-ce \
  --exit-status
```

Inspect run summary/jobs:

```bash
gh run view "$RUN_ID" --repo Theriark/nowlert-ce
gh run view "$RUN_ID" --repo Theriark/nowlert-ce --log-failed
```

## Rollback

### Before stable publication

If Stage fails, stop the release. Do not move `main` and do not run Finalize CE
Release. The Stage promotion workflow contains bounded rollback handling for
failed live gates where a previous image is available.

If Stage passes but release finalization has not started, `main` remains on the
previous finalized release by design.

### After stable publication

A source rollback and a state rollback are separate decisions:

1. identify the last known-good version and digest;
2. determine whether private state changed incompatibly;
3. if required, restore the matched pre-upgrade state/config/secret backup;
4. pin the known-good version/digest; and
5. verify health/login/routing/delivery before restoring traffic.

Never point an older image at a database schema it cannot open.

## Documentation/release consistency

Before finalization, verify all of the following describe the same candidate:

- `src/version.py`;
- `.env.example`;
- `compose.production.yaml`;
- `README.md`;
- `DOCKERHUB_README.md`;
- `CHANGELOG.md`;
- current release notes/QA checklist;
- screenshots; and
- the Development/Stage source SHA and immutable digest.

After finalization, verify `main` equals that exact released source SHA.
