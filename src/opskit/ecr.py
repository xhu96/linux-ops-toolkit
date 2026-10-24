"""Delete old container images from ECR, keeping the newest N per repository."""

from __future__ import annotations


def plan_cleanup(ecr, repository: str, keep: int) -> list[dict]:
    """Return the images that would be deleted: all untagged ones, plus tagged
    ones beyond the `keep` most recently pushed."""
    images = []
    for page in ecr.get_paginator("describe_images").paginate(repositoryName=repository):
        images.extend(page["imageDetails"])

    untagged = [i for i in images if not i.get("imageTags")]
    tagged = sorted(
        (i for i in images if i.get("imageTags")), key=lambda i: i["imagePushedAt"], reverse=True
    )
    doomed = untagged + tagged[keep:]
    return [
        {
            "repository": repository,
            "digest": i["imageDigest"],
            "tags": ",".join(i.get("imageTags", [])) or "<untagged>",
            "pushed": i["imagePushedAt"].strftime("%Y-%m-%d"),
            "size_mb": round(i.get("imageSizeInBytes", 0) / 1_048_576, 1),
        }
        for i in doomed
    ]


def delete(ecr, repository: str, digests: list[str]) -> int:
    deleted = 0
    for start in range(0, len(digests), 100):  # API limit per call
        batch = [{"imageDigest": d} for d in digests[start : start + 100]]
        resp = ecr.batch_delete_image(repositoryName=repository, imageIds=batch)
        deleted += len(resp.get("imageIds", []))
    return deleted
