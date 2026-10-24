"""opskit: AWS housekeeping from the command line or a scheduled CI job.

    opskit ecr-cleanup --repository my-app --keep 20          # dry run
    opskit ecr-cleanup --repository my-app --keep 20 --apply  # delete
    opskit tag-audit --required Project,Owner,Environment
    opskit waste --snapshot-days 90
    opskit cost --days 30

Read-only commands exit 1 when they find something, so CI can fail on them.
Destructive commands only act with --apply.
"""

from __future__ import annotations

import argparse
import os
import sys

from opskit import cost, ecr, tags, waste
from opskit.output import render


def _client(name: str):
    import boto3

    return boto3.client(name)


def _summary(text: str) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(text + "\n\n")


def cmd_ecr_cleanup(args) -> int:
    client = _client("ecr")
    rows = ecr.plan_cleanup(client, args.repository, args.keep)
    print(render(rows, ["digest", "tags", "pushed", "size_mb"], args.format))
    freed = sum(r["size_mb"] for r in rows)
    if not args.apply:
        print(f"\n{len(rows)} image(s), {freed:.1f} MB would be deleted. Re-run with --apply.")
        return 0
    deleted = ecr.delete(client, args.repository, [r["digest"] for r in rows])
    print(f"\ndeleted {deleted} image(s), freed {freed:.1f} MB")
    return 0


def cmd_tag_audit(args) -> int:
    required = [t.strip() for t in args.required.split(",") if t.strip()]
    rows = tags.audit(_client("resourcegroupstaggingapi"), required, args.resource_type or None)
    print(render(rows, ["arn", "missing"], args.format))
    _summary(
        f"### Tag audit: {len(rows)} non-compliant\n\n"
        + render(rows, ["arn", "missing"], "markdown")
    )
    return 1 if rows else 0


def cmd_waste(args) -> int:
    rows = waste.find(_client("ec2"), snapshot_days=args.snapshot_days)
    cols = ["kind", "id", "detail", "usd_month"]
    print(render(rows, cols, args.format))
    total = sum(r["usd_month"] for r in rows)
    if args.format != "json":
        print(f"\nestimated waste: ${total:.2f}/month")
    _summary(f"### Idle resources: ~${total:.2f}/month\n\n" + render(rows, cols, "markdown"))
    return 1 if rows else 0


def cmd_cost(args) -> int:
    rows = cost.by_service(_client("ce"), days=args.days, top=args.top)
    print(render(rows, ["service", "usd", "share"], args.format))
    _summary(
        f"### Spend, last {args.days} days\n\n"
        + render(rows, ["service", "usd", "share"], "markdown")
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opskit", description=__doc__.split("\n")[0])
    parser.add_argument("--format", choices=["table", "json", "markdown"], default="table")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ecr-cleanup", help="delete old ECR images")
    p.add_argument("--repository", required=True)
    p.add_argument("--keep", type=int, default=20, help="tagged images to keep (newest first)")
    p.add_argument("--apply", action="store_true", help="actually delete")
    p.set_defaults(func=cmd_ecr_cleanup)

    p = sub.add_parser("tag-audit", help="resources missing required tags")
    p.add_argument("--required", default="Project,Owner,Environment")
    p.add_argument("--resource-type", action="append", help="e.g. ec2:instance (repeatable)")
    p.set_defaults(func=cmd_tag_audit)

    p = sub.add_parser("waste", help="idle resources that still cost money")
    p.add_argument("--snapshot-days", type=int, default=90)
    p.set_defaults(func=cmd_waste)

    p = sub.add_parser("cost", help="spend per service")
    p.add_argument("--days", type=int, default=30)
    p.add_argument("--top", type=int, default=10)
    p.set_defaults(func=cmd_cost)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if getattr(args, "keep", 1) < 1:
        print("--keep must be at least 1", file=sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
