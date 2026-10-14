# LabWeft Adapter

One external research workspace belongs to one long-lived catalog project, not
one execution task. Keep the workflow package, LabWeft source, team records,
research records and dataset payloads separate. This branch generates explicit
command argument arrays and reads research records; it never imports or invokes
LabWeft automatically. Core Python remains 3.10+; backend commands need 3.11+.

Add this to the external configuration after registering the catalog project:

```json
{
  "adapters": {
    "labweft": {
      "tool_root": "/tools/LabWeft",
      "python": "/runtime/python3.12",
      "projects": {
        "project-alpha": {
          "workspace": "/research-workspaces/alpha",
          "project_id": null,
          "code": "/projects/alpha",
          "results": "/experiments/alpha"
        }
      }
    }
  }
}
```

`code/results` are optional for an existing workspace and required as applicable
for bootstrap planning. The bootstrap plan installs the backend controller Skill
in the external research workspace. Execute it only through the authorized external
task. Read `.research/manifest.json` and pin its generated `id` as `project_id` in
the external config before subsequent operations. A mismatch fails instead of
silently connecting a different project. Do not copy the research state into this
tool checkout or the task's temporary folder.

```sh
python -B /tools/agent-team-workflow/scripts/labweft_bridge.py --config /config/team.json --project project-alpha plan bootstrap
python -B /tools/agent-team-workflow/scripts/labweft_bridge.py --config /config/team.json --project project-alpha inspect
python -B /tools/agent-team-workflow/scripts/labweft_bridge.py --config /config/team.json --project project-alpha plan sync
python -B /tools/agent-team-workflow/scripts/labweft_bridge.py --config /config/team.json --project project-alpha checkpoint --output alpha/check-001.json --apply
python -B /tools/agent-team-workflow/scripts/labweft_bridge.py --config /config/team.json --project project-alpha inspect --checkpoint /team/agent_team/receipts/alpha/check-001.json
```

Commands are emitted as argv arrays, not shell command strings; the external
executor must pass them as arguments without shell interpolation. Other plan
operations are `context`, `validate`, `export`, and `apply --patch /external/file`.
Export targets the external runtime directory and does not include evidence text.
The runtime directory is created by core initialization. No model/GPU search,
publication, service startup or backup commands are generated.

## Authority And Freshness

The team catalog owns project identity and task bindings. LabWeft owns research
nodes, evidence and semantic history. Link by stable IDs; do not maintain editable
copies of the same graph in both places. Source code belongs in its own Git repo;
checkpoint payloads remain in their store. Record training-time code revision,
effective config and checkpoint SHA-256 in experiment manifests when required.

The bridge understands LabWeft schema 1 and checks its event hash chain without
executing source code. Compatibility was inspected against upstream revision
`366e0e89424ee0353210e6a80e0a8a6c56a43e81`. A schema change requires explicit adapter
review. This check is not the full backend validator and does not validate blobs.

Inspection hashes already indexed small source files (2 MiB/file, 32 MiB total,
up to 10,000 indexed entries). It flags changed or missing sources and their direct
node references. Binary/over-budget files are content-unverified; matching size
does not imply equal checkpoint contents. Unknown files are not discovered by this
bridge. Backend `sync` and an explicit expected-source inventory remain necessary.
Sources stored only as imported/synthetic snapshots may have no live source alias;
they are reported as unavailable for freshness checking, not as modified files.

A checkpoint is an immutable observation receipt selected explicitly on the next
inspection; the newest timestamp is not automatically authoritative. Changed event
revision/hash or source observations invalidate it. `unchanged_since_checkpoint`
means only those observations agree. `semantics_verified` stays false even when
no differences are found. This cannot prove all tasks/results were interpreted.

After source import, review affected summaries and conclusions, preserve unrelated
fields in LabWeft's full-object patches, validate and inspect the rendered map.
Transitive relations and missing edges require additional review. `plan apply`
rejects an already-stale semantic patch; the backend must recheck revision at actual
execution. Read-only plans never execute their generated commands.

Raw research metadata can contain private content. Evidence blobs are ignored by
LabWeft's Git defaults; arrange backup separately, and never treat a copied event
index or exported graph as a checkpoint/data backup.
