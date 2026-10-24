"""Find resources that are missing required tags (cost allocation, ownership)."""

from __future__ import annotations


def audit(tagging, required: list[str], resource_types: list[str] | None = None) -> list[dict]:
    kwargs = {"ResourceTypeFilters": resource_types} if resource_types else {}
    findings = []
    for page in tagging.get_paginator("get_resources").paginate(**kwargs):
        for res in page["ResourceTagMappingList"]:
            present = {t["Key"] for t in res.get("Tags", [])}
            missing = [k for k in required if k not in present]
            if missing:
                findings.append({"arn": res["ResourceARN"], "missing": ",".join(missing)})
    return sorted(findings, key=lambda f: f["arn"])
