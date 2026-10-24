"""Spend per AWS service over the last N days, from Cost Explorer."""

from __future__ import annotations

from datetime import date, timedelta


def by_service(ce, days: int = 30, today: date | None = None, top: int = 10) -> list[dict]:
    today = today or date.today()
    start = today - timedelta(days=days)
    totals: dict[str, float] = {}
    token = None
    while True:
        kwargs = {
            "TimePeriod": {"Start": start.isoformat(), "End": today.isoformat()},
            "Granularity": "MONTHLY",
            "Metrics": ["UnblendedCost"],
            "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
        }
        if token:
            kwargs["NextPageToken"] = token
        resp = ce.get_cost_and_usage(**kwargs)
        for period in resp["ResultsByTime"]:
            for group in period["Groups"]:
                service = group["Keys"][0]
                amount = float(group["Metrics"]["UnblendedCost"]["Amount"])
                totals[service] = totals.get(service, 0.0) + amount
        token = resp.get("NextPageToken")
        if not token:
            break

    grand = sum(totals.values()) or 1.0
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    rows = [
        {"service": s, "usd": round(v, 2), "share": f"{v / grand:.0%}"} for s, v in ranked[:top]
    ]
    rest = sum(v for _, v in ranked[top:])
    if rest:
        rows.append({"service": "(other)", "usd": round(rest, 2), "share": f"{rest / grand:.0%}"})
    return rows
