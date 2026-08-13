# Agent Team Initialization

This folder is a portable agent-team control surface for **{{PROJECT_NAME}}**.

## Mandatory Setup Gate

Before changing project files, launching agents, reserving resources, or starting external work:

1. Read applicable repository instructions and inspect existing project-management files read-only.
2. Ask the user the setup questions incrementally:
   - repository and documentation destination;
   - project objective, non-goals, repositories, branches, worktrees, and integration strategy;
   - task trigger, roles, ownership, reviewer independence, and concurrency;
   - local/remote compute, GPUs, environments, storage, path mappings, network, and secret references;
   - setup, test, build, experiment, deploy, and rollback commands;
   - budgets, status cadence, terminal markers, and acceptance thresholds;
   - commit, staging, push, destructive-action, process-termination, transfer, deployment, and external-message policies;
   - task, report, artifact, decision, and claim-evidence locations.
3. Record unknowns explicitly and explain what each unknown blocks.
4. Present the resolved setup summary and exact planned files.
5. Obtain user confirmation.
6. Render `setup_answers.yaml` and `resources_manifest.yaml`; validate this folder before starting tasks.

Do not infer authority from tool access. Store secret references such as `env:NAME` or configured aliases, never secret values.

## Current Setup

- Project: {{PROJECT_NAME}}
- Objective: {{PROJECT_OBJECTIVE}}
- Repository: {{REPOSITORY_PATH}}
- Documentation root: {{DOCS_DIR}}
- Formal task trigger: {{FORMAL_TASK_TRIGGER}}
- Agent concurrency setting: {{MAX_AGENTS}}
- Status cadence: every {{STATUS_CADENCE_MINUTES}} minutes while work is active
- Confirmed by: {{CONFIRMED_BY}}
- Confirmed at: {{CONFIRMED_AT}}

Use `agent_team_scheme.md` for operation, `task_status.md` for canonical portfolio state, `resource_status.md` for reservations and external jobs, and `tasks/_template/` for task records.
