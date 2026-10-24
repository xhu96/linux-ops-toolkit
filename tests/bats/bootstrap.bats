#!/usr/bin/env bats
# Argument validation and dry-run behaviour. The full run is covered by the
# container integration test (tests/integration/run.sh) in CI.

setup() {
  BS="$BATS_TEST_DIRNAME/../../bin/bootstrap-server"
  KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAITestKey test@ci"
  printf 'ID=ubuntu\nVERSION_CODENAME=noble\n' >"$BATS_TEST_TMPDIR/os-release"
  export OS_RELEASE="$BATS_TEST_TMPDIR/os-release"
  export SSHD_DIR="$BATS_TEST_TMPDIR/sshd" NO_COLOR=1
}

@test "help" {
  run "$BS" --help
  [ "$status" -eq 0 ]
  [[ "$output" == *"--ssh-key"* ]]
}

@test "rejects an invalid user name" {
  run "$BS" --dry-run --user 'Bad User'
  [ "$status" -ne 0 ]
  [[ "$output" == *"invalid user name"* ]]
}

@test "rejects an invalid port" {
  run "$BS" --dry-run --ssh-port 70000
  [ "$status" -ne 0 ]
}

@test "rejects something that is not a public key" {
  run "$BS" --dry-run --ssh-key "-----BEGIN OPENSSH PRIVATE KEY-----"
  [ "$status" -ne 0 ]
  [[ "$output" == *"public key"* ]]
}

@test "refuses unsupported operating systems" {
  printf 'ID=fedora\n' >"$OS_RELEASE"
  run "$BS" --dry-run
  [ "$status" -ne 0 ]
  [[ "$output" == *"unsupported OS"* ]]
}

@test "dry run changes nothing on disk" {
  run "$BS" --dry-run --user tester --ssh-key "$KEY" --no-docker --swap 0
  [ "$status" -eq 0 ]
  [[ "$output" == *"[dry-run]"* ]]
  [[ "$output" == *"(dry run)"* ]]
  [ ! -e "$SSHD_DIR/10-hardening.conf" ]
}

@test "requires root without --dry-run" {
  [ "$(id -u)" -ne 0 ] || skip "running as root"
  run "$BS"
  [ "$status" -ne 0 ]
  [[ "$output" == *"must run as root"* ]]
}
