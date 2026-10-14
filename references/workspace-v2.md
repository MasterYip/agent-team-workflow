# External Workspaces (V2)

## Boundaries

The checkout is a reusable tool/Skill distribution. Normal use only reads it.
Workspace configuration, task records, runtime files, receipts and research state
belong outside it. One checkout serves many workspaces; a new task does not clone
the workflow or create a fresh long-lived project. Python 3.10+ is sufficient for
the core. JSON is the dependency-free configuration format.

All paths in examples are illustrative. The initializer only writes external
workspace records with `--apply`; it never creates a Git repository, edits a
project's AGENTS.md, runs shell commands, moves datasets or starts services.
Use an existing user's authorization; do not repeat a setup interview when the
facts and scope are already established. Unresolved configuration only blocks the
operations that depend on it.

## Initialization

From the target workspace, create a machine-local configuration based on
`assets/workspace.example.json`. Set absolute host paths and stable workspace,
repository and store IDs. Keep private locations out of shared source control.
An external config may be shared deliberately when its paths are non-sensitive;
it is never copied into generated tracked records.

```sh
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json init
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json init --apply
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json validate
```

The first command previews exact paths with no writes. Initialization refuses all
existing destination files; there is no force or merge mode. Interrupted creation
may leave a partial directory. Inspect it and use a fresh destination or reconcile
explicitly; do not automatically delete existing records. Do not bootstrap v2 into
an existing v1 directory. Inventory and map its IDs first, then migrate in a bounded
task. V1's original `init_agent_team.py` and validator remain for existing installs.

Keep `records` and `runtime` disjoint and outside the tool checkout; datasets must
not overlap either. A store defaults to `reference`. Changing a machine path is a
deliberate relocation: verify the intended project's identity before reusing IDs.
The path resolver proves containment, not that two similarly named datasets are
the same project. It follows resolved paths to reject junction/symlink escapes;
it is not a sandbox against a concurrent filesystem attacker.

## Authority And Records

Task manifests and `task_status.md` remain authoritative for task execution and
lifecycle. The catalog owns project records and task-to-project bindings, not a
second task state. References combine workspace ID and task/project ID; unrelated
workspaces do not share a mandatory numeric task sequence.

Projects contain `label`, `store`, store-relative `path`, `steward`, `lifecycle`
(`active`, `dormant`, `archived`), optional `protected` project-relative paths and
`maintenance` notes. Use stable IDs independent of folder names.

Bindings contain `task_id`, records-relative `task_manifest`, `project`, project-
relative `scope`, `roles`, `state`, `writes` and `authorization`. Roles are
`reference`, `maintain`, `promote`; states are `proposed`, `active`, `retired`.
Active scopes must exist and their project must be active. A reference-only store
cannot have writable bindings. Each write rule has a scope-relative `path`, a
`recursive` boolean and operations from `create/update/promote/rename/delete`.
Rules describe scope, not commands to execute. Protected paths override write
rules. The plan validates an exact requested target; broad rules can contain
protected children which remain forbidden. Check both source and destination for
rename operations. Never bypass backend-owned metadata with broad folder rules.

Copy and complete the task manifest before registering its binding. Initial
examples are in `assets/project-change.example.json` and
`assets/binding-change.example.json`; edit external copies, not package assets.

```sh
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json status
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json update --patch /work/register.json
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json update --patch /work/register.json --apply
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.json plan --binding binding-task-001 --path talk.pptx --operation update
```

## Metadata Changes And History

Changes use an expected `base_revision`, unique `change_id`, reason, and a list of
`{collection, id, set}` operations. `set` changes only supplied top-level fields;
omitted fields survive. List/object field values replace that field completely.
Unknown fields are rejected. Retire records rather than deleting provenance.

Updates are previews unless `--apply` is explicit. Actual writes recheck state
under an OS file lock at `catalog/.writer.lock` in external records (Git-ignored).
Its location follows the catalog, so two configurations cannot choose independent
locks for the same records. An immutable event contains
the complete resulting compact catalog, prior event hash and request digest. The
same change ID and request is idempotent; reuse with different content fails.
Keep event bytes unchanged. Git can version compact records independently.

The event chain and lock detect ordinary corruption and stale writes, not malicious
tampering, cross-machine/NFS coordination or scientific errors. Full snapshots are
intended for small catalogs, not per-step training logs. There is no automatic
compaction, migration or distributed merge. Initialize separate workspaces for
independent teams and explicitly reconcile shared dataset writes.

`validate` checks the catalog and current path/manifest references. It does not
prove task acceptance, authorizations, backup recovery, completed file transfers
or experiment correctness. A passed metadata update does not execute the plan.
`status` can read intact records while a store is offline; this does not validate
local availability. Retired bindings retain historical manifest paths even after
task archival. Active bindings must resolve when validating or applying changes.

## Dataset Maintenance

Resolve the binding, inspect exact files and capture base hashes. Produce drafts
in ignored task work/runtime folders. The external executor rechecks base identities
and shared path reservations immediately before applying any authorized change.
For native documents retain editable sources and linked dependencies. Promote an
accepted immutable release or use a recoverable working-file update; record exact
paths/hashes, binding/catalog revision, source task, validation and acceptance.

Write compact receipts under `receipts/<operation-id>.json` and reference them
from the task. A current pointer is keyed by artifact and variant (language,
audience, format), not by latest timestamp. Keep backup status independently
`pending`, `verified`, `failed` or `not-required`; verified requires backend and
restore/hash evidence. Project backlog and stewardship outlive task closure.

This release supplies contracts and read-only target planning, not a file-copy or
backup engine. It never claims atomicity across multiple files or volumes. External
execution must maintain staged/applied/indexed receipts and recover interrupted
operations by operation ID without overwriting newer human changes.

## Adapter Branches

`feat/workflow-v2` is provider-neutral. `feat/workflow-sftr` and
`feat/workflow-v2-labweft` are independent descendants. Only enable an adapter if
its module exists in the selected checkout; core rejects unsupported settings.
Adapters validate external config and produce read-only observations/plans. They
do not install their backends or execute commands from config. Branch-specific
configuration belongs in external files; no personal paths are baked into code.
