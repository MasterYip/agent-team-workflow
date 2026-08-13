# Initialization Interview

Use this interview before writing agent-team files into a project. Ask one compact group at a time, reflect the answers, and let the user correct them. Do not silently infer authority from available tools or infrastructure.

## 1. Destination And Existing Instructions

Ask:

- Which repository is in scope, and where should agent-team documentation live?
- Should the workflow integrate with an existing root or nested `AGENTS.md`? May the initializer create one when absent, emit a marked fragment, or leave instructions untouched?
- Which existing instructions, contribution guides, architecture docs, or task trackers take precedence?
- Is this a greenfield setup, a migration, or coexistence with another workflow?

Inspect the repository read-only. Report collisions, dirty state, nested repositories, and existing task IDs before proposing writes.

## 2. Project And Repository Topology

Ask:

- What outcome is the team pursuing, and what is explicitly out of scope?
- Which repositories, submodules, nested repositories, paper repos, services, or data repos participate?
- What are the canonical branches, branch naming rules, worktree roots, integration branches, and merge strategy?
- Which changes may be made directly in the main checkout, and which require task worktrees?
- What files or registries need exclusive single-writer ownership?

Record repository identities and path aliases. Do not assume that local and remote paths match.

## 3. Roles And Concurrency

Ask:

- Who acts as manager, task owner, reviewer/evaluator, integrator, resource steward, experiment registrar, or deployment approver?
- How many agents and external jobs may run concurrently?
- Should formal task records be created for every change or only on an explicit trigger such as "new task" or "send an agent"?
- How should timed-out or disconnected agent threads be resumed or replaced?
- Which files, datasets, registries, and environments must be serialized?

Require one accountable owner and a distinct acceptor for each substantive task unless the user explicitly approves a small-project exception.

## 4. Compute, Storage, Network, And Secrets

Ask:

- Which local machines, remote host aliases, CPU/GPU pools, queues, containers, environments, and schedulers are available?
- How are GPU indices reserved, probed, released, and audited? What wall-time, memory, storage, API, or cost budgets apply?
- Where do source, datasets, checkpoints, logs, temporary files, and durable artifacts live on each host?
- Which network operations are allowed? Which require approval?
- Which credentials are needed, and how are they referenced without storing values?

Record configured aliases and secret references only. Never record raw IP addresses, private keys, access tokens, passwords, cookies, or credential values.

## 5. Commands And Quality Gates

Ask:

- What are the authoritative setup, format, lint, type-check, unit-test, integration-test, build, experiment, deploy, and rollback commands?
- Which commands are cheap enough for every task, and which require scarce resources or approval?
- What constitutes a smoke test, terminal success marker, accepted metric, or failure threshold?
- Which environment/import-origin, dataset, seed, config, commit, and artifact fingerprints are mandatory?

Do not invent commands. Record unknown commands as blocking setup gaps.

## 6. Governance And Communication

Ask:

- What status heartbeat and user-update cadence should apply?
- What commit cadence, commit style, staging policy, push policy, and branch-protection rules apply?
- Which destructive actions, process termination, deployments, external messages, purchases, or data transfers require approval?
- Where should task manifests, inspection reports, decisions, progress snapshots, and claim-evidence records live?
- What artifact retention, privacy, licensing, and compliance rules apply?

Separate permission to edit local task files from permission to push, deploy, transfer data, terminate jobs, or contact people.

## 7. Confirmation Gate

Present a concise setup summary containing:

- destination and instruction precedence;
- project goal and repository topology;
- roles, concurrency, and formal-task trigger;
- resource inventory and budgets;
- commands and gates;
- status cadence and documentation paths;
- commit, push, destructive-action, network, deployment, and secret policies;
- unresolved questions and proposed defaults;
- exact files the initializer will create or modify.

Ask the user to confirm or amend the summary. Write an answers file only after confirmation. If a required answer remains unknown, record `unknown` and state which work it blocks.

## Answers File Contract

Provide the initializer a YAML or JSON mapping with these required top-level keys:

```yaml
project:
  name: example-project
  objective: "Deliver the confirmed project outcome"
  repository: /absolute/path/to/repository
workflow:
  docs_dir: agent_team
  formal_task_trigger: explicit
  status_cadence_minutes: 10
  max_agents: 3
  commit_policy: "Batch coherent reviewed changes"
  push_policy: "Require explicit approval"
  destructive_action_policy: "Require explicit approval"
  external_action_policy: "Require explicit approval"
  agents_integration: fragment
resources:
  manifest_file: resources_manifest.yaml
documentation:
  task_dir: tasks
  progress_dir: progress_reports
confirmation:
  confirmed_by: user
  confirmed_at: "2026-01-01T12:00:00Z"
```

Use `agents_integration: fragment`, `create`, or `none`. `fragment` emits a reviewable `AGENTS.md.agent-team.fragment`; `create` creates `AGENTS.md` only when absent; `none` leaves repository instructions untouched.
