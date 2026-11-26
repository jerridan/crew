#!/bin/bash
# Seeded test of the default deploy signal of pr-watch.sh (AC1 of issue 144).
#
# usage: bash skills/delivered-window/scripts/test-pr-watch-deploy.sh
#
# It builds a record under a temp directory, puts a stub `gh` first in PATH,
# and runs `pr-watch.sh <record> deploy-once` once per case. The stub reads
# raw JSON from files under $STUB_DIR and applies the `--jq` filter of the
# call with `jq`, as `gh` does. For the runs endpoints it filters by `head_sha`,
# `event` and workflow id, serves 100 runs per `page`, and follows pages with
# `--paginate` (the `--jq` applies per page), as GitHub does. It exits 0 only
# when every check passes.

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
  *"/actions/runs"*|*"/actions/workflows/"*"/runs"*)
    echo "$args" >> "$D/calls"
    [ -e "$D/fail-runs" ] && exit 1
    case "$args" in *event=workflow_run*) [ -e "$D/fail-wfrun" ] && exit 1 ;; esac
    [ -f "$D/runs.json" ] || exit 1
    sha=''; ev=''; wf=''; page=1
    case "$args" in *"/actions/workflows/"*"/runs"*) wf=${args#*/actions/workflows/}; wf=${wf%%/*} ;; esac
    case "$args" in *head_sha=*) sha=${args#*head_sha=}; sha=${sha%%[&\ ]*} ;; esac
    case "$args" in *event=*) ev=${args#*event=}; ev=${ev%%[&\ ]*} ;; esac
    case "$args" in *page=*) q=${args#*&page=}; [ "$q" != "$args" ] && page=${q%%[&\ ]*} ;; esac
    pg() {
      jq -c --arg sha "$sha" --arg ev "$ev" --arg wf "$wf" --argjson p "$1" '
        {workflow_runs: ([.workflow_runs[]
          | select($sha == "" or (.head_sha // $ENV.STUB_OID) == $sha)
          | select($ev == "" or .event == $ev)
          | select($wf == "" or (.workflow_id | tostring) == $wf)]
          | .[($p - 1) * 100 : $p * 100])}' "$D/runs.json"
    }
    case "$args" in
      *--paginate*)
        while :; do
          out=$(pg "$page") || exit 1
          [ "$(printf '%s' "$out" | jq '.workflow_runs | length')" != 0 ] || exit 0
          if [ -n "$expr" ]; then printf '%s' "$out" | jq -r "$expr" || exit 1; else printf '%s\n' "$out"; fi
          page=$((page + 1))
        done ;;
      *)
        out=$(pg "$page") || exit 1
        if [ -n "$expr" ]; then printf '%s' "$out" | jq -r "$expr" || exit 1; else printf '%s\n' "$out"; fi
        exit 0 ;;
    esac ;;
  *"/actions/workflows"*)
    [ -e "$D/fail-workflows" ] && exit 1
    if [ -e "$D/fail-workflows-once" ]; then rm -f "$D/fail-workflows-once"; exit 1; fi
    echo "$args" >> "$D/calls"
    emit "$D/workflows.json" ;;
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
export STUB_OID=$OID
export PATH="$T/bin:$PATH"

# setup <minutes since merge> <deployments json> <workflows json> <runs json>
# Set FILES to the PR files json, FAIL_WF=1 for a workflows read that always
# fails, FAIL_WF_ONCE=1 or FAIL_FILES_ONCE=1 for a read that fails once,
# FAIL_RUNS=1 for a runs read that always fails, FAIL_WFRUN=1 for a read of
# the `workflow_run` event that always fails.
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
  [ -z "${FAIL_RUNS:-}" ] || : > "$STUB_DIR/fail-runs"
  [ -z "${FAIL_WFRUN:-}" ] || : > "$STUB_DIR/fail-wfrun"
}

# check <label> <want> : want is `none` (no output), `no-deploy-wf` (the no
# deploy workflow text) or `no-deploy-wait` (the 10-minute text), each exactly
# one line, `deployed`, `deployed:<id>:<n>` (one line, naming run <id> and
# <n> succeeded runs), `failed:<id>` (one deploy-failed line naming <id>) or
# `timeout`. REC=<dir> before a call picks another record.
check() {
  total=$((total + 1))
  out=$(bash "$PW" "${REC:-$T/rec}" deploy-once 2>&1)
  lines=$(printf '%s' "$out" | grep -c .)
  ok=''
  case "$2" in
    none) [ -z "$out" ] && ok=1 ;;
    no-deploy-wf) [ "$lines" = 1 ] && case "$out" in "no-deploy 7 - "*"and no deploy workflow") true ;; *) false ;; esac && ok=1 ;;
    no-deploy-wait) [ "$lines" = 1 ] && case "$out" in "no-deploy 7 - "*"or deploy runs") true ;; *) false ;; esac && ok=1 ;;
    deployed) case "$out" in "deployed "*) ok=1 ;; esac ;;
    deployed:*) w=${2#deployed:}; n=${w#*:}; w=${w%%:*}
      [ "$lines" = 1 ] && case "$out" in "deployed $w - "*"$n deploy runs succeeded") true ;; *) false ;; esac && ok=1 ;;
    failed:*) w=${2#failed:}
      [ "$lines" = 1 ] && case "$out" in "deploy-failed $w - "*) true ;; *) false ;; esac && ok=1 ;;
    timeout) [ "$lines" = 1 ] && case "$out" in "deploy-timeout "*) true ;; *) false ;; esac && ok=1 ;;
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
DEPRUN='{"workflow_runs":[{"id":9,"name":"CI","path":".github/workflows/deploy.yml","event":"push","status":"completed","conclusion":"success","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}]}'

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
RDRUN='{"workflow_runs":[{"id":9,"name":"CI","path":".github/workflows/release-drafter.yml","event":"push","status":"completed","conclusion":"success","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}]}'
setup 3 "$NODEP" "$WF_RELEASE" "$RDRUN"; check 'release-drafter.yml run named CI with success, 3 minutes' none
NAMEDRUN='{"workflow_runs":[{"id":9,"name":"Deploy","path":".github/workflows/ci.yml","event":"push","status":"completed","conclusion":"success","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:01:00Z"}]}'
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

# --- The merge's own deploy runs (issue 146) ---
mkdir -p "$T/rec-named"
cat > "$T/rec-named/state.json" <<'EOF'
{"deliverables":[{"pr_url":"https://github.com/o/r/pull/7"}],
 "run":{"deploy":{"environment":null,"workflow":"Deploy CD","timeout_minutes":180,
 "source":"explicit","since":null,"ended":null}}}
EOF

# run <id> <name> <event> <status> <conclusion> <time> [workflow id]
run() {
  jq -nc --argjson id "$1" --arg name "$2" --arg ev "$3" --arg st "$4" --arg c "$5" --arg u "$6" --argjson w "${7:-1}" \
    '{id:$id,name:$name,event:$ev,status:$st,conclusion:(if $c == "" then null else $c end),
      created_at:$u,updated_at:$u,workflow_id:$w}'
}
runs() { printf '%s\n' "$@" | jq -sc '{workflow_runs: .}'; }
T1=2026-01-01T00:01:00Z; T2=2026-01-01T00:02:00Z; T3=2026-01-01T00:03:00Z

# AC1: the deploy run is on page 2 of the push runs, behind 250 schedule runs.
BIG=$(jq -nc '{workflow_runs: ([range(1; 151) | {id: ., name: (if . == 140 then "Deploy" else "Build" end),
  event: "push", status: "completed", conclusion: "success", created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z", workflow_id: 1}]
  + [range(1000; 1250) | {id: ., name: "Deploy nightly", event: "schedule", status: "completed",
  conclusion: "success", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", workflow_id: 2}])}')
setup 3 "$NODEP" "$WF_DEPLOY" "$BIG"; check 'AC1 deploy run on page 2 of 150' deployed:140:1
total=$((total + 1))
if grep -q 'event=push' "$STUB_DIR/calls" && grep -q 'event=workflow_run' "$STUB_DIR/calls" &&
  ! grep 'actions/runs' "$STUB_DIR/calls" | grep -qv 'event='; then
  echo "ok   default rung reads only event=push and event=workflow_run"
else
  fails=$((fails + 1)); echo "FAIL default rung reads only event=push and event=workflow_run"; sed 's/^/     /' "$STUB_DIR/calls"
fi

# AC2: schedule and workflow_dispatch runs named like a deploy do not count.
SCHED=$(runs "$(run 1 'Deploy nightly' schedule completed success $T1)" "$(run 2 'Release' workflow_dispatch completed success $T2)")
setup 3 "$NODEP" "$WF_DEPLOY" "$SCHED"; check 'AC2 schedule and dispatch runs, 3 minutes' none
setup 11 "$NODEP" "$WF_DEPLOY" "$SCHED"; check 'AC2 schedule and dispatch runs, 11 minutes' no-deploy-wait

# AC3: the set of deploy runs of the merge, from both event streams.
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)" "$(run 2 'Deploy web' workflow_run in_progress '' $T2)")"
check 'AC3a push success, workflow_run in progress' none
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)" "$(run 2 'Deploy web' workflow_run completed success $T2)")"
check 'AC3b push and workflow_run both succeed' deployed:2:2
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)" "$(run 2 'Deploy web' workflow_run completed failure $T2)")"
check 'AC3c push success, workflow_run failure' failed:2
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed failure $T1)" "$(run 2 'Deploy web' workflow_run completed timed_out $T3)" "$(run 3 'Release' push completed success $T2)")"
check 'two failures name the latest' failed:2
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)" "$(run 2 CI push in_progress '' $T2)")"
check 'AC3d deploy success, push CI in progress' none
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)" "$(run 2 Notify workflow_run in_progress '' $T2)")"
check 'deploy success, workflow_run Notify in progress' none
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)" "$(run 2 'Deploy web' workflow_run completed cancelled $T2)")"
check 'a cancelled deploy run neither blocks nor counts' deployed:1:1
setup 3 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed cancelled $T1)" "$(run 2 'Deploy web' workflow_run completed skipped $T2)")"
check 'only cancelled and skipped deploy runs' none

# A failed runs read is no result: no line from the run judgment or the no-deploy wait.
FAIL_WFRUN=1 setup 11 "$NODEP" "$WF_PR" "$(runs "$(run 1 'Deploy api' push completed success $T1)")"
check 'workflow_run read fails, 11 minutes' none
FAIL_WFRUN=1 setup 3 "$NODEP" "$WF_PR" "$NORUNS"
check 'workflow_run read fails, no deploy workflow, 3 minutes' none
FAIL_RUNS=1 setup 11 "$NODEP" "$WF_PR" "$NORUNS"
check 'both runs reads fail, 11 minutes' none
FAIL_WFRUN=1 setup 200 "$NODEP" "$WF_PR" "$NORUNS"
check 'workflow_run read fails past the timeout' timeout

# AC4: Deploy: workflow: <name> reads the workflow's own runs, with every event.
WFN='{"workflows":[{"id":56,"name":"CI","path":".github/workflows/ci.yml","state":"active"},{"id":55,"name":"Deploy CD","path":".github/workflows/cd.yml","state":"active"}]}'
OLD=$(jq -nc '[range(1; 121) | {id: (100 + .), name: "Deploy CD", event: "workflow_dispatch", status: "completed",
  conclusion: "cancelled", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", workflow_id: 55}]')
NEWOK=$(run 1 'Deploy CD' workflow_dispatch completed success $T2 55)
NEWBAD=$(run 2 'Deploy CD' schedule completed failure $T3 55)
WFRUNS=$(jq -nc --argjson o "$OLD" --argjson a "$NEWOK" '{workflow_runs: ($o[0:110] + [$a] + $o[110:])}')
export REC="$T/rec-named"
setup 3 "$NODEP" "$WFN" "$WFRUNS"; check 'AC4 named workflow run on page 2' deployed:1:1
total=$((total + 1))
if grep -q 'actions/workflows/55/runs' "$STUB_DIR/calls" && ! grep -q 'actions/runs' "$STUB_DIR/calls"; then
  echo "ok   named rung reads the workflow's runs only"
else
  fails=$((fails + 1)); echo "FAIL named rung reads the workflow's runs only"; sed 's/^/     /' "$STUB_DIR/calls"
fi
setup 3 "$NODEP" "$WFN" "$(jq -nc --argjson w "$WFRUNS" --argjson b "$NEWBAD" '{workflow_runs: ($w.workflow_runs + [$b])}')"
check 'AC4 a newer run of that name failed' failed:2
setup 3 "$NODEP" '{"workflows":[{"id":56,"name":"CI","state":"active"}]}' "$WFRUNS"
check 'named workflow does not exist, 3 minutes' none
FAIL_WF=1 setup 3 "$NODEP" "$WFN" "$WFRUNS"
check 'named workflow read fails' none
FAIL_RUNS=1 setup 3 "$NODEP" "$WFN" "$WFRUNS"
check 'named workflow runs read fails' none
FAIL_RUNS=1 setup 200 "$NODEP" "$WFN" "$WFRUNS"
check 'named workflow runs read fails past the timeout' timeout
unset REC

echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]
