#!/usr/bin/env bash
# Integration test: run bootstrap-server in a throwaway container of the given
# image, twice, and check the result. The second run must change nothing.
#   tests/integration/run.sh ubuntu:24.04 [extra docker run args...]
set -euo pipefail
image="$1"; shift
repo="$(cd "$(dirname "$0")/../.." && pwd)"

docker run --rm -v "${repo}:/toolkit:ro" "$@" "$image" bash -euo pipefail -c '
  key="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKeyForIntegrationOnly test@ci"
  /toolkit/bin/bootstrap-server --user deploy --ssh-key "$key" --no-docker --timezone Europe/London

  echo "--- second run (must be a no-op)"
  out=$(/toolkit/bin/bootstrap-server --user deploy --ssh-key "$key" --no-docker --timezone Europe/London 2>&1)
  echo "$out"
  grep -q "nothing to do" <<<"$out"

  echo "--- assertions"
  id deploy | grep -q "(sudo)"
  test "$(stat -c %a /home/deploy/.ssh)" = 700
  test "$(stat -c %a /home/deploy/.ssh/authorized_keys)" = 600
  test "$(grep -c "ssh-ed25519" /home/deploy/.ssh/authorized_keys)" = 1
  grep -qx "PermitRootLogin no" /etc/ssh/sshd_config.d/10-hardening.conf
  grep -qx "PasswordAuthentication no" /etc/ssh/sshd_config.d/10-hardening.conf
  sshd -t
  sudo -u deploy sudo -n true
  test "$(readlink /etc/localtime)" = /usr/share/zoneinfo/Europe/London
  test -f /etc/fail2ban/jail.d/sshd.local
  test -f /etc/apt/apt.conf.d/20auto-upgrades
  echo "all assertions passed on '"$image"'"
'
