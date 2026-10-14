# SFTR / ProjectKeeper Adapter

Use this branch for a workspace whose project datasets live in SFTR. The core
still owns bounded tasks and their project bindings; SFTR keeps long-lived files
in the user's existing layout. Do not initialize another ProjectKeeper project
inside a task's scoped subfolder.

Add this block to an external v2 configuration, adjusting host-specific paths:

```json
{
  "stores": {
    "sftr-local": {"root": "/absolute/path/to/SFTR", "access": "reference"}
  },
  "adapters": {
    "sftr": {
      "stores": ["sftr-local"],
      "projectkeeper_root": "/absolute/path/to/ProjectKeeper"
    }
  }
}
```

Register the parent project in the external catalog, for example store-relative
`2 Project/ProjectName`. Bind a task's `scope` to the actual working subfolder.
Change store access to `maintain` only when applicable; write rules and active
task authorization remain necessary. Store access alone grants no task writes.

```sh
python -B /tools/agent-team-workflow/scripts/sftr.py --config /config/team.sftr.json inspect --project project-id
python -B /tools/agent-team-workflow/scripts/workflow.py --config /config/team.sftr.json plan --binding binding-id --path talk.pptx --operation update
python -B /tools/agent-team-workflow/scripts/sftr.py --config /config/team.sftr.json backup-handoff --project project-id
```

Inspection directly reads selected fields from `.projectcfg`. `_CacheInfo` is
recognized without migration or execution. ProjectKeeper is never imported:
some legacy constructors can save a converted configuration during loading.
The adapter does not recursively scan SFTR, invoke backup, write project metadata,
copy files, or turn recorded backup dates into verified backup status.

The common `plan` command enforces adapter protection as well: `.projectcfg` and
`_CacheInfo` cannot be ordinary task write targets; `_Temp` cannot receive promoted
durable releases. Existing `_Event Records` entries are immutable for adapter
planning: use a new entry name for revisions. This reflects the inspected backend
which recognizes new event entries by their top-level names. `_Extension Package`
can contain maintained dependencies, but old-file backup retention must be checked.

## External Execution And Recovery

Work in an external task copy, preserve editable sources and native links, validate
the final package, and recheck destination base hashes before the authorized write.
Save a compact delivery receipt in workspace records. The ProjectKeeper backup
unit is the registered parent project, even when the task changed one subfolder.
Hand off exact affected files and their hashes to the backend operator.

Keep backup `planned/pending` until external execution and verification exist.
The inspected backend can advance metadata before completing its archive and can
reuse a date-based archive name. Inspect destination collisions, archive validity
and restored content. A successful delivery is not a successful backup.

No actual backup command is fabricated in the plan. Backend revision, destination,
scope and retention are workspace choices; inspect the configured installation
before execution. User-approved backend changes may require adapting these checks.
