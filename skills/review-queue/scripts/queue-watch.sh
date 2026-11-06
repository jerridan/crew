#!/bin/bash
# Poll the review queue's sources and children, and print one line per new event.
#
# usage: queue-watch.sh <queue-dir> <session-id> [once]
#
# With no third argument, the script polls every 60 seconds until it is killed
# or until it prints `not-owner - -`. That is the `Monitor` command. With
# `once`, it runs one pass and exits. Only the seeded test uses `once`.
#
# Every line is `<kind> <owner>/<repo>#<n> <rest>`. The kinds are `push`,
# `queued`, `merged`, `closed` and `dequeued` (from `pr-watch.sh once`, one
# run for each board row that is not done), `ready` (a child wrote its
# `ready.json`), `ask` (a review request with no board row, only with no Slack
# token), `child-prompt`, `child-gone` and `child-idle`. The line `not-owner - -`
# means another session took the board: the script prints it and exits 0.
#
# The state of the last pass is in `<queue-dir>/watch-<session-id>.json`. A pass
# prints the events that the last pass did not hold. A pass with no state file
# prints nothing. A check that fails keeps the events it held, and prints
# nothing. `skills/review-queue/SKILL.md` says what the queue does with a line.
#
# It reads the board at each pass, and finds `pr-watch.sh` from its own path.
# Never copy this file into a record: a copy keeps the poll of the version that
# wrote it (design §15.123). It never prints the Slack token, and never reads
# it into a variable.

set -u

die() { printf 'queue-watch.sh: %s\n' "$1" >&2; exit 2; }

[ $# -ge 2 ] && [ $# -le 3 ] || die 'usage: queue-watch.sh <queue-dir> <session-id> [once]'
mode=${3:-loop}
case "$mode" in
  loop|once) ;;
  *) die "unknown mode '$mode'; use once or nothing" ;;
esac
queue=${1%/}
sid=$2
here=$(cd "$(dirname "$0")" && pwd)
prwatch="$here/../../delivered-window/scripts/pr-watch.sh"
[ -f "$prwatch" ] || die "no pr-watch.sh at $prwatch"
record_root=$(dirname "$queue")
board="$queue/board.json"
statef="$queue/watch-$sid.json"
W=''
trap '[ -z "$W" ] || rm -rf "$W"' EXIT

mtime() {
  if [ "$(uname)" = Darwin ]; then stat -f %m "$1" 2>/dev/null; else stat -c %Y "$1" 2>/dev/null; fi
}

# add_event <group> <kind> <label> <rest>: the dedupe key is the kind, the PR
# and the first word of the rest.
add_event() {
  local key="$2 $3 ${4%% *}"
  cut -f2 "$W/cur" | grep -Fxq -- "$key" && return 0
  printf '%s\t%s\t%s\n' "$1" "$key" "$(printf '%s %s %s' "$2" "$3" "$4" | tr '\t' ' ')" >> "$W/cur"
}

# Keep the events the last pass held for a group whose check failed.
carry() { awk -F'\t' -v g="$1" '$1 == g' "$W/prev" >> "$W/cur"; }

pr_poll() { # slug label dir
  local g="pr:$1" out line kind rest
  [ -f "$3/state.json" ] || return 0
  if ! jq -e '.run.watch | type == "object"' "$3/state.json" >/dev/null 2>&1; then carry "$g"; return 0; fi
  out=$(bash "$prwatch" "$3" once 2>/dev/null </dev/null); local rc=$?
  if [ "$rc" -ne 0 ] || ! printf '%s\n' "$out" | grep -Eq '^isDraft=(true|false)$'; then carry "$g"; return 0; fi
  while IFS= read -r line; do
    kind=${line%% *}
    case "$kind" in
      push|queued|merged|closed|dequeued) ;;
      *) continue ;;
    esac
    rest=${line#* }
    add_event "$g" "$kind" "$2" "$rest"
  done <<< "$out"
}

kid_prev() { # child: sets palive, pidle, pstart from the last pass
  palive=''; pidle=0; pstart='-'
  local l
  l=$(awk -F'\t' -v n="$1" '$1 == n' "$W/prevkids" | head -1)
  [ -z "$l" ] || IFS=$'\t' read -r _ palive pidle pstart <<< "$l"
}

kid_put() { printf '%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" >> "$W/kids"; }

child_carry() { # child
  carry "child:$1"
  [ -z "$palive" ] || kid_put "$1" "$palive" "$pidle" "$pstart"
}

child_check() { # slug label
  local child="review-$1" g="child:review-$1" err rc start alive=0 d='' f m pane prompt idle running fl
  kid_prev "$child"
  err=$(tmux has-session -t "=$child" 2>&1 </dev/null); rc=$?
  if [ "$rc" -eq 0 ]; then
    alive=1
  elif printf '%s' "$err" | grep -Eqi "can't find session|no server running|error connecting to|no sessions"; then
    alive=0
  else
    child_carry "$child"; return 0
  fi
  if [ "$alive" = 1 ]; then
    start=$(tmux display-message -p -t "=$child" '#{session_created}' 2>/dev/null </dev/null)
    case "$start" in
      ''|*[!0-9]*) child_carry "$child"; return 0 ;;
    esac
    [ "$start" = "$pstart" ] || pidle=0
  else
    # A child never seen alive has no start time and gets no line.
    [ "$palive" = true ] || return 0
    start=$pstart
  fi
  d=$(ls -dt "$record_root"/pr-"$1"-*/ 2>/dev/null | head -1); d=${d%/}
  if [ -n "$d" ] && [ -f "$d/ready.json" ]; then
    m=$(mtime "$d/ready.json")
    if [ -n "$m" ] && [ "$m" -gt "$start" ]; then
      add_event "$g" ready "$2" "$d/ready.json"
      kid_put "$child" true "$pidle" "$start"
      return 0
    fi
  fi
  if [ "$alive" = 0 ]; then
    add_event "$g" child-gone "$2" -
    kid_put "$child" true "$pidle" "$start"
    return 0
  fi
  pane=$(tmux capture-pane -p -t "=$child" 2>/dev/null </dev/null) || { child_carry "$child"; return 0; }
  prompt=0
  printf '%s' "$pane" | grep -Eq 'Do you want to proceed|❯ 1\. Yes|Esc to cancel' && prompt=1
  if printf '%s' "$pane" | grep -q 'esc to interrupt'; then idle=0; else idle=$((pidle + 1)); fi
  if [ "$prompt" = 1 ]; then
    add_event "$g" child-prompt "$2" -
  elif [ "$idle" -ge 3 ] && [ -n "$d" ]; then
    # Idle needs a quiet record directory and no skeptical review that runs.
    running=0
    for fl in "$d"/reviews/skeptical-r*-result.stderr; do
      [ -e "$fl" ] || continue
      [ -e "${fl%.stderr}.exit" ] || running=1
    done
    if [ "$running" = 0 ] && ! find "$d" -type f -mmin -10 2>/dev/null | head -1 | grep -q .; then
      add_event "$g" child-idle "$2" -
    fi
  fi
  kid_put "$child" true "$idle" "$start"
}

ask_poll() {
  local res asks r n u
  if ! res=$(gh search prs --review-requested=@me --state=open --limit 100 --json number,repository,url,title,author 2>/dev/null </dev/null) ||
     ! asks=$(printf '%s' "$res" | jq -r '.[] | [.repository.nameWithOwner, (.number | tostring), .url] | join("\t")' 2>/dev/null); then
    carry search; return 0
  fi
  while IFS=$'\t' read -r r n u; do
    [ -n "$r" ] || continue
    grep -Fxq -- "$r#$n" "$W/rowkeys" || add_event search ask "$r#$n" "$u"
  done <<< "$asks"
}

NOT_OWNER=''

pass() {
  local owner repo pr stage slug label g k l have_state=0
  W=$(mktemp -d "${TMPDIR:-/tmp}/queue-watch.XXXXXX") || return 0
  : > "$W/cur"; : > "$W/kids"; : > "$W/prev"; : > "$W/prevkids"
  owner=$(jq -r '.owner.session_id // ""' "$board" 2>/dev/null) && [ -n "$owner" ] || { rm -rf "$W"; W=''; return 0; }
  if [ "$owner" != "$sid" ]; then
    echo 'not-owner - -'
    NOT_OWNER=1
    rm -rf "$W"; W=''
    return 0
  fi
  if [ -f "$statef" ] &&
     jq -r '.events[]? | [.g, .k, .l] | join("\t")' "$statef" > "$W/prev" 2>/dev/null &&
     jq -r '(.children // {}) | to_entries[] | [.key, (.value.alive | tostring), (.value.idle | tostring), (.value.start | tostring)] | join("\t")' "$statef" > "$W/prevkids" 2>/dev/null; then
    have_state=1
  else
    : > "$W/prev"; : > "$W/prevkids"
  fi
  jq -r '.rows[]? | [.repo, (.pr | tostring), .stage] | join("\t")' "$board" > "$W/rows" 2>/dev/null || { rm -rf "$W"; W=''; return 0; }
  awk -F'\t' '{print $1 "#" $2}' "$W/rows" > "$W/rowkeys"
  while IFS=$'\t' read -r repo pr stage; do
    slug="${repo%%/*}-${repo#*/}-$pr"
    label="$repo#$pr"
    case "$stage" in
      merged|closed) continue ;;
    esac
    pr_poll "$slug" "$label" "$queue/prs/$slug"
    case "$stage" in
      reviewing|fixing|rereview|blocked) child_check "$slug" "$label" ;;
    esac
  done < "$W/rows"
  if jq -e '[.watches[]? | select(.source == "github:review-requests" and .status == "active")] | length > 0' "$board" >/dev/null 2>&1 &&
     ! grep -q '[^[:space:]]' "$HOME/.claude/secrets/slack-token" 2>/dev/null; then
    ask_poll
  fi
  if [ "$have_state" = 1 ]; then
    while IFS=$'\t' read -r g k l; do
      [ -n "$k" ] || continue
      cut -f2 "$W/prev" | grep -Fxq -- "$k" || printf '%s\n' "$l"
    done < "$W/cur"
  fi
  if jq -n --rawfile ev "$W/cur" --rawfile kids "$W/kids" '{
      version: 1,
      events: ($ev | split("\n") | map(select(length > 0) | split("\t") | {g: .[0], k: .[1], l: (.[2:] | join("\t"))})),
      children: ($kids | split("\n") | map(select(length > 0) | split("\t")
        | {key: .[0], value: {alive: (.[1] == "true"), idle: (.[2] | tonumber), start: .[3]}}) | from_entries)
    }' > "$statef.tmp.$$" 2>/dev/null; then
    mv "$statef.tmp.$$" "$statef"
  else
    rm -f "$statef.tmp.$$"
  fi
  rm -rf "$W"; W=''
}

while :; do
  pass
  [ -z "$NOT_OWNER" ] || exit 0
  [ "$mode" != once ] || exit 0
  sleep 60
done
