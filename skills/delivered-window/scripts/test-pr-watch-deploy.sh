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
  if [ -n "$expr" ]; then jq -r "$expr" "$1"; else cat "$1"; fi
  exit 0
}
case "$args" in
  "pr view"*) emit "$D/pr.json" ;;
  *"/deployments/"*"/statuses"*) emit "$D/statuses.json" ;;
  *"/deployments?sha="*) emit "$D/deployments.json" ;;
  *"/deployments?per_page"*) emit "$D/deployments.json" ;;
  *"/actions/workflows"*) [ -e "$D/fail-workflows" ] && exit 1; emit "$D/workflows.json" ;;
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

export STUB_DIR="$T/stub"
export PATH="$T/bin:$PATH"

# case <name> <minutes since merge> <deployments json> <workflows json> <runs json>
# Add `fail-workflows` to $STUB_DIR by setting FAIL_WF=1 before the call.
setup() {
  rm -rf "$STUB_DIR"; mkdir -p "$STUB_DIR"
  merged=$(date -u -v-"$1"M +%Y-%m-%dT%H:%M:%SZ)
  printf '{"state":"MERGED","mergeCommit":{"oid":"%s"},"mergedAt":"%s"}\n' "$OID" "$merged" > "$STUB_DIR/pr.json"
  printf '%s\n' "$2" > "$STUB_DIR/deployments.json"
  printf '%s\n' "$3" > "$STUB_DIR/workflows.json"
  printf '%s\n' "$4" > "$STUB_DIR/runs.json"
  printf '[{"state":"success","created_at":"2026-01-01T00:00:00Z"}]\n' > "$STUB_DIR/statuses.json"
  [ -z "${FAIL_WF:-}" ] || : > "$STUB_DIR/fail-workflows"
}

# check <label> <want> : want is `none`, `no-deploy`, `deployed` or `not-no-deploy`.
check() {
  total=$((total + 1))
  out=$(bash "$PW" "$T/rec" deploy-once 2>&1)
  lines=$(printf '%s' "$out" | grep -c .)
  ok=''
  case "$2" in
    none) [ -z "$out" ] && ok=1 ;;
    no-deploy) [ "$lines" = 1 ] && case "$out" in "no-deploy 7 - "*) true ;; *) false ;; esac && ok=1 ;;
    deployed) case "$out" in "deployed "*) ok=1 ;; esac ;;
    not-no-deploy) case "$out" in *no-deploy*) ;; *) ok=1 ;; esac ;;
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

setup 1 "$NODEP" "$WF_PR" "$NORUNS";      check 'no deploy workflow, merged 1 minute ago' no-deploy
setup 1 "$NODEP" "$WF_DEPLOY" "$NORUNS";  check 'workflow Deploy, no run, 1 minute' none
setup 11 "$NODEP" "$WF_DEPLOY" "$NORUNS"; check 'workflow Deploy, no run, 11 minutes' no-deploy
setup 1 "$NODEP" "$WF_RELEASE" "$NORUNS"; check 'release.yml named CI, no run, 1 minute' none
setup 11 "$NODEP" "$WF_RELEASE" "$NORUNS"; check 'release.yml named CI, no run, 11 minutes' no-deploy
FAIL_WF=1 setup 1 "$NODEP" "$WF_PR" "$NORUNS"; check 'workflows read fails, 1 minute' none
setup 1 "$OTHERDEP" "$WF_PR" "$NORUNS";   check 'a deployment exists, no deploy workflow' not-no-deploy
setup 1 "$OTHERDEP" "$WF_DEPLOY" "$NORUNS"; check 'a deployment exists, a deploy workflow' not-no-deploy
setup 1 "$PRODDEP" "$WF_PR" "$NORUNS";    check 'production deployment with success' deployed
setup 1 "$NODEP" "$WF_OFF" "$NORUNS";     check 'only a disabled Deploy workflow' no-deploy
setup 1 "$NODEP" "$WF_RELEASE" "$DEPRUN"; check 'run of deploy.yml named CI with success' deployed

echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]
