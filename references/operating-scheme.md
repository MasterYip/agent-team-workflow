# Agent-Team Operating Scheme

## Plan As A Task Graph

Decompose the project into bounded tasks with one primary verb and a measurable deliverable. Record dependencies and gates. Split exploratory work from production integration and split unrelated ownership surfaces.

Create a formal task only according to the user-confirmed trigger. Questions, status requests, and clarifications do not automatically create new task records unless configured otherwise.

## Assign Accountable Roles

| Role | Accountability |
|---|---|
| Manager | task graph, priorities, ownership, scope, acceptance, escalation |
| Task owner | declared implementation or analysis and self-verification |
| Experiment operator | dry-run, launch, monitoring, raw artifact handoff |
| Reviewer/evaluator | independent gates and acceptance recommendation |
| Integrator | merge queue, integration revision, post-merge checks |
| Resource steward | environments, compute, reservations, import origins |
| Registrar | shared experiment or result indexes |
| Documentation integrator | high-conflict reports, tables, figures, claims |

Allow one person or agent to hold multiple roles when necessary, but do not let a substantive task owner be the sole acceptor unless the setup contract records that exception.

## Isolate Work

- Use one task branch and one implementation worktree for code, configuration, paper source, or generated implementation assets.
- Keep task-management records in the canonical documentation checkout unless the setup contract specifies another single-writer location.
- Record base and candidate revisions, including nested repository revisions.
- Never create a worktree from a dirty or ambiguous base.
- Use worktree-local overlays or explicit source paths for development checks. Bind authoritative evaluation to a controlled checkout and environment.
- Reject imports that resolve into another agent's checkout.
- Integrate reviewed commits, never uncommitted worktree state.

## Control Concurrency

- Assign one owner per task and one writer per high-conflict file, mutable dataset, resource reservation, registry, or integration checkout.
- Parallelize independent code review, analysis, and immutable runs with unique resources and output paths.
- Serialize canonical environment mutation, integration checkout changes, shared index edits, and in-place dataset changes.
- Do not run a long job from an unrecorded mutable branch head.

## Reuse Canonical Agent Threads

Assign one canonical agent thread to a task and reuse it for follow-ups, monitoring, retries, and revisions. A timeout, disconnection, intermediate completion, or paused external job does not justify a replacement.

Replace a thread only after verifying that it is unavailable, checking for live external jobs, recording the prior owner state, and explicitly transferring ownership. Keep one current owner in live status; retain previous agent instances only as history.

## Monitor At Intervals

At each configured interval:

1. list current agents and reconcile one owner per task;
2. inspect external jobs through read-only process, scheduler, log, artifact, or heartbeat evidence;
3. update `agent_state` and `external_job_state` separately;
4. record `last_verified_at`, `next_check_at`, progress marker, resource, and next gate;
5. refresh the canonical status timestamp and totals;
6. escalate stale, conflicting, over-budget, or unsafe conditions.

Do not describe an agent as running solely because an old PID or screen name exists. Do not describe a task as stopped solely because the agent thread timed out. Prefer a terminal marker plus artifact validation over log wording alone.

## Recover Safely

Use this order:

1. Inspect thread, process/job, resource, log, output, and terminal marker read-only.
2. Resume the canonical thread with the exact task ID and current evidence.
3. If the external job is healthy, monitor it without relaunching.
4. If it failed, preserve partial artifacts and diagnose before proposing a bounded retry.
5. Obtain approval before termination, deletion, overwrite, transfer, deployment, or other external state change when required.
6. Use a new run ID and output path for a retry. Record relationship to the failed run.

## Gate Work Progressively

Run applicable gates in order:

1. scope: declared files, ownership, clean diff, no secrets or bulk artifacts;
2. static: parse, format, lint, syntax, types;
3. unit: focused deterministic tests;
4. component: bounded smoke and import-origin checks;
5. integration: controlled checkout/environment;
6. experiment: config, data, seed, metrics, artifacts, terminal marker;
7. publication/deployment: claim traceability or authorized safety checks.

Distinguish mandatory gates from diagnostics. Record waivers with approver, reason, risk, expiration, and follow-up.

## Hand Off And Integrate

Require a clean declared diff, candidate commits, inspection report, reproduction record, artifact inventory, residual risks, and rollback approach. Let the reviewer reproduce mandatory gates in the controlled environment. Return failed work to the same task for revision unless scope changes.

Order integration by dependency and risk. Record the integration revision and notify dependents when their base changes.

## Retain Evidence

Track compact manifests, decisions, checksums, aggregate metrics, reports, and selected figures. Store bulk datasets, checkpoints, raw traces, repeated media, caches, logs, PID files, and transfer bundles outside Git with durable paths and checksums.
