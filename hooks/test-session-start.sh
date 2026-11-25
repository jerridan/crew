#!/usr/bin/env bash
# Seeded test of hooks/session-start.py and of its entry in hooks/hooks.json.
#
# It uses a temporary record root. It never touches ~/.claude/crew and never
# starts `claude`. It stops at the first failed check and exits non-zero.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/.." && pwd)
ORCH_PY="$REPO/skills/orchestrator/scripts/crew-orch.py"
HOOK="$HERE/session-start.py"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export CREW_RECORD_ROOT="$TMP/root"
mkdir -p "$CREW_RECORD_ROOT"
unset CREW_ORCH CLAUDE_CODE_SESSION_ID

STEP=""
fail() {
  echo "FAIL [$STEP]: $*" >&2
  exit 1
}
pass() { echo "ok   $STEP"; }

# hook <json>: run the hook script with the JSON on stdin.
hook() { printf '%s' "$1" | python3 "$HOOK"; }

# Two open records and a closed one. Each `init` stores the id of the session
# that ran it.
CLAUDE_CODE_SESSION_ID=sess-one python3 "$ORCH_PY" --orch one init >/dev/null || fail "init one"
CLAUDE_CODE_SESSION_ID=sess-two python3 "$ORCH_PY" --orch two init >/dev/null || fail "init two"
CLAUDE_CODE_SESSION_ID=sess-old python3 "$ORCH_PY" --orch old init >/dev/null || fail "init old"
python3 "$ORCH_PY" --orch old close >/dev/null || fail "close old"
python3 "$ORCH_PY" --orch one item add alpha --title Alpha --repo owner/x >/dev/null || fail "item add"
python3 "$ORCH_PY" --orch two item add beta --title Beta --repo owner/x >/dev/null || fail "item add"

STEP="a compact source and a matching session id print the resume digest as context"
out=$(hook '{"session_id": "sess-one", "source": "compact"}') || fail "exit non-zero"
python3 - "$out" <<'PY' || fail "bad output: $out"
import json, sys
d = json.loads(sys.argv[1])
o = d["hookSpecificOutput"]
assert o["hookEventName"] == "SessionStart", o
assert "alpha launch:" in o["additionalContext"], o
PY
pass

STEP="a resume source and a matching session id print the digest"
out=$(hook '{"session_id": "sess-two", "source": "resume"}') || fail "exit non-zero"
[ -n "$out" ] || fail "nothing printed for a matching id"
pass

STEP="another session id prints nothing"
out=$(hook '{"session_id": "sess-other", "source": "compact"}') || fail "exit non-zero"
[ -z "$out" ] || fail "printed: $out"
pass

STEP="a startup source prints nothing"
out=$(hook '{"session_id": "sess-one", "source": "startup"}') || fail "exit non-zero"
[ -z "$out" ] || fail "printed: $out"
pass

STEP="a closed record prints nothing"
out=$(hook '{"session_id": "sess-old", "source": "compact"}') || fail "exit non-zero"
[ -z "$out" ] || fail "printed: $out"
pass

STEP="bad stdin and a missing record root exit 0 and print nothing"
out=$(printf 'not json' | python3 "$HOOK") || fail "exit non-zero on bad stdin"
[ -z "$out" ] || fail "printed: $out"
out=$(printf '{"session_id": "sess-one", "source": "compact"}' | CREW_RECORD_ROOT="$TMP/none" python3 "$HOOK") || fail "exit non-zero"
[ -z "$out" ] || fail "printed: $out"
pass

STEP="the read-only digest writes nothing"
before=$(cat "$CREW_RECORD_ROOT/orchestrators/one/orchestrator.json")
hook '{"session_id": "sess-one", "source": "compact"}' >/dev/null
[ "$before" = "$(cat "$CREW_RECORD_ROOT/orchestrators/one/orchestrator.json")" ] || fail "the hook changed the record"
pass

STEP="hooks.json registers the tested script for the compact and resume sources"
cmd=$(python3 - "$REPO/hooks/hooks.json" <<'PY' || fail "no SessionStart entry"
import json, sys
h = json.load(open(sys.argv[1]))["hooks"]["SessionStart"]
assert len(h) == 1, h
assert set(h[0]["matcher"].split("|")) == {"compact", "resume"}, h[0]
assert h[0]["hooks"][0]["type"] == "command"
assert 0 < h[0]["hooks"][0]["timeout"] <= 60
print(h[0]["hooks"][0]["command"])
PY
)
case "$cmd" in *'hooks/session-start.py'*) ;; *) fail "the registered command does not name the script: $cmd" ;; esac
out=$(printf '{"session_id": "sess-one", "source": "compact"}' | CLAUDE_PLUGIN_ROOT="$REPO" bash -c "$cmd") || fail "the registered command failed"
case "$out" in *'alpha launch:'*) ;; *) fail "the registered command did not print the digest: $out" ;; esac
pass

echo "all checks passed"
