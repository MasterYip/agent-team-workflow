# {{PROJECT_NAME}} Agent Team Scheme

## Objective

{{PROJECT_OBJECTIVE}}

## Sources Of Truth

Use this precedence unless the confirmed setup says otherwise:

1. Current user direction and accepted task-manifest amendments.
2. Repository `AGENTS.md` files in scope.
3. This setup contract and resource manifest.
4. Component-specific instructions and accepted historical examples.

Resolve conflicts before continuing. Do not silently choose the most convenient instruction.

## Task Model

Manage work as a dependency graph. Give each formal task one measurable outcome, one owner, one canonical agent thread, one reviewer, one durable task directory, and one implementation branch/worktree when code or source assets change.

Formal task trigger: **{{FORMAL_TASK_TRIGGER}}**.

Keep `phase` separate from portfolio `status`:

- phase: `proposed`, `ready`, `active`, `review`, `evaluation`, `accepted`, `integrated`;
- status: `running`, `waiting`, `blocked`, `completed`, `archived`, `superseded`.

## Roles And Ownership

The setup contract defines the manager, owners, reviewers, integrator, resource steward, and any single-writer roles. One person or agent may hold several roles, but a substantive task owner must not be the sole acceptor unless the setup records that exception.

Assign exclusive ownership for high-conflict files, mutable datasets, registries, canonical environments, evaluation checkouts, and resource reservations.

## Worktrees And Integration

Use task worktrees for implementation changes. Keep management records in this canonical documentation location. Record base, candidate, nested-repository, and integration revisions. Never integrate uncommitted worktree state.

Use a controlled integration/evaluation checkout for authoritative checks when environment or source-origin ambiguity is possible. Reject project imports that resolve outside the intended checkout.

## Gates

Run applicable gates from cheapest to most expensive:

1. declared scope and clean diff;
2. parse, format, lint, syntax, and type checks;
3. focused deterministic unit tests;
4. bounded component smoke and source-origin checks;
5. controlled integration evaluation;
6. registered experiment with config, data, seed, resource, and artifact provenance;
7. deployment or publication evidence.

Record mandatory versus diagnostic gates. Record waivers with approver, reason, risk, expiration, and follow-up.

## Monitoring And Recovery

Agent concurrency setting: **{{MAX_AGENTS}}**. Regardless of whether the configured value is numeric or unlimited, start work only within the resource, ownership, and approval constraints in the setup contract. Refresh status every **{{STATUS_CADENCE_MINUTES}} minutes** during active work and immediately at lifecycle changes.

Track agent state and external-job state separately. Record last verification, next check, resource, process/job ID, progress or terminal marker, next gate, and blocker.

Reuse the canonical agent thread after timeout, disconnection, retry, or revision. Before replacement or relaunch, verify external jobs and artifacts read-only. Never assume a timed-out agent stopped its job.

## Authority Boundaries

- Commit policy: {{COMMIT_POLICY}}
- Push policy: {{PUSH_POLICY}}
- Destructive/process-termination policy: {{DESTRUCTIVE_ACTION_POLICY}}
- External action, network, transfer, message, and deployment policy: {{EXTERNAL_ACTION_POLICY}}

Never expose credentials or private connection details. Never terminate, delete, overwrite, transfer, deploy, push, or contact external parties beyond confirmed authority.

## Evidence And Retention

Require a goal manifest before assignment and an inspection report at handoff. Owners report completion; reviewers or the manager accept. Use repository-relative durable links.

Keep compact reports, manifests, checksums, aggregate data, scripts, and selected figures in Git. Keep datasets, checkpoints, raw traces, repeated media, caches, runtime logs, PID/status files, and transfer bundles in durable artifact storage with identity and checksums.

## Archived Task Organization

Keep active lifecycle records directly under `tasks/YYYYMMDD_TASK-ID/`. Only when a
task's portfolio status changes to `archived`, move its complete durable directory to:

```text
tasks/archived/<classname>/YYYYMMDD_TASK-ID/
```

Derive `<classname>` from the broad leading task-ID prefix before the first
hyphen: `ENV-VIS-015`, `ENV-REJECT-006`, and `ENV-TORSO-007` all belong to
`ENV`; `RL-SMOKE-002` belongs to `RL`; and `DOC-001` belongs to `DOC`. Do not
create a class directory for each narrow task family. Keep the dated
task-directory name unchanged so history and provenance remain recognizable.

Perform the move in the same lifecycle update that marks the task archived. Update
every canonical relative link in `task_status.md` and any dependency, experiment,
decision, or claim-evidence record. Keep exactly one task directory; do not leave a
copy at the old path. Never move `running`, `waiting`, `blocked`, `completed`, or
`superseded` tasks into the archive tree, and do not archive a task with a live
external job or an unresolved integration gate.

## Documentation And Visualization

Use Mermaid for dependency graphs, lifecycle/state flows, architecture, data flow, ownership, and recovery sequences when the relationships are easier to verify visually. Use LaTeX for objectives, constraints, metrics, state/condition parameterizations, and other mathematical contracts.

Every diagram and equation must match the recorded implementation or be labeled clearly as proposed. Keep Mermaid readable in source form, define mathematical symbols locally, and retain exact commands, revisions, configurations, and acceptance evidence in text or tables. Visuals explain the work; they do not replace executable evidence.

Prefer one focused visual over several decorative or repetitive diagrams. Update or remove visuals when the underlying contract changes.

## Status Maintenance

Maintain exactly one canonical row per task ID in `task_status.md`. Maintain current reservations and jobs in `resource_status.md`. Do not create dated progress snapshots unless the confirmed setup or user requests them. Do not commit heartbeat-only timestamp updates unless the commit policy requires it.
