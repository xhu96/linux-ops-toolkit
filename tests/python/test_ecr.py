import json
from datetime import UTC, datetime, timedelta

from opskit import cli, ecr


def push(client, repo, tag, n):
    manifest = json.dumps(
        {
            "schemaVersion": 2,
            "mediaType": "application/vnd.docker.distribution.manifest.v2+json",
            "config": {"digest": f"sha256:{n:064x}"},
            "layers": [{"digest": f"sha256:{n + 100:064x}", "size": n}],
        }
    )
    kwargs = {"repositoryName": repo, "imageManifest": manifest}
    if tag:
        kwargs["imageTag"] = tag
    client.put_image(**kwargs)


def test_plan_keeps_newest_and_drops_untagged():
    t0 = datetime(2026, 1, 1, tzinfo=UTC)
    images = [
        {"imageDigest": f"d{i}", "imageTags": [f"v{i}"], "imagePushedAt": t0 + timedelta(days=i)}
        for i in range(5)
    ] + [{"imageDigest": "dx", "imagePushedAt": t0}]

    class Fake:
        def get_paginator(self, _):
            class P:
                def paginate(self, **_):
                    return [{"imageDetails": images}]

            return P()

    rows = ecr.plan_cleanup(Fake(), "app", keep=2)
    assert {r["digest"] for r in rows} == {"dx", "d0", "d1", "d2"}
    assert rows[0]["tags"] == "<untagged>"


def test_cli_dry_run_then_apply(aws, capsys):
    client = aws("ecr")
    client.create_repository(repositoryName="app")
    for i in range(4):
        push(client, "app", f"v{i}", i)

    assert cli.main(["ecr-cleanup", "--repository", "app", "--keep", "2"]) == 0
    assert "would be deleted" in capsys.readouterr().out
    assert len(client.describe_images(repositoryName="app")["imageDetails"]) == 4

    assert cli.main(["ecr-cleanup", "--repository", "app", "--keep", "2", "--apply"]) == 0
    assert "deleted 2 image(s)" in capsys.readouterr().out
    assert len(client.describe_images(repositoryName="app")["imageDetails"]) == 2


def test_keep_must_be_positive(aws):
    assert cli.main(["ecr-cleanup", "--repository", "app", "--keep", "0"]) == 2
