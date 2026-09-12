# Stage-Final CE Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove Production Reference from the active Nowlert CE release path and release v3.1.3 using Stage as the final runtime acceptance gate.

**Architecture:** Development produces one immutable image. Stage validates and deploys that exact digest, records desired state, and advances the `stage` branch. `main` then fast-forwards to the approved source. Finalization validates Development + Stage evidence and publishes the tag/release without another deployment.

**Tech Stack:** GitHub Actions YAML, Python 3.13, pytest, GitHub CLI/API, Dokploy release helper, AWS-backed CE ledger.

**Spec:** `docs/superpowers/specs/2026-09-12-stage-final-acceptance-release-design.md`

## Global Constraints

- Stage application ID remains `x9zOew6dmrn-jmcnFbllk`.
- Stage health remains `https://ce-stg-nowlert.theriark.dev/api/health`.
- Promotion tests remain notification-silent; do not reintroduce delivery QA.
- Release publication performs no build and no deployment.
- Historical release records that actually used Production Reference are not rewritten.
- No application runtime, schema, routing, destination, authentication, or persistent-state changes.

---

### Task 1: Make release finalization Stage-only

**Files:**
- Modify: `.github/workflows/finalize-release.yml`
- Modify: `.github/scripts/finalize_release.py`
- Test: release-finalization and environment-workflow tests under `tests/`

**Interfaces:**
- Consumes: Development Image run ID, Stage promotion run ID, immutable GHCR digest, source commit, release version.
- Produces: `release-manifest.json` and `release-summary.md` containing Development + Stage evidence only.

- [ ] **Step 1: Write failing tests for the new finalizer contract**

Assert that the finalizer no longer accepts `production_reference_run_id`, no longer contains `CE_PRODREF_APPLICATION_ID`, requires `main == stage == source_commit`, and validates Stage live image + Stage ledger.

```python
assert "production_reference_run_id" not in workflow_text
assert "CE_PRODREF_APPLICATION_ID" not in workflow_text
assert "refs/remotes/origin/stage" in workflow_text
assert "--environment stage" in workflow_text
```

For the Python release validator, assert the expected workflow map contains only Development and Stage, and the generated manifest has no Production Reference fields.

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
python -m pytest -q tests/test_environment_branch_workflow.py tests/test_v313_release_docs.py tests/test_promotion_smoke_safety.py
```

Expected: failures where Production Reference is still required.

- [ ] **Step 3: Implement the minimal Stage-only finalizer**

In `finalize-release.yml`:

```yaml
inputs:
  version:
    required: true
    type: string
  final_image:
    required: true
    type: string
  source_commit:
    required: true
    type: string
  development_run_id:
    required: true
    type: string
  stage_promotion_run_id:
    required: true
    type: string
  release_notes:
    required: true
    type: string
```

Fetch both `main` and `stage`, require both refs to equal `SOURCE_COMMIT`, assert the live Stage application image equals `FINAL_IMAGE`, and assert the Stage ledger current record matches `FINAL_IMAGE`, `SOURCE_COMMIT`, and `STAGE_PROMOTION_RUN_ID`.

Call `finalize_release.py` without a Production Reference run argument.

In `finalize_release.py`, reduce the workflow/evidence model to Development + Stage and emit a manifest shaped around:

```python
manifest = {
    "schema_version": 1,
    "edition": "ce",
    "version": args.version,
    "source_commit": args.source_commit,
    "development_run": str(args.development_run),
    "stage_promotion_run": str(args.stage_run),
    "final_image": args.final_image,
    "stage_application_id": STAGE_APPLICATION_ID,
    "qa_evidence": {
        "type": "notification_silent_stage_final_acceptance",
        "notification_delivery_tests": False,
        "stage": {
            "promotion_run": str(args.stage_run),
            "success_marker": STAGE_SILENT_SUCCESS_MARKER,
        },
    },
    "rebuild_during_promotion": False,
    "deployment_during_finalization": False,
}
```

- [ ] **Step 4: Run focused tests and confirm GREEN**

```bash
python -m pytest -q tests/test_environment_branch_workflow.py tests/test_v313_release_docs.py tests/test_promotion_smoke_safety.py
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/finalize-release.yml .github/scripts/finalize_release.py tests
git commit -m "release: make Stage the final CE acceptance gate"
```

---

### Task 2: Remove Production Reference runtime state from active tooling

**Files:**
- Delete: `.github/workflows/promote-production-reference.yml`
- Modify: `.github/scripts/ledger.py`
- Modify: `.github/scripts/verify_drift.py`
- Modify: `.github/workflows/verify-runtime-drift.yml`
- Modify: `.github/workflows/ci.yml`
- Test: `tests/test_ledger.py`
- Test: `tests/test_verify_drift.py`
- Test: `tests/test_environment_branch_workflow.py`

**Interfaces:**
- Consumes: Stage ledger record and live Stage application.
- Produces: Stage-only desired-state and drift checks.

- [ ] **Step 1: Write failing Stage-only ledger/drift tests**

```python
assert ledger.VALID_ENVIRONMENTS == {"stage"}
assert set(verify_drift.ENVIRONMENTS) == {"stage"}
```

Update workflow-list tests so `promote-production-reference.yml` must not exist and CI/YAML validation no longer references it.

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
python -m pytest -q tests/test_ledger.py tests/test_verify_drift.py tests/test_environment_branch_workflow.py
```

- [ ] **Step 3: Implement Stage-only runtime state**

Set:

```python
VALID_ENVIRONMENTS = {"stage"}
```

and:

```python
ENVIRONMENTS = {
    "stage": {"application_id": "x9zOew6dmrn-jmcnFbllk"},
}
```

Retarget `verify-runtime-drift.yml` to GitHub environment `stage` and remove any Production Reference matrix/arguments. Remove `promote-production-reference.yml` from CI workflow validation lists, then delete the workflow file.

Remove Production Reference fields from new release ledger records while preserving backward-compatible reading of old ledger objects where practical.

- [ ] **Step 4: Run focused tests and confirm GREEN**

```bash
python -m pytest -q tests/test_ledger.py tests/test_verify_drift.py tests/test_environment_branch_workflow.py
```

- [ ] **Step 5: Commit**

```bash
git add .github tests
git commit -m "release: remove CE Production Reference runtime"
```

---

### Task 3: Update current release documentation and documentation validation

**Files:**
- Modify: `docs/deployment.md`
- Modify: `docs/releases/v3.1.3.md`
- Modify: `docs/v3.1.3-qa-checklist.md`
- Modify: `tools/validate_current_documentation.py`
- Test: `tests/test_v313_release_docs.py`
- Test: `tests/test_v310_brand_asset_and_deployment_gate.py`

**Interfaces:**
- Consumes: Stage-final workflow contract from Tasks 1-2.
- Produces: operator instructions for `Development -> Stage -> main -> Release`.

- [ ] **Step 1: Write failing documentation tests**

Require current docs to contain `Development -> Stage -> main -> Release`, the Stage health hostname, and the Stage-only finalizer inputs. Require the current v3.1.3 docs not to instruct operators to dispatch `promote-production-reference.yml`.

- [ ] **Step 2: Run focused tests and confirm RED**

```bash
python -m pytest -q tests/test_v313_release_docs.py tests/test_v310_brand_asset_and_deployment_gate.py
python tools/validate_current_documentation.py
```

- [ ] **Step 3: Update docs and validator**

Document these operator commands:

```bash
# after Stage is accepted, fast-forward main only
git fetch origin
git checkout main
git merge --ff-only origin/stage
git push origin main
```

and finalization inputs with no Production Reference run ID. Preserve historical v3.1.2 records unchanged.

- [ ] **Step 4: Run documentation tests and validator**

```bash
python -m pytest -q tests/test_v313_release_docs.py tests/test_v310_brand_asset_and_deployment_gate.py
python tools/validate_current_documentation.py
```

- [ ] **Step 5: Commit**

```bash
git add docs tools tests
git commit -m "docs: document Stage-final CE release chain"
```

---

### Task 4: Full verification and release-chain handoff

**Files:**
- Review all changed files from Tasks 1-3.

- [ ] **Step 1: Run the complete test suite**

```bash
python -m pytest -q
```

Expected: all tests pass.

- [ ] **Step 2: Validate workflow YAML and current docs through repository CI**

Push the branch and open a PR against `development`. Require CI success before merge.

- [ ] **Step 3: Merge to `development` and create a fresh candidate**

After merge, dispatch `docker-development.yml` from `development`. Record the new source SHA, immutable digest, and Development run ID.

- [ ] **Step 4: Promote that exact candidate through Stage**

Dispatch `promote-stage.yml` from `development` with the new immutable digest/source SHA. Require Stage full gate, passive smoke, Stage ledger, and Stage branch advancement to pass.

- [ ] **Step 5: Fast-forward `main` to Stage**

Use a non-force ref move and verify `main == stage == source_commit`.

- [ ] **Step 6: Dispatch Stage-only finalization**

Run `finalize-release.yml` from `main` with `version=v3.1.3`, the new immutable digest, source commit, Development run ID, Stage promotion run ID, and release notes.

- [ ] **Step 7: Publish stable aliases only after finalization succeeds**

Dispatch `docker-release.yml` with the created `v3.1.3` tag and the same immutable digest. Verify GHCR and Docker Hub `3.1.3` and `latest` aliases resolve to that digest without rebuild.
