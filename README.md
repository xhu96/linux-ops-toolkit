# Linux ops toolkit

[![CI](https://github.com/xhu96/linux-ops-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/xhu96/linux-ops-toolkit/actions/workflows/ci.yml)

Small, tested tools for the routine parts of running Linux servers and an AWS account: set a server up the same way every time, check that it is healthy, back it up, and find what is costing money for no reason.

| Tool | What it does |
|---|---|
| [`bootstrap-server`](bin/bootstrap-server) | Turns a fresh Ubuntu/Debian host into a hardened server: admin user with key-only SSH, firewall, fail2ban, automatic security updates, kernel hardening, Docker. Idempotent, with a dry-run mode and lockout protection. [What it changes and why](docs/hardening.md) |
| [`healthcheck`](bin/healthcheck) | Disk, inodes, memory, load per CPU, failed systemd units, services, TLS certificate expiry. Nagios-style exit codes (0/1/2) and `--json`, so it plugs into cron, a monitoring agent or CI |
| [`backup`](bin/backup) | Compressed, checksummed, rotated backups with optional S3 upload. Lock against overlapping runs, atomic writes, `--verify` |
| [`opskit`](src/opskit) | Python CLI for AWS housekeeping: ECR image cleanup, tag compliance audit, idle resources (unattached volumes, unused Elastic IPs, old snapshots) with an estimated monthly cost, and spend per service |

## How it is tested

- **ShellCheck** on every script.
- **24 bats tests** for the shell tools. `healthcheck` reads its data from overridable sources, so tests feed it a fake host (disk at 95%, inodes exhausted, high load) and check the verdict and exit code.
- **Container integration tests**: `bootstrap-server` runs for real in Ubuntu 22.04, Ubuntu 24.04 and Debian 12 containers, twice. The second run must report "nothing to do", then the result is checked (user, key permissions, `sshd -t`, sudo, timezone…).
- **VM integration test**: containers cannot exercise ufw, sysctl or systemd, so CI also runs the full script on the GitHub-hosted Ubuntu VM, including Docker, and checks the firewall, kernel settings and services.
- **11 pytest tests, ~99% coverage** for `opskit`, against AWS mocked with moto (and botocore's Stubber for Cost Explorer). No AWS account needed.

## Quick start

```bash
git clone https://github.com/xhu96/linux-ops-toolkit && cd linux-ops-toolkit
sudo make install                 # links the scripts into /usr/local/bin
pip install .                     # installs opskit
```

### bootstrap-server

```bash
# see what would change
sudo bootstrap-server --dry-run --user deploy --ssh-key-file ~/.ssh/id_ed25519.pub

# apply
sudo bootstrap-server --user deploy --ssh-key-file ~/.ssh/id_ed25519.pub --timezone Europe/London
```

On a cloud VM it can also run as user data at first boot. Keep your current SSH session open until you have logged in as the new user in a second terminal.

### healthcheck

```bash
$ healthcheck --service fail2ban --tls example.com
OK        disk:/                       41% used
OK        inodes:/                     6% used
OK        memory                       38% used (2410 MiB available)
OK        load                         0.31 on 2 CPU(s) (0.15 per CPU)
OK        systemd                      no failed units
OK        service:fail2ban             active
WARNING   tls:example.com              expires in 19 days

overall: WARNING
$ echo $?
1
```

Run it every 5 minutes with the systemd timer in [`examples/systemd`](examples/systemd).

### backup

```bash
backup --dest /var/backups/app --keep 14 --exclude '*.log' --s3 s3://my-backups/web-1 /etc /srv/app
backup --verify /var/backups/app/backup-20261024T023000Z.tar.gz
```

### opskit

```bash
opskit waste                                          # idle resources, sorted by monthly cost
opskit tag-audit --required Project,Owner,Environment # exits 1 if anything is untagged
opskit ecr-cleanup --repository my-app --keep 20      # dry run; add --apply to delete
opskit cost --days 30 --format markdown
```

The [AWS hygiene workflow](.github/workflows/aws-hygiene.yml) runs `waste`, `tag-audit` and `cost` every Monday through GitHub OIDC and writes the results to the job summary. It is read-only and stays skipped until `AWS_HYGIENE_ROLE_ARN` is set.

IAM permissions needed: `ecr:DescribeImages`, `ecr:BatchDeleteImage` (cleanup only), `tag:GetResources`, `ec2:DescribeVolumes`, `ec2:DescribeAddresses`, `ec2:DescribeSnapshots`, `ce:GetCostAndUsage`.

## Layout

```
bin/            bootstrap-server, healthcheck, backup
lib/common.sh   logging, dry-run, idempotent file writes, OS/container detection
src/opskit/     AWS housekeeping CLI
tests/          bats, pytest, container integration
examples/       systemd units and timers
docs/           hardening rationale
```

## Related

[mlops-aws-pipeline](https://github.com/xhu96/mlops-aws-pipeline): end-to-end MLOps pipeline on AWS with Terraform, GitHub Actions and ECS.
