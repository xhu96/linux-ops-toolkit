#!/usr/bin/env bash
# Shared helpers for the scripts in bin/. Source it, don't execute it.
# shellcheck disable=SC2034  # variables here are used by the sourcing scripts

set -Eeuo pipefail

DRY_RUN="${DRY_RUN:-0}"
LOG_FILE="${LOG_FILE:-}"
if [[ -t 2 && -z "${NO_COLOR:-}" ]]; then
  C_RESET=$'\e[0m' C_BLUE=$'\e[34m' C_YELLOW=$'\e[33m' C_RED=$'\e[31m' C_GREEN=$'\e[32m'
else
  C_RESET='' C_BLUE='' C_YELLOW='' C_RED='' C_GREEN=''
fi

_log() {
  local level="$1" color="$2"; shift 2
  local line
  line="$(date -u +%Y-%m-%dT%H:%M:%SZ) ${level} $*"
  printf '%s%s%s\n' "$color" "$line" "$C_RESET" >&2
  if [[ -n "$LOG_FILE" ]]; then printf '%s\n' "$line" >>"$LOG_FILE" 2>/dev/null || true; fi
}
info() { _log INFO "$C_BLUE" "$@"; }
ok()   { _log OK "$C_GREEN" "$@"; }
warn() { _log WARN "$C_YELLOW" "$@"; }
err()  { _log ERROR "$C_RED" "$@"; }
die()  { err "$@"; exit 1; }

# run CMD...: execute, or only print it in dry-run mode.
run() {
  if [[ "$DRY_RUN" == 1 ]]; then
    info "[dry-run] $*"
  else
    "$@"
  fi
}

# write_file PATH MODE: write stdin to PATH only if the content changed.
# Returns 0 if the file changed, 1 if it was already up to date.
write_file() {
  local path="$1" mode="$2" tmp
  tmp="$(mktemp)"
  cat >"$tmp"
  if [[ -f "$path" ]] && cmp -s "$tmp" "$path"; then
    rm -f "$tmp"
    return 1
  fi
  if [[ "$DRY_RUN" == 1 ]]; then
    info "[dry-run] would write $path"
    rm -f "$tmp"
    return 0
  fi
  install -D -m "$mode" "$tmp" "$path"
  rm -f "$tmp"
  info "wrote $path"
}

require_root() {
  [[ "$DRY_RUN" == 1 || "$(id -u)" -eq 0 ]] || die "must run as root (or use --dry-run)"
}

in_container() {
  [[ -f /.dockerenv || -f /run/.containerenv ]] && return 0
  grep -qaE '(docker|containerd|kubepods|lxc)' /proc/1/cgroup 2>/dev/null
}

has_systemd() {
  [[ -d /run/systemd/system ]]
}

# os_id: prints the ID from /etc/os-release (ubuntu, debian, ...)
os_id() {
  # shellcheck disable=SC1090,SC1091
  (. "${OS_RELEASE:-/etc/os-release}" && printf '%s\n' "$ID")
}
