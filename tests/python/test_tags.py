import json

from opskit import cli


def make_instances(ec2):
    image = ec2.describe_images(Owners=["amazon"])["Images"][0]["ImageId"]
    good = ec2.run_instances(ImageId=image, MinCount=1, MaxCount=1)["Instances"][0]["InstanceId"]
    bad = ec2.run_instances(ImageId=image, MinCount=1, MaxCount=1)["Instances"][0]["InstanceId"]
    ec2.create_tags(
        Resources=[good],
        Tags=[{"Key": k, "Value": "x"} for k in ("Project", "Owner", "Environment")],
    )
    ec2.create_tags(Resources=[bad], Tags=[{"Key": "Project", "Value": "x"}])
    return good, bad


def test_reports_only_non_compliant(aws, capsys, tmp_path, monkeypatch):
    good, bad = make_instances(aws("ec2"))
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    code = cli.main(["--format", "json", "tag-audit", "--resource-type", "ec2:instance"])
    rows = json.loads(capsys.readouterr().out)
    assert code == 1
    assert [r["missing"] for r in rows] == ["Owner,Environment"]
    assert rows[0]["arn"].endswith(bad)
    assert "1 non-compliant" in summary.read_text()


def test_compliant_exits_zero(aws, capsys):
    make_instances(aws("ec2"))
    assert cli.main(["tag-audit", "--required", "Project", "--resource-type", "ec2:instance"]) == 0
