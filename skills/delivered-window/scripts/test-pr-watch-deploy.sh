#!/bin/bash
# Seeded test of the default deploy signal of pr-watch.sh (AC1 of issue 144).
#
# usage: bash skills/delivered-window/scripts/test-pr-watch-deploy.sh
#
# It builds a record under a temp directory, puts a stub `gh` first in PATH,
# and runs `pr-watch.sh <record> deploy-once` once per case. The stub reads
# raw JSON from files under $STUB_DIR and applies the `--jq` filter of the
# call with `jq`, as `gh` does. It exits 0 only when every check passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
PW="$here/pr-watch.sh"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fails=0
total=0
OID=abc123def456

mkdir -p "$T/bin" "$T/rec"
cat > "$T/bin/gh" <<'STUB'
#!/bin/bash
D=$STUB_DIR
args="$*"
expr=''
prev=''
for a in "$@"; do
  case "$prev" in --jq|-q) expr=$a ;; esac
  prev=$a
done
emit() {
  [ -f "$1" ] || exit 1
  if [ -n "$expr" ]; then jq -r "$expr" "$1" || exit 1; else cat "$1"; fi
  exit 0
}
case "$args" in
  "pr view"*) emit "$D/pr.json" ;;
  *"/pulls/"*"/files"*)
    if [ -e "$D/fail-files-once" ]; then rm -f "$D/fail-files-once"; exit 1; fi
    emit "$D/files.json" ;;
  *"/deployments/"*"/statuses"*) emit "$D/statuses.json" ;;
  *"/deployments?sha="*) emit "$D/deployments.json" ;;
  *"/deployments?per_page"*) emit "$D/deployments.json" ;;
  *"/actions/workflows"*)
    [ -e "$D/fail-workflows" ] && exit 1
    if [ -e "$D/fail-workflows-once" ]; then rm -f "$D/fail-workflows-once"; exit 1; fi
    emit "$D/workflows.json" ;;
  *"/actions/runs"*) emit "$D/runs.json" ;;
esac
exit 1
STUB
chmod +x "$T/bin/gh"

cat > "$T/rec/state.json" <<'EOF'
{"deliverables":[{"pr_url":"https://github.com/o/r/pull/7"}],
 "run":{"deploy":{"environment":null,"workflow":null,"timeout_minutes":180,
 "source":"default","since":null,"ended":null}}}
EOF

# A stub `sleep` for the deploy mode: it counts calls and ends the watch on the sixth.
cat > "$T/bin/sleep" <<'STUB'
#!/bin/bash
n=$(cat "$STUB_DIR/sleeps" 2>/dev/null || echo 0)
echo $((n + 1)) > "$STUB_DIR/sleeps"
[ "$n" -lt 5 ] || kill -TERM "$PPID"
exit 0
STUB
chmod +x "$T/bin/sleep"

export STUB_DIR="$T/stub"
export PATH="$T/bin:$PATH"

# setup <minutes since merge> <deployments json> <workflows json> <runs json>
# Set FILES to the PR files json, FAIL_WF=1 for a workflows read that always
# fails, FAIL_WF_ONCE=1 or FAIL_FILES_ONCE=1 for a read that fails once.
setup() {
  rm -rf "$STUB_DIR"; mkdir -p "$STUB_DIR"
  merged=$(jq -nr --argjson m "$1" '(now - $m*60) | strftime("%Y-%m-%dT%H:%M:%SZ")')
  files=${FILES-'[{"filename":"README.md"}]'}
  printf '{"state":"MERGED","mergeCommit":{"oid":"%s"},"mergedAt":"%s"}\n' "$OID" "$merged" > "$STUB_DIR/pr.json"
  printf '%s\n' "$files" > "$STUB_DIR/files.json"
  printf '%s\n' "$2" > "$STUB_DIR/deployments.json"
  printf '%s\n' "$3" > "$STUB_DIR/workflows.json"
  printf '%s\n' "$4" > "$STUB_DIR/runs.json"
  printf '[{"state":"success","created_at":"2026-01-01T00:00:00Z"}]\n' > "$STUB_DIR/statuses.json"
  [ -z "${FAIL_WF:-}" ] || : > "$STUB_DIR/fail-workflows"
  [ -z "${FAIL_WF_ONCE:-}" ] || : > "$STUB_DIR/fail-workflows-once"
  [ -z "${FAIL_FILES_ONCE:-}" ] || : > "$STUB_DIR/fail-files-once"
}

# check <label> <want> : want is `none` (no output), `no-deploy-wf` (the no
# deploy workflow text) or `no-deploy-wait` (the 10-minute text), each exactly
# one line, or `deployed`.
check() {
  total=$((total + 1))
  out=$(bash "$PW" "$T/rec" deploy-once 2>&1)
  lines=$(printf '%s' "$out" | grep -c .)
  ok=''
  case "$2" in
    none) [ -z "$out" ] && ok=1 ;;
    no-deploy-wf) [ "$lines" = 1 ] && case "$out" in "no-deploy 7 - "*"and no deploy workflow") true ;; *) false ;; esac && ok=1 ;;
    no-deploy-wait) [ "$lines" = 1 ] && case "$out" in "no-deploy 7 - "*"or deploy runs") true ;; *) false ;; esac && ok=1 ;;
    deployed) case "$out" in "deployed "*) ok=1 ;; esac ;;
  esac
  if [ -n "$ok" ]; then echo "ok   $1"; else
    fails=$((fails + 1)); echo "FAIL $1 (want $2)"; printf '     got: %s\n' "$out"
  fi
}

WF_PR='{"workflows":[{"name":"PR review","path":".github/workflows/pr-review.yml","state":"active"}]}'
WF_DEPLOY='{"workflows":[{"name":"Deploy","path":".github/workflows/prod.yml","state":"active"}]}'
WF_RELEASE='{"workflows":[{"name":"CI","path":".github/workflows/release.yml","state":"active"}]}'
WF_OFF='{"workflows":[{"name":"Deploy","path":".github/workflows/deploy.yml","state":"disabled_manually"}]}'
NORUNS='{"workflow_runs":[]}'
NODEP='[]'
OTHERDEP='[{"id":4,"environment":"staging","production_environment":false,"sha":"zzz","created_at":"2026-01-01T00:00:00Z"}]'
PRODDEP='[{"id":5,"environment":"production","production_environment":true,"sha":"'$OID'","created_at":"2026-01-01T00:00:00Z"}]'
DEPRUN='{"workflow_runs":[{"id":9,"name":"CI","path":".github/workflows/deploy.yml","conclusion":"success","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}]}'

setup 1 "$NODEP" "$WF_PR" "$NORUNS";      check 'no deploy workflow, merged 1 minute ago' none
setup 3 "$NODEP" "$WF_PR" "$NORUNS";      check 'no deploy workflow, merged 3 minutes ago' no-deploy-wf
setup 3 "$NODEP" "$WF_DEPLOY" "$NORUNS";  check 'workflow Deploy, no run, 3 minutes' none
setup 11 "$NODEP" "$WF_DEPLOY" "$NORUNS"; check 'workflow Deploy, no run, 11 minutes' no-deploy-wait
setup 3 "$NODEP" "$WF_RELEASE" "$NORUNS"; check 'release.yml named CI, no run, 3 minutes' none
setup 11 "$NODEP" "$WF_RELEASE" "$NORUNS"; check 'release.yml named CI, no run, 11 minutes' no-deploy-wait
FAIL_WF=1 setup 3 "$NODEP" "$WF_PR" "$NORUNS"; check 'workflows read fails, 3 minutes' none
setup 3 "$OTHERDEP" "$WF_PR" "$NORUNS";   check 'a deployment exists, no deploy workflow, 3 minutes' none
setup 3 "$OTHERDEP" "$WF_DEPLOY" "$NORUNS"; check 'a deployment exists, a deploy workflow, 3 minutes' none
setup 1 "$PRODDEP" "$WF_PR" "$NORUNS";    check 'production deployment with success' deployed
setup 3 "$NODEP" "$WF_OFF" "$NORUNS";     check 'only a disabled Deploy workflow' no-deploy-wf
setup 3 "$NODEP" "$WF_RELEASE" "$DEPRUN"; check 'run of deploy.yml named CI with success, 3 minutes' none
RDRUN='{"workflow_runs":[{"id":9,"name":"CI","path":".github/workflows/release-drafter.yml","conclusion":"success","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}]}'
setup 3 "$NODEP" "$WF_RELEASE" "$RDRUN"; check 'release-drafter.yml run named CI with success, 3 minutes' none
NAMEDRUN='{"workflow_runs":[{"id":9,"name":"Deploy","path":".github/workflows/ci.yml","conclusion":"success","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}]}'
setup 1 "$NODEP" "$WF_PR" "$NAMEDRUN";    check 'a run named Deploy with success, 1 minute' deployed
# The merged PR added or renamed a workflow file: keep the wait.
ADD='[{"filename":"README.md","status":"modified"},{"filename":".github/workflows/x.yml","status":"added"}]'
FILES=$ADD setup 3 "$NODEP" "$WF_PR" "$NORUNS"
check 'PR added a workflow file, 3 minutes' none
FILES=$ADD setup 11 "$NODEP" "$WF_PR" "$NORUNS"
check 'PR added a workflow file, 11 minutes' no-deploy-wait
FILES='[{"filename":".github/workflows/y.yml","status":"renamed"}]' setup 3 "$NODEP" "$WF_PR" "$NORUNS"
check 'PR renamed a workflow file, 3 minutes' none
# An edit of an existing workflow file does not keep the wait.
FILES='[{"filename":".github/workflows/pr-review.yml","status":"modified"}]' setup 3 "$NODEP" "$WF_PR" "$NORUNS"
check 'PR edited pr-review.yml, 3 minutes' no-deploy-wf
FILES='[{"filename":"README.md","status":"modified"}]' setup 1 "$NODEP" "$WF_PR" "$NORUNS"
check 'PR changed no workflow file, 1 minute' none
FILES='[{"filename":"README.md","status":"modified"}]' setup 3 "$NODEP" "$WF_PR" "$NORUNS"
check 'PR changed no workflow file, 3 minutes' no-deploy-wf
FILES=null setup 3 "$NODEP" "$WF_PR" "$NORUNS"
check 'files read fails, 3 minutes' none

# One deploy process: the workflows read fails once, then succeeds.
total=$((total + 1))
FAIL_WF_ONCE=1 setup 3 "$NODEP" "$WF_PR" "$NORUNS"
out=$(bash "$PW" "$T/rec" deploy 2>&1)
sleeps=$(cat "$STUB_DIR/sleeps" 2>/dev/null || echo 0)
case "$out" in
  "no-deploy 7 - "*"and no deploy workflow")
    if [ "$(printf '%s\n' "$out" | grep -c .)" = 1 ] && [ "$sleeps" = 1 ]; then
      echo "ok   workflows read fails once, then no-deploy on the next poll"
    else
      fails=$((fails + 1)); echo "FAIL failed-then-good read (sleeps: $sleeps)"; printf '     got: %s\n' "$out"
    fi ;;
  *) fails=$((fails + 1)); echo "FAIL failed-then-good read (sleeps: $sleeps)"; printf '     got: %s\n' "$out" ;;
esac

# One deploy process: the files read fails once, then shows only README.md.
total=$((total + 1))
FAIL_FILES_ONCE=1 FILES='[{"filename":"README.md","status":"modified"}]' setup 3 "$NODEP" "$WF_PR" "$NORUNS"
out=$(bash "$PW" "$T/rec" deploy 2>&1)
sleeps=$(cat "$STUB_DIR/sleeps" 2>/dev/null || echo 0)
case "$out" in
  "no-deploy 7 - "*"and no deploy workflow")
    if [ "$(printf '%s\n' "$out" | grep -c .)" = 1 ] && [ "$sleeps" = 1 ]; then
      echo "ok   files read fails once, then no-deploy on the next poll"
    else
      fails=$((fails + 1)); echo "FAIL failed-then-good files read (sleeps: $sleeps)"; printf '     got: %s\n' "$out"
    fi ;;
  *) fails=$((fails + 1)); echo "FAIL failed-then-good files read (sleeps: $sleeps)"; printf '     got: %s\n' "$out" ;;
esac

echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]
