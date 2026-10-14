# Workspace Records

This directory belongs to this workspace, not to the workflow tool repository.
Keep the machine configuration outside this directory. Use the workflow tool's
`scripts/workflow.py --config /absolute/path/to/config.json` from this workspace.

- `workspace.json`: stable workspace identity.
- `catalog/events/`: authoritative project and task-binding metadata. Update with
  the CLI and an expected revision. Do not edit events or maintain a second catalog.
- `tasks/`: bounded task manifests, source scripts, decisions and inspection reports.
- `task_status.md`: authoritative task portfolio; it does not duplicate project state.
- `resource_status.md`: resource reservations and external job records.
- `receipts/`: compact external file maintenance, release and backup evidence.

Copy `tasks/_template/` to a task directory and fill its manifest before binding.
Keep task IDs unique within this workspace; carry workspace ID in cross-workspace
references. Retain the same task identity on retry or continuation.

The CLI checks records and generates plans. It does not execute dataset transfers,
backups, training, publication or recurring jobs. Accepted outputs and their native
dependencies belong in the registered long-lived project store. Keep drafts and
generated intermediates in ignored task folders or the configured runtime directory.

Metadata history is a local hash-linked event log, not a replacement for Git or
backup. Track compact records in your workspace's repository if configured; back
up payloads separately. Inspect current instructions and configured policy before
each external operation. No background agent or scheduler is installed.
