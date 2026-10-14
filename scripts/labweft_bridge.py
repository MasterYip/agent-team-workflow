#!/usr/bin/env python3
"""Inspect an external LabWeft workspace, checkpoint observations, or print argv."""
import sys
sys.dont_write_bytecode = True

import argparse
import json
from pathlib import Path
from adapter_labweft import command_plan, inspect_project
from workspace_core import WorkflowError, load_config, outside_package, resolve_under, within


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--project", required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    inspect = sub.add_parser("inspect")
    inspect.add_argument("--checkpoint", help="Explicit previously captured observation JSON")
    plan = sub.add_parser("plan")
    plan.add_argument("operation", choices=["bootstrap", "sync", "context", "validate", "export", "apply"])
    plan.add_argument("--patch")
    capture = sub.add_parser("checkpoint", help="Capture an observation, not scientific acceptance")
    capture.add_argument("--output", required=True, help="New records-relative receipt filename")
    capture.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    try:
        env = load_config(args.config)
        if args.command == "plan":
            result = command_plan(env, args.project, args.operation, args.patch)
        else:
            result = inspect_project(env, args.project, getattr(args, "checkpoint", None))
            if args.command == "checkpoint":
                from workspace_core import require
                require(result["initialized"], "No initialized workspace to checkpoint")
                target = resolve_under(env["records"] / "receipts", args.output)
                outside_package(target)
                require(within(target, env["records"]), "Receipt path escapes workspace records")
                require(not target.exists(), "Checkpoint receipt already exists; select a new identity")
                if args.apply:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with target.open("x", encoding="utf-8") as handle:
                        json.dump(result, handle, ensure_ascii=False, indent=2)
                result = {"output": str(target), "applied": args.apply, "observation": result}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
