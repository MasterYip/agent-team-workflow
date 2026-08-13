# Agent-Team Artifact Retention

## Keep In Git

- goal manifests, decisions, protocols, inspection and evaluation reports;
- small configuration, checksum, inventory, validation, and aggregate data files;
- scripts needed to reproduce checks;
- a small number of selected summary figures.

## Keep Outside Git

- datasets, checkpoints, model weights, tensor dumps, and raw traces;
- per-run or per-cell rollout trees;
- videos, repeated frames, caches, virtual environments, and package stores;
- runtime logs, PID/status files, terminal captures, transfer bundles, and temporary staging.

For every external artifact, record its durable location, task/run ID, source revision, checksum or immutable identity, inventory, validation state, retention owner, and privacy classification.

Never commit credential values, private keys, tokens, cookies, private host details, or unapproved private data.
