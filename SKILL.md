---
name: agent-team-workflow
description: Initialize, configure, operate, monitor, recover, and validate a portable multi-agent project workflow. Use when Codex needs to set up an agent team in a repository, create agent-team manifests and task records, coordinate agents across branches or worktrees and compute resources, maintain canonical task status, recover timed-out agents without losing external jobs, or package an existing team process for reuse.
---

# Agent Team Workflow

Build the team process from user-confirmed project facts. Keep planning records durable, execution isolated, resource use explicit, and acceptance evidence independent from an agent's self-report.

## Initialize A Project

1. Read repository instructions and inspect existing project-management files without writing.
2. Read [initialization-interview.md](references/initialization-interview.md) completely.
3. Conduct the interview incrementally. Do not write project files until every required topic has an answer, an explicit `unknown`, or an approved default and the user confirms the setup summary.
4. Read [resources-manifest.md](references/resources-manifest.md) when compute, repositories, environments, storage, networking, tools, or approval boundaries must be represented.
5. Render `assets/repo-template/` from the confirmed answers. Keep secret values out of files; record only environment-variable names, secret-manager references, or configured aliases.
6. Preview initialization with:

   ```bash
   python scripts/init_agent_team.py --repo <repo> --config <answers.yaml> --dry-run
   ```

7. Review the planned paths with the user when they alter an existing `AGENTS.md` or documentation tree. Initialize without `--dry-run` only after confirmation. Refuse overwrite; never use `--force` because the script intentionally has no such option.
8. Validate the installed folder with:

   ```bash
   python scripts/validate_agent_team.py --repo <repo> --docs-dir <docs-dir>
   ```

## Create And Assign Tasks

1. Read [operating-scheme.md](references/operating-scheme.md) and [task-lifecycle.md](references/task-lifecycle.md) before creating the first task or changing lifecycle policy.
2. Convert each goal into one measurable outcome with declared non-goals, owned paths, dependencies, resource budget, gates, stop conditions, and reviewer.
3. Create one durable task ID, task directory, branch/worktree when implementation isolation is needed, and canonical agent thread. Reuse that thread for retries and resumed work.
4. Keep management records in the canonical documentation checkout. Keep implementation changes in task-owned worktrees. Link reviewed commits, not uncommitted directories.
5. Assign high-conflict files and mutable registries to one writer at a time.
6. Start expensive or external work only after cheap checks, an inspected dry-run, a unique output path, and any required approval.

## Monitor And Recover

1. Track the agent process and its external job separately. Record `agent_state`, `external_job_state`, `last_verified_at`, `next_check_at`, resource reservation, process/job identifier, progress marker, and next gate.
2. Refresh the canonical status index at the configured cadence while work is active and immediately on lifecycle changes. Do not commit heartbeat-only refreshes unless project policy requires it.
3. On timeout or disconnect, verify the external job and artifacts read-only before acting. Resume the canonical agent thread when available.
4. Never infer that an agent timeout means its external process stopped. Never kill, replace, relaunch, delete, overwrite, push, deploy, or message external parties without authority recorded in the setup contract.
5. Create a replacement owner only when the canonical thread is unavailable and ownership transfer is explicit. Preserve the retired thread and job evidence.

## Evaluate And Close

1. Run gates from cheapest to most expensive: scope, static, unit, component smoke, integration, experiment, then publication/deployment as applicable.
2. Require an inspection report with exact commands, commits, environment, data identity, seeds, outputs, deviations, and residual risks.
3. Keep `phase` separate from portfolio `status`; use the definitions in [task-lifecycle.md](references/task-lifecycle.md).
4. Let the reviewer or manager accept work. An implementation agent may report completion but must not self-accept.
5. Integrate reviewed commits through the declared merge policy, record the integration revision, release resources, and archive only after acceptance.

## Maintain The Workflow

- Treat the setup answers and resources manifest as sources of truth. Amend them through explicit decisions rather than silently changing assumptions.
- Keep bulk logs, datasets, checkpoints, media collections, caches, PID files, and credentials outside Git. Retain compact reports, manifests, checksums, summaries, and selected figures.
- Run the validator after structural changes and before handing the workflow to another project.
- Prefer repository-relative durable links. Do not make canonical status depend on temporary worktree paths.
- Record waivers with approver, reason, risk, expiration, and follow-up.

## Resources

- [initialization-interview.md](references/initialization-interview.md): mandatory setup questions and confirmation contract.
- [resources-manifest.md](references/resources-manifest.md): portable resource and approval schema.
- [operating-scheme.md](references/operating-scheme.md): roles, worktrees, concurrency, monitoring, recovery, safety, and integration.
- [task-lifecycle.md](references/task-lifecycle.md): task documents, phase/status model, status index, reports, and evidence gates.
- `assets/repo-template/`: paste-ready repository files rendered by the initializer.
- `scripts/init_agent_team.py`: dry-run-first, collision-safe bootstrapper.
- `scripts/validate_agent_team.py`: read-only structural and policy validator.
