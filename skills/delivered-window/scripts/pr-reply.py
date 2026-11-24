#!/usr/bin/env python3
"""Post a round's replies on the PR, and find the replies a round posted.

usage:
  pr-reply.py send <record-dir> <round-id> <replies-file> [--mark-replied]
  pr-reply.py posted <record-dir> <round-id>

The replies file holds every reply of the round. A line that starts `=== `
opens a reply:

  === <kind> <item-id> [to <comment-id>] [resolve]
  <body>

The kinds are `review-comment`, `review`, `comment`, `check` and `dequeued`.
`to` and `resolve` are for `review-comment` only. The script drops the blank
lines at the end of each body, then adds the marker
`<!-- pr-review: <round-id> <item-id> -->` as the last line. A body reaches
GitHub byte for byte, through a file. The PR is the one deliverable `pr_url`
of `state.json`. Only a marker from the login of `gh api user` counts as a
reply already posted.

`send` prints one line per item: `posted <item-id> <reply-id>`,
`skipped <item-id> <reply-id> already posted`, `resolved <item-id>
<thread-id>` or `failed <item-id> <step>: <message>`, and exits 1 when an item
failed. With `--mark-replied` and no failure it then runs
`crew-record.py round replied <round-id>`. `posted` prints
`<item-id> <reply-id>` per reply. A usage or file error prints
`pr-reply.py: <message>` on stderr and exits 2, before any post.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD_PY = HERE.parent.parent / "project-lead" / "scripts" / "crew-record.py"
KINDS = ("review-comment", "review", "comment", "check", "dequeued")


class Failed(Exception):
    """One step failed. For an item, the loop goes on."""


def fail(message):
    print(f"pr-reply.py: {message}", file=sys.stderr)
    sys.exit(2)


def gh(*args):
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True)
    except OSError as exc:
        raise Failed(f"cannot run gh: {exc}")
    if done.returncode != 0:
        raise Failed(f"gh {' '.join(args[:2])} failed: {(done.stderr.strip() or 'no message')}")
    return done.stdout


def json_stream(text):
    """The values of back-to-back JSON documents, as `gh --paginate` prints them."""
    dec, i, out = json.JSONDecoder(), 0, []
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return out
        value, i = dec.raw_decode(text, i)
        out.append(value)


def pr_of(record):
    try:
        state = json.loads((Path(record) / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        fail(f"cannot read state.json in {record}; pass the record directory")
    urls = [d["pr_url"] for d in state.get("deliverables") or [] if d.get("pr_url")]
    if len(urls) != 1:
        fail("the record needs exactly one deliverable with a pr_url")
    m = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", urls[0].split("?")[0].split("#")[0].rstrip("/"))
    if not m:
        fail(f"pr_url '{urls[0]}' is not a GitHub PR URL")
    return urls[0], m.group(1), m.group(2), m.group(3)


def login():
    try:
        return gh("api", "user", "--jq", ".login").strip()
    except Failed as exc:
        fail(f"cannot read your login: {exc}; run `gh auth status`")


def marker(round_id, item):
    return f"<!-- pr-review: {round_id} {item} -->"


def find_posted(owner, repo, num, round_id, me):
    """item id -> reply id, for the markers of this round from this login."""
    prefix = f"<!-- pr-review: {round_id} "
    found = {}
    for kind in ("pulls", "issues"):
        try:
            pages = json_stream(gh("api", "--paginate", f"repos/{owner}/{repo}/{kind}/{num}/comments"))
        except (Failed, ValueError) as exc:
            fail(f"cannot read the {kind} comments: {exc}; check the network, then run it again")
        for page in pages:
            for c in page:
                if (c.get("user") or {}).get("login") != me:
                    continue
                body = (c.get("body") or "").replace("\r", "")
                if body.endswith("\n"):
                    body = body[:-1]
                last = body.split("\n")[-1]
                if last.startswith(prefix) and last.endswith(" -->"):
                    found.setdefault(last[len(prefix):-len(" -->")], c["id"])
    return found


def parse_replies(path):
    try:
        text = Path(path).read_bytes().decode("utf-8")
    except OSError as exc:
        fail(f"cannot read the replies file {path}: {exc}")
    replies, cur = [], None
    for raw in text.split("\n"):
        if raw.startswith("=== "):
            t = raw.rstrip("\r").split()[1:]
            if len(t) < 2 or t[0] not in KINDS:
                fail(f"cannot read the header '{raw[:60]}'. A header is `=== <kind> <item-id> [to <comment-id>] [resolve]`, "
                     f"and the kind is one of {', '.join(KINDS)}. Nothing was posted")
            cur = {"kind": t[0], "item": t[1], "to": None, "resolve": False, "lines": []}
            rest = t[2:]
            if rest[:1] == ["to"]:
                if len(rest) < 2:
                    fail(f"the header '{raw[:60]}' has `to` with no comment id. Nothing was posted")
                cur["to"], rest = rest[1], rest[2:]
            if rest == ["resolve"]:
                cur["resolve"], rest = True, []
            if rest:
                fail(f"cannot read the header '{raw[:60]}'. Nothing was posted")
            if (cur["to"] or cur["resolve"]) and cur["kind"] != "review-comment":
                fail(f"`to` and `resolve` are for review-comment only: '{raw[:60]}'. Nothing was posted")
            replies.append(cur)
        elif cur is None:
            if raw.strip():
                fail("the replies file has text before its first `=== ` header. Nothing was posted")
        else:
            cur["lines"].append(raw)
    if not replies:
        fail("the replies file has no reply. Nothing was posted")
    for r in replies:
        lines = r["lines"]
        while lines and lines[-1].strip() == "":
            lines.pop()
        if not lines:
            fail(f"the reply for {r['item']} has no body. Nothing was posted")
    return replies


def first_comment(owner, repo, comment):
    d = json.loads(gh("api", f"repos/{owner}/{repo}/pulls/comments/{comment}"))
    return d.get("in_reply_to_id") or d["id"]


def post_reply(rep, body_path, owner, repo, num, pr_url, first):
    if rep["kind"] == "review-comment":
        out = gh("api", "-X", "POST", f"repos/{owner}/{repo}/pulls/{num}/comments/{first}/replies",
                 "-F", f"body=@{body_path}")
        return json.loads(out)["id"]
    out = gh("pr", "comment", pr_url, "--body-file", body_path).strip()
    m = re.search(r"issuecomment-(\d+)", out)
    return m.group(1) if m else out.split()[-1]


def thread_of(owner, repo, num, first):
    query = ("query($owner: String!, $repo: String!, $n: Int!, $endCursor: String) {"
             " repository(owner: $owner, name: $repo) { pullRequest(number: $n) {"
             " reviewThreads(first: 100, after: $endCursor) {"
             " pageInfo { hasNextPage endCursor }"
             " nodes { id isResolved comments(first: 1) { nodes { databaseId } } } } } } }")
    out = gh("api", "graphql", "--paginate", "-f", f"owner={owner}", "-f", f"repo={repo}",
             "-F", f"n={num}", "-f", f"query={query}")
    for page in json_stream(out):
        for node in page["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]:
            comments = node["comments"]["nodes"]
            if comments and str(comments[0]["databaseId"]) == str(first):
                return node["id"], node["isResolved"]
    raise Failed(f"no review thread has the first comment {first}")


def resolve(thread):
    gh("api", "graphql", "-f", f"id={thread}", "-f",
       "query=mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { isResolved } } }")


def one_line(text):
    return " ".join(str(text).split())


def cmd_send(record, round_id, replies_file, mark):
    replies = parse_replies(replies_file)
    pr_url, owner, repo, num = pr_of(record)
    me = login()
    posted = find_posted(owner, repo, num, round_id, me)
    failed = False
    for rep in replies:
        item, step = rep["item"], "reply"
        target = rep["to"] or item
        first = None
        try:
            if item in posted:
                print(f"skipped {item} {posted[item]} already posted")
            else:
                if rep["kind"] == "review-comment":
                    step = "thread read"
                    first = first_comment(owner, repo, target)
                step = "reply"
                body = ("\n".join(rep["lines"]) + "\n" + marker(round_id, item) + "\n").encode("utf-8")
                fd, path = tempfile.mkstemp(prefix="pr-reply-")
                try:
                    with os.fdopen(fd, "wb") as f:
                        f.write(body)
                    rid = post_reply(rep, path, owner, repo, num, pr_url, first)
                finally:
                    os.unlink(path)
                print(f"posted {item} {rid}")
            if rep["resolve"]:
                step = "thread read"
                if first is None:
                    first = first_comment(owner, repo, target)
                thread, resolved = thread_of(owner, repo, num, first)
                step = "resolve"
                if not resolved:
                    resolve(thread)
                print(f"resolved {item} {thread}")
        except (Failed, ValueError, KeyError) as exc:
            failed = True
            print(f"failed {item} {step}: {one_line(exc)}")
        sys.stdout.flush()
    if failed:
        sys.exit(1)
    if mark:
        done = subprocess.run([sys.executable, str(RECORD_PY), str(record), "round", "replied", round_id],
                              capture_output=True, text=True)
        if done.returncode != 0:
            print(f"failed {round_id} round replied: {one_line(done.stderr or done.stdout)}")
            sys.exit(1)
        print(f"replied {round_id}")


def cmd_posted(record, round_id):
    _, owner, repo, num = pr_of(record)
    for item, rid in find_posted(owner, repo, num, round_id, login()).items():
        print(f"{item} {rid}")


def main(argv):
    if len(argv) >= 4 and argv[0] == "send" and len(argv) in (4, 5) and (len(argv) == 4 or argv[4] == "--mark-replied"):
        cmd_send(argv[1], argv[2], argv[3], len(argv) == 5)
    elif len(argv) == 3 and argv[0] == "posted":
        cmd_posted(argv[1], argv[2])
    else:
        fail("usage: pr-reply.py send <record-dir> <round-id> <replies-file> [--mark-replied] | posted <record-dir> <round-id>")


if __name__ == "__main__":
    main(sys.argv[1:])
