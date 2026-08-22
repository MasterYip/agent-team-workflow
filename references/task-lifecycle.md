# Task Lifecycle And Records

## Keep Task IDs Globally Unique

A logical task ID is immutable and unique across the project's complete history. The terminal numeric serial is project-global, not prefix-local: allocate one monotonically increasing, zero-padded sequence across all task classes. If `ENV-VIS-015` exists, no `RL-*`, `DOC-*`, or other task may reuse `015`. Before creating a task, search the canonical index, active and archived task directories, goal manifests, progress snapshots, decision records, and any migrated legacy register for both the full ID and serial. Never issue an ID or serial that appears anywhere in those records.

Do not recycle IDs from completed, archived, superseded, rejected, cancelled, or deleted work. Retain the historical record. A retry, revision, resumed agent, or replacement owner continues under the original task ID, directory, and canonical thread. When the objective is materially different, create a new ID and record `depends on`, `supersedes`, or another explicit relationship.

The descriptive task prefix and date prefix in `YYYYMMDD_TASK-ID` cannot make a repeated terminal serial unique. If a duplicate is discovered, stop new assignment, preserve both records, and let the manager perform an explicit, user-approved reconciliation with a durable legacy-to-canonical mapping rather than silently renumbering accepted history.

## Keep Phase And Status Separate

Use `phase` for workflow progression:

`proposed -> ready -> active -> review -> evaluation -> accepted -> integrated`

Use `status` for the portfolio view:

| Status | Meaning |
|---|---|
| `running` | An agent or external job is actively advancing the task |
| `waiting` | Ready or partially complete but queued for a resource, reviewer, or non-blocking decision |
| `blocked` | No meaningful progress is possible until a named condition changes |
| `completed` | Contracted deliverables and task-owner checks are complete |
| `archived` | Accepted work is preserved and has no active action |
| `superseded` | Replaced or rejected work is retained for provenance |

Examples: a task may have `phase: review` and `status: waiting`; an external run may leave `phase: active` and `status: running` while its agent thread is waiting.

## Goal Manifest

Create the goal manifest before assignment. Require:

- task ID, title, phase, status, owner, reviewer, repository, branch/worktree, base revision, dependencies, priority, budget;
- measurable objective, hypothesis/background, in-scope deliverables, non-goals;
- owned paths and permissions;
- instruction sources, data/checkpoint/environment/resource identities;
- acceptance requirements with command, threshold, and evidence location;
- staged execution plan, risks, stop/escalation conditions;
- decision log and ready-to-start approval.

Treat undeclared file or external-system changes as unauthorized scope expansion until the manager amends the manifest.

## Inspection Report

Require:

- owner-reported outcome and independent acceptance state;
- base, candidate, nested, and integration revisions;
- deliverables and changed files;
- exact verification commands and all results, including skipped or failed checks;
- reproduction record: revisions, dirty state, environment/import origins, hardware, dataset identity, resolved configuration, seeds, command, output/run IDs;
- acceptance comparison, deviations, residual risks, artifact inventory;
- integration and non-destructive rollback guidance;
- independent evaluator context, evidence, and decision.

An owner may report `complete`; only the designated acceptor records `accepted`.

## Canonical Task Index

Maintain exactly one row per globally unique task ID. Group rows by status instead of mixing lifecycle states. Include a local timestamp and totals. Refresh immediately on lifecycle changes and at the configured cadence while any task is running.

Each row must contain:

- task ID and compact evidence-backed headline;
- current phase, owner, and external job state;
- key result, revision, or progress marker;
- deviations or blockers;
- one bounded next gate;
- durable repository-relative links to the manifest and latest report.

Do not list sequential replacement agent instances as separate tasks. Do not use temporary worktree paths as canonical evidence links.

## Live Agent And Resource Status

Track one current owner per task with:

| Field | Required content |
|---|---|
| Agent | Stable current thread or owner |
| Task | One task ID or coordination |
| Agent state | `active`, `waiting`, `blocked`, `awaiting_review`, `completed`, `superseded`, or `disconnected` |
| External job state | `none`, `planned`, `starting`, `running`, `succeeded`, `failed`, `unknown`, or `stopped` |
| Evidence | Revision, progress count, terminal marker, validated artifact, or process probe |
| Resource | Reservation ID, host/pool ID, unit/index, process/job ID |
| Last verified | Timestamp of the evidence |
| Next check | Configured next verification time |
| Next gate/blocker | One bounded action or exact release condition |

Historical, timed-out, errored, or superseded agent instances belong in task evidence, not the live table.

## Progress Snapshots

Create dated snapshots only when the setup contract or user requests them. Keep snapshots immutable after publication except for explicit corrections. Include separate live-agent and task-progress tables, timestamp, totals, revisions, results, next actions, blockers, resources, and durable materials.

## Task Directory

Use the configured naming convention. A date-prefixed example is:

```text
agent_team/tasks/YYYYMMDD_TASK-ID/
  goal_manifest.md
  inspection_report.md
```

Keep the date prefix immutable. It does not make a repeated logical ID unique. Revisions, retries, resumed agents, and replacement owners reuse the same directory and task ID.

## Evidence Rules

- Use exact revisions, resolved configs, immutable/checksummed data, seeds, environment fingerprints, run IDs, raw metrics, aggregation scripts, and regenerated figures for research claims.
- Label preliminary, diagnostic, validated, accepted, and negative results distinctly.
- Record exclusions and failed runs, not only the best result.
- Keep compact evidence in Git and bulk evidence in durable storage with inventory and checksums.
- Record every scope, dataset, baseline, threshold, budget, or protocol change in the decision log.
