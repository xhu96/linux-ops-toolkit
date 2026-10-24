#!/usr/bin/env bats

setup() {
  BK="$BATS_TEST_DIRNAME/../../bin/backup"
  SRC="$BATS_TEST_TMPDIR/src"
  DEST="$BATS_TEST_TMPDIR/dest"
  mkdir -p "$SRC/sub"
  echo hello >"$SRC/a.txt"
  echo noise >"$SRC/sub/debug.log"
  export NO_COLOR=1
}

archives() { find "$DEST" -name 'backup-*.tar.gz' 2>/dev/null | sort; }

@test "creates a checksummed archive" {
  run "$BK" --dest "$DEST" "$SRC"
  [ "$status" -eq 0 ]
  a=$(archives)
  [ -f "$a" ] && [ -f "$a.sha256" ]
  tar -tzf "$a" | grep -q "a.txt"
}

@test "verify passes on a good archive and fails on a tampered one" {
  "$BK" --dest "$DEST" "$SRC"
  a=$(archives)
  run "$BK" --verify "$a"
  [ "$status" -eq 0 ]
  echo garbage >>"$a"
  run "$BK" --verify "$a"
  [ "$status" -ne 0 ]
  [[ "$output" == *"checksum mismatch"* ]]
}

@test "excludes patterns" {
  "$BK" --dest "$DEST" --exclude '*.log' "$SRC"
  run tar -tzf "$(archives)"
  [[ "$output" == *"a.txt"* ]]
  [[ "$output" != *"debug.log"* ]]
}

@test "keeps only the N most recent archives" {
  mkdir -p "$DEST"
  for d in 20260101 20260102 20260103; do
    touch "$DEST/backup-${d}T000000Z.tar.gz" "$DEST/backup-${d}T000000Z.tar.gz.sha256"
  done
  run "$BK" --dest "$DEST" --keep 2 "$SRC"
  [ "$status" -eq 0 ]
  [ "$(archives | wc -l)" -eq 2 ]
  [ ! -e "$DEST/backup-20260102T000000Z.tar.gz" ]
  [ ! -e "$DEST/backup-20260101T000000Z.tar.gz.sha256" ]
  [ -e "$DEST/backup-20260103T000000Z.tar.gz" ]
}

@test "dry run writes nothing" {
  run "$BK" --dest "$DEST" --dry-run "$SRC"
  [ "$status" -eq 0 ]
  [ -z "$(archives)" ]
}

@test "refuses to run twice at the same time" {
  mkdir -p "$DEST"
  exec 8>"$DEST/.backup.lock"
  flock -n 8
  run "$BK" --dest "$DEST" "$SRC"
  [ "$status" -ne 0 ]
  [[ "$output" == *"is running"* ]]
}

@test "missing source fails before doing anything" {
  run "$BK" --dest "$DEST" /does/not/exist
  [ "$status" -ne 0 ]
  [ ! -d "$DEST" ]
}

@test "validates arguments" {
  run "$BK" --dest "$DEST" --keep 0 "$SRC"
  [ "$status" -ne 0 ]
  run "$BK" --dest "$DEST" --s3 http://nope "$SRC"
  [ "$status" -ne 0 ]
}
