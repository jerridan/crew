#!/usr/bin/env bash
# Seeded test of hooks/session-end.py.
#
# It uses a temporary record root and a temporary HOME, so the hook reads no
# real record. It never starts `claude`. It stops at the first failed check
# and exits non-zero.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/.." && pwd)
RECORD_PY="$REPO/skills/project-lead/scripts/crew-record.py"
HOOK="$HERE/session-end.py"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export CREW_RECORD_ROOT="$TMP/root"
export HOME="$TMP/home"
mkdir -p "$CREW_RECORD_ROOT" "$HOME"
unset CLAUDE_CONFIG_DIR CLAUDE_CODE_SESSION_ID

STEP=""
fail() {
  echo "FAIL [$STEP]: $*" >&2
  exit 1
}
pass() { echo "ok   $STEP"; }

# seed <slug> <session-id> <run_state> [<run set field> <json>]...: one record
# with one worktree entry that the session holds.
seed() {
  local slug=$1 sid=$2 rstate=$3
  shift 3
  local d="$CREW_RECORD_ROOT/$slug"
  python3 "$RECORD_PY" "$d" init "the goal" "$slug" "$sid" >/dev/null || fail "init $slug"
  python3 "$RECORD_PY" "$d" run set run_state "\"$rstate\"" >/dev/null || fail "run_state $slug"
  while [ $# -ge 2 ]; do
    python3 "$RECORD_PY" "$d" run set "$1" "$2" >/dev/null || fail "run set $1 in $slug"
    shift 2
  done
  printf '{"p1": {"worktree": "/x/p1", "session_ids": ["%s"]}}\n' "$sid" > "$d/worktrees.json"
}

# end <session-id>: run the hook as the end of that session.
end() { printf '{"session_id": "%s", "reason": "prompt_input_exit"}' "$1" | python3 "$HOOK"; }

field() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run"]["run_state"])' "$CREW_RECORD_ROOT/$1/state.json"; }
orphaned() { python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["p1"].get("orphaned") is True)' "$CREW_RECORD_ROOT/$1/worktrees.json"; }

PARK='{"reason": "usage", "by": "usage", "at": "2026-11-25T10:00:00Z", "until": null, "next": "go on", "from_session": "sess-park", "prompt": "/x/prompt-1.md", "waiter": null}'

seed parked sess-park active park "$PARK"
seed live sess-live active park null
# wpark <from_session> <waiter id>: a park whose waiter started.
wpark() { printf '{"reason": "usage", "by": "usage", "at": "2026-11-25T10:00:00Z", "until": null, "next": "go on", "from_session": "%s", "prompt": "/x/prompt-1.md", "waiter": {"name": "pl", "session_id": "%s", "tab": "tmux:%%9", "terminal": "tmux", "tab_group": "g", "model": "opus", "started_at": "2026-11-25T10:00:01Z"}}' "$1" "$2"; }
seed waitdead sess-from1 active park "$(wpark sess-from1 sess-pw1)"
seed waitfrom sess-from2 active park "$(wpark sess-from2 sess-pw2)"
seed waitother sess-from3 active park "$(wpark sess-from3 sess-pw3)"
seed delivered sess-del delivered
seed woke sess-woke active park null parks \
  '[{"reason": "pause", "by": "ann", "at": "2026-11-25T09:00:00Z", "until": null, "next": "go on", "from_session": "sess-woke", "prompt": "/x/prompt-1.md", "waiter": {"name": "pl", "session_id": "sess-waiter", "tab": "tmux:%9", "terminal": "tmux", "tab_group": "g", "model": "opus", "started_at": "2026-11-25T09:00:01Z"}, "woke": {"at": "2026-11-25T09:30:00Z", "by": "resume word", "session_id": "sess-waiter"}}]'
python3 "$RECORD_PY" "$CREW_RECORD_ROOT/woke" session-id sess-waiter >/dev/null || fail "session-id woke"
seed failed sess-failed active park null parks \
  '[{"reason": "usage", "by": "usage", "at": "2026-11-25T09:00:00Z", "until": null, "next": "go on", "from_session": "sess-failed", "prompt": "/x/prompt-1.md", "waiter": null, "failed": {"step": "window", "at": "2026-11-25T09:00:02Z", "error": "no tab"}}]'

STEP="a parked run stays active when the session that parked ends"
end sess-park || fail "exit non-zero"
[ "$(field parked)" = active ] || fail "run_state is $(field parked)"
[ "$(orphaned parked)" = False ] || fail "the worktree was orphaned"
pass

STEP="the waiter ends while its park holds: the run goes interrupted"
end sess-pw1 || fail "exit non-zero"
[ "$(field waitdead)" = interrupted ] || fail "run_state is $(field waitdead)"
pass

STEP="the from_session of a park with a waiter ends: the run stays active"
end sess-from2 || fail "exit non-zero"
[ "$(field waitfrom)" = active ] || fail "run_state is $(field waitfrom)"
[ "$(orphaned waitfrom)" = False ] || fail "the worktree was orphaned"
pass

STEP="an unrelated session ends while a park holds: the run stays active"
end sess-unrelated || fail "exit non-zero"
[ "$(field waitother)" = active ] || fail "run_state is $(field waitother)"
[ "$(field waitfrom)" = active ] || fail "run_state is $(field waitfrom)"
pass

STEP="a live run with run.park null goes interrupted"
end sess-live || fail "exit non-zero"
[ "$(field live)" = interrupted ] || fail "run_state is $(field live)"
[ "$(orphaned live)" = True ] || fail "the worktree was not orphaned"
pass

STEP="a delivered run stays delivered"
end sess-del || fail "exit non-zero"
[ "$(field delivered)" = delivered ] || fail "run_state is $(field delivered)"
pass

STEP="the old session ends after the waiter's unpark: the run stays active"
end sess-woke || fail "exit non-zero"
[ "$(field woke)" = active ] || fail "run_state is $(field woke)"
[ "$(orphaned woke)" = False ] || fail "the worktree was orphaned"
pass

STEP="the waiter that took the run over still ends the run when it ends"
end sess-waiter || fail "exit non-zero"
[ "$(field woke)" = interrupted ] || fail "run_state is $(field woke)"
pass

STEP="a failed park leaves its session live: its end interrupts the run"
end sess-failed || fail "exit non-zero"
[ "$(field failed)" = interrupted ] || fail "run_state is $(field failed)"
pass

STEP="bad stdin exits 0"
printf 'not json' | python3 "$HOOK" || fail "exit non-zero"
pass

echo "all checks passed"
