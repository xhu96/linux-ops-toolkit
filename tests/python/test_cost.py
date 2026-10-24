from datetime import date

import boto3
from botocore.stub import ANY, Stubber

from opskit import cli, cost
from opskit.output import render


def group(service, amount):
    return {"Keys": [service], "Metrics": {"UnblendedCost": {"Amount": str(amount), "Unit": "USD"}}}


def stubbed(pages):
    ce = boto3.client("ce", region_name="us-east-1")
    stub = Stubber(ce)
    for page in pages:
        stub.add_response(
            "get_cost_and_usage",
            page,
            {
                "TimePeriod": ANY,
                "Granularity": "MONTHLY",
                "Metrics": ["UnblendedCost"],
                "GroupBy": ANY,
                **({"NextPageToken": ANY} if page is not pages[0] else {}),
            },
        )
    stub.activate()
    return ce


def test_aggregates_ranks_and_pages():
    pages = [
        {"ResultsByTime": [{"Groups": [group("EC2", 30), group("S3", 5)]}], "NextPageToken": "t"},
        {"ResultsByTime": [{"Groups": [group("EC2", 10), group("RDS", 15), group("SNS", 1)]}]},
    ]
    rows = cost.by_service(stubbed(pages), days=30, today=date(2026, 10, 24), top=2)
    assert [r["service"] for r in rows] == ["EC2", "RDS", "(other)"]
    assert rows[0] == {"service": "EC2", "usd": 40.0, "share": "66%"}
    assert rows[2]["usd"] == 6.0


def test_cli(monkeypatch, capsys):
    pages = [{"ResultsByTime": [{"Groups": [group("EC2", 12.5)]}]}]
    ce = stubbed(pages)
    monkeypatch.setattr(cli, "_client", lambda name: ce)
    assert cli.main(["--format", "markdown", "cost", "--days", "7"]) == 0
    assert "| EC2 | 12.5 | 100% |" in capsys.readouterr().out


def test_render_formats():
    rows = [{"a": 1, "b": "x"}]
    assert render(rows, ["a", "b"]).splitlines()[0].startswith("A")
    assert render([], ["a"]) == "(none)"
    assert render(rows, ["a", "b"], "json").startswith("[")
