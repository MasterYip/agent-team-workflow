#!/usr/bin/env python3
"""Run from an external workspace with an absolute script path and explicit config."""
import sys

sys.dont_write_bytecode = True

import argparse
import json
from workspace_core import WorkflowError, apply_change, binding_plan, initialize, load_catalog, load_config, read_json, validate_state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, help="External machine-local JSON configuration")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="Preview external workspace creation")
    init.add_argument("--apply", action="store_true")
    sub.add_parser("validate", help="Read-only configuration and catalog checks")
    sub.add_parser("status", help="Read the authoritative project/binding catalog")
    update = sub.add_parser("update", help="Preview field-level catalog changes")
    update.add_argument("--patch", required=True)
    update.add_argument("--apply", action="store_true")
    plan = sub.add_parser("plan", help="Resolve one binding and optionally inspect one target")
    plan.add_argument("--binding", required=True)
    plan.add_argument("--path")
    plan.add_argument("--operation", default="read", choices=["read", "create", "update", "promote", "rename", "delete"])
    args = parser.parse_args()
    try:
        env = load_config(args.config)
        if args.command == "init":
            result = initialize(env, args.apply)
        elif args.command == "update":
            result = apply_change(env, read_json(args.patch), args.apply)
        elif args.command == "plan":
            result = binding_plan(env, args.binding, args.path, args.operation)
        else:
            last, _ = load_catalog(env)
            result = {"record_integrity": True, "revision": last["revision"], "workspace": env["data"]["workspace"]["id"]}
            if args.command == "validate":
                validate_state(env, last["state"])
                result["valid"] = True
            if args.command == "status":
                result["catalog"] = last["state"]
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
