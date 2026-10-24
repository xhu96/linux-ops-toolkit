#!/usr/bin/env bats
# healthcheck reads its data from overridable sources, so each test feeds it a
# fake host and checks the verdict and the exit code.

setup() {
  HC="$BATS_TEST_DIRNAME/../../bin/healthcheck"
  FIX="$BATS_TEST_TMPDIR"
  printf 'MemTotal:       8000000 kB\nMemAvailable:   4000000 kB\n' >"$FIX/meminfo"
  echo "0.50 0.40 0.30 1/200 1234" >"$FIX/loadavg"
  export MEMINFO="$FIX/meminfo" LOADAVG="$FIX/loadavg" NPROC=2
  export DF_CMD="cat $FIX/df" DF_INODE_CMD="cat $FIX/dfi"
  # Stub systemctl so the real host's failed units don't leak into the tests.
  mkdir -p "$FIX/bin"
  printf '#!/bin/sh\nexit 0\n' >"$FIX/bin/systemctl"
  chmod +x "$FIX/bin/systemctl"
  export PATH="$FIX/bin:$PATH"
  df_with 40 10
}

df_with() {
  printf 'Filesystem 1024-blocks Used Available Capacity Mounted\n/dev/sda1 100 0 0 %s%% /\n' "$1" >"$FIX/df"
  printf 'Filesystem Inodes IUsed IFree IUse%% Mounted\n/dev/sda1 100 0 0 %s%% /\n' "$2" >"$FIX/dfi"
}

@test "healthy host exits 0" {
  run "$HC"
  [ "$status" -eq 0 ]
  [[ "$output" == *"overall: OK"* ]]
  [[ "$output" == *"memory"*"50% used"* ]]
}

@test "disk above warning threshold exits 1" {
  df_with 85 10
  run "$HC"
  [ "$status" -eq 1 ]
  [[ "$output" == *"WARNING   disk:/"* ]]
}

@test "disk above critical threshold exits 2" {
  df_with 95 10
  run "$HC"
  [ "$status" -eq 2 ]
  [[ "$output" == *"overall: CRITICAL"* ]]
}

@test "thresholds are configurable" {
  df_with 85 10
  run "$HC" --disk-warn 90 --disk-crit 95
  [ "$status" -eq 0 ]
}

@test "inode exhaustion is caught even when space is fine" {
  df_with 20 97
  run "$HC"
  [ "$status" -eq 2 ]
  [[ "$output" == *"CRITICAL  inodes:/"* ]]
}

@test "load is judged per CPU" {
  echo "7.00 5.00 4.00 1/200 1234" >"$FIX/loadavg"
  run "$HC"
  [ "$status" -eq 2 ]
  [[ "$output" == *"3.50 per CPU"* ]]
}

@test "memory pressure is a warning" {
  printf 'MemTotal: 1000 kB\nMemAvailable: 100 kB\n' >"$FIX/meminfo"
  run "$HC"
  [ "$status" -eq 1 ]
}

@test "json output is valid and carries the overall status" {
  df_with 95 10
  run "$HC" --json
  [ "$status" -eq 2 ]
  [ "$(jq -r .status <<<"$output")" = CRITICAL ]
  [ "$(jq '.checks | length' <<<"$output")" -ge 4 ]
}

@test "unknown option is rejected" {
  run "$HC" --bogus
  [ "$status" -ne 0 ]
}
