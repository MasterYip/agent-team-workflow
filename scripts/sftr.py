#!/usr/bin/env python3
"""Read-only SFTR inspection and external backup handoff planning."""
import sys
sys.dont_write_bytecode = True

import argparse
import json
from adapter_sftr import backup_handoff, inspect_project
from workspace_core import WorkflowError, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("command", choices=["inspect", "backup-handoff"])
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    try:
        env = load_config(args.config)
        result = (inspect_project if args.command == "inspect" else backup_handoff)(env, args.project)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
