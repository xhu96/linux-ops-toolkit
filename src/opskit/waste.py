"""Find resources that cost money but do nothing: unattached EBS volumes,
unassociated Elastic IPs and old snapshots.

Prices are rough eu-west-2 list prices (USD/month) to rank findings, not a bill.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

EBS_GB_MONTH = {"gp3": 0.088, "gp2": 0.116, "io1": 0.138, "io2": 0.138, "st1": 0.053, "sc1": 0.028}
SNAPSHOT_GB_MONTH = 0.053
EIP_MONTH = 3.65


def find(ec2, snapshot_days: int = 90, now: datetime | None = None) -> list[dict]:
    now = now or datetime.now(UTC)
    findings = []

    pages = ec2.get_paginator("describe_volumes").paginate(
        Filters=[{"Name": "status", "Values": ["available"]}]
    )
    for page in pages:
        for v in page["Volumes"]:
            price = EBS_GB_MONTH.get(v["VolumeType"], 0.1) * v["Size"]
            findings.append(
                {
                    "kind": "unattached-volume",
                    "id": v["VolumeId"],
                    "detail": f"{v['Size']} GiB {v['VolumeType']}",
                    "usd_month": round(price, 2),
                }
            )

    for addr in ec2.describe_addresses()["Addresses"]:
        if "AssociationId" not in addr:
            findings.append(
                {
                    "kind": "idle-elastic-ip",
                    "id": addr.get("AllocationId", addr["PublicIp"]),
                    "detail": addr["PublicIp"],
                    "usd_month": EIP_MONTH,
                }
            )

    cutoff = now - timedelta(days=snapshot_days)
    for page in ec2.get_paginator("describe_snapshots").paginate(OwnerIds=["self"]):
        for s in page["Snapshots"]:
            if s["StartTime"] < cutoff:
                age = (now - s["StartTime"]).days
                findings.append(
                    {
                        "kind": "old-snapshot",
                        "id": s["SnapshotId"],
                        "detail": f"{s['VolumeSize']} GiB, {age} days old",
                        "usd_month": round(SNAPSHOT_GB_MONTH * s["VolumeSize"], 2),
                    }
                )

    return sorted(findings, key=lambda f: f["usd_month"], reverse=True)
