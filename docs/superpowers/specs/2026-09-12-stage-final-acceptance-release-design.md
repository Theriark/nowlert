# Stage-Final CE Release Design

## Goal

Remove Production Reference from the active Nowlert CE release chain and make Stage the final runtime acceptance environment before `main` and release publication.

## Approved release chain

`development -> Stage -> main -> Release`

Development builds the immutable candidate image. Stage performs the complete network-isolated test gate, deploys that exact digest, performs passive live verification, records the Stage desired-state ledger entry, and advances the `stage` branch to the approved source commit. No Production Reference runtime exists in the active release path.

After Stage acceptance, `main` must fast-forward to the Stage-approved source commit. Release finalization is publication-only: it validates the immutable Development image, the successful Stage promotion and Stage ledger, the source version and release documentation, then creates the annotated tag and GitHub Release without building or deploying.

## Runtime and evidence model

- Stage is the only pre-production runtime acceptance environment.
- The Stage application is `x9zOew6dmrn-jmcnFbllk` and health is `https://ce-stg-nowlert.theriark.dev/api/health`.
- The Stage promotion must remain notification-silent: full tests run in an isolated network namespace and live verification remains passive/read-only.
- The Stage ledger remains the authoritative desired-state record used by finalization and drift verification.
- Production Reference application IDs, health URLs, ledger environments, workflow inputs, evidence fields, and drift checks are removed from the active chain.
- Historical release documentation for earlier versions may keep historical Production Reference records; current v3.1.3 and general deployment documentation must describe the new Stage-final chain.

## Finalizer contract

`finalize-release.yml` accepts:

- `version`
- `final_image`
- `source_commit`
- `development_run_id`
- `stage_promotion_run_id`
- `release_notes`

The finalizer must prove:

1. it is launched from `main`;
2. `main == stage == source_commit`;
3. source `VERSION` matches the requested release tag;
4. current release notes and QA checklist exist;
5. the Development run succeeded for the source commit and immutable digest;
6. the Stage promotion succeeded for the same source commit and immutable digest;
7. the Stage promotion logs contain the required silent-gate and passive-smoke evidence and no delivery-QA markers;
8. the live Stage Dokploy application is pinned to `final_image`;
9. the Stage ledger current record matches `final_image`, `source_commit`, and `stage_promotion_run_id`;
10. the requested tag and GitHub Release do not already exist.

Only after these checks may the workflow publish the annotated tag, GitHub Release, and release ledger record.

## Drift verification

Runtime drift verification becomes Stage-only. It compares the live Stage application with the Stage desired-state ledger and no longer references the removed Production Reference environment.

## Repository changes

Delete `.github/workflows/promote-production-reference.yml`.

Update the finalizer, release validator, ledger, drift verifier/workflow, CI workflow lists, current release documentation, documentation validator, and their tests so Production Reference is absent from the active v3.1.3 release path.

## Release execution after merge

Because release-pipeline files are part of the source commit provenance, after these changes merge to `development` a fresh immutable Development image must be built and promoted through Stage. Then `main` is fast-forwarded to that Stage-approved source and the Stage-only finalizer is dispatched. Stable GHCR/Docker Hub aliases are published only after finalization succeeds.

## Non-goals

- Do not modify application runtime behavior, database schema, parser/routing/destination/authentication behavior, or persistent-state layout.
- Do not reintroduce CE notification-delivery smoke infrastructure.
- Do not deploy directly to Production as part of this change.
- Do not rewrite historical release records for versions that actually used Production Reference.
