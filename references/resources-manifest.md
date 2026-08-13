# Resources Manifest

Keep static inventory separate from dynamic reservations. Store only portable identities, configured aliases, path mappings, capabilities, constraints, and secret references.

## Static Schema

```yaml
schema_version: 1
project: example-project
repositories:
  - id: main
    role: implementation
    local_path: /path/from-confirmed-setup
    canonical_branch: main
    worktree_root: ../example-worktrees
    integration_branch: integration
environments:
  - id: canonical-python
    kind: conda
    executable: /confirmed/path/python
    mutable_by: environment-steward
    origin_checks: [python_executable, import_paths, lock_hash]
hosts:
  - id: gpu-primary
    connection_alias: configured-ssh-alias
    roles: [compute, artifact-storage]
    path_maps:
      - local: /local/data
        remote: /remote/data
compute_pools:
  - id: training-gpus
    host: gpu-primary
    accelerator: gpu
    count: 8
    memory_gib: 24
    scheduler: configured-launcher
storage:
  - id: durable-artifacts
    path: /confirmed/artifact/root
    retention: immutable-by-run-id
network:
  default: denied-unless-task-authorized
  allowed_operations: [configured-package-mirror]
secrets:
  - id: experiment-tracker
    reference: env:EXPERIMENT_API_TOKEN
    permitted_consumers: [experiment-launcher]
tools:
  - id: test
    command: "project-specific test command"
approval_boundaries:
  terminate_process: explicit-user-approval
  push: explicit-user-approval
  deploy: explicit-user-approval
  external_message: explicit-user-approval
  destructive_filesystem: explicit-user-approval
budgets:
  default_wall_hours: 2
  default_gpu_hours: 0
  default_storage_gib: 1
validated_at: "2026-01-01T12:00:00Z"
validated_by: manager
```

Use `unknown` for unresolved values. Do not fabricate availability, paths, capacity, or permission.

## Dynamic Reservation Schema

Keep reservations in `resource_status.md` or an equivalent mutable ledger:

| Field | Meaning |
|---|---|
| Reservation ID | Globally unique task/run identity |
| Task | Owning task ID |
| Resource | Manifest resource ID and unit/index |
| Owner | Current accountable agent or operator |
| State | `planned`, `reserved`, `active`, `released`, or `failed` |
| Start / expiry | Confirmed timestamps and lease boundary |
| Process/job ID | External identifier; never a credential |
| Last verified | Time and evidence used to verify state |
| Output path | Unique durable run path |
| Release condition | Terminal marker, approval, or explicit time |

Never infer that an expired heartbeat released a GPU. Probe the scheduler or process state read-only and record uncertainty.

## Portability Rules

- Use IDs in task files and resolve them through the manifest.
- Keep host connection details in configured aliases, not tracked IP addresses.
- Keep secret values outside Git; record `env:NAME`, `keyring:ENTRY`, or a secret-manager URI.
- Represent cross-host paths explicitly. Reject unresolved symlinks and implicit mount assumptions before launch.
- Record environment executable and import origins for authoritative runs.
- Give each run a unique artifact path containing task ID, commit, and run ID.
- Make datasets immutable once referenced by accepted evidence; create a new identity for revisions.

## Resource Preflight

Before external or expensive work, verify:

1. task authority and budget;
2. repository revision and clean/declared diff;
3. environment and import origins;
4. dataset identity and path mapping;
5. resource availability and reservation ownership;
6. dry-run command, unique output path, seed, and terminal marker;
7. monitoring cadence and stop/escalation conditions;
8. explicit approval for any transfer, deployment, termination, or destructive action.
