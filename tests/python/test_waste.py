import json
from datetime import UTC, datetime, timedelta

from opskit import cli, waste


def test_finds_idle_volume_and_ip(aws, capsys):
    ec2 = aws("ec2")
    ec2.create_volume(AvailabilityZone="eu-west-2a", Size=100, VolumeType="gp3")
    ec2.allocate_address(Domain="vpc")

    code = cli.main(["--format", "json", "waste"])
    rows = json.loads(capsys.readouterr().out)
    assert code == 1
    kinds = {r["kind"] for r in rows}
    assert {"unattached-volume", "idle-elastic-ip"} <= kinds
    vol = next(r for r in rows if r["kind"] == "unattached-volume")
    assert vol["usd_month"] == 8.8
    assert rows == sorted(rows, key=lambda r: r["usd_month"], reverse=True)


def test_old_snapshots_only(aws):
    ec2 = aws("ec2")
    vol = ec2.create_volume(AvailabilityZone="eu-west-2a", Size=10)["VolumeId"]
    ec2.create_snapshot(VolumeId=vol)
    later = datetime.now(UTC) + timedelta(days=200)
    rows = waste.find(ec2, snapshot_days=90, now=later)
    assert any(r["kind"] == "old-snapshot" for r in rows)
    rows = waste.find(ec2, snapshot_days=90)
    assert not any(r["kind"] == "old-snapshot" for r in rows)


def test_clean_account_exits_zero(aws, capsys):
    assert cli.main(["waste"]) == 0
    assert "(none)" in capsys.readouterr().out
