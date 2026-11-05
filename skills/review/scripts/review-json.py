#!/usr/bin/env python3
"""Build the JSON of a review post from a draft file.

usage: review-json.py <draft path> --commit <sha> --event <EVENT>

The draft has the shape `github-review.md` "The draft file" gives: a
`--- summary` section, a `--- body` section, then one `--- comment` block per
inline comment. The script prints the JSON that "The post command" takes. The
summary never reaches the output.

A section's text is every line between its header and the next header, or
the end of the file. The one blank line before the next header is not part of
it, and neither is the line break that ends the last text line. A comment
block starts with its `path:`, `line:` and `side:` lines and one blank line.
Those are fields. The script changes no other byte.

Exit 2, with a message on stderr, when the draft is malformed or when the
body or a comment does not end in a `<!-- pr-review: ` marker line.
"""

import json
import sys

MARKER = "<!-- pr-review: "
HEADERS = ("--- summary", "--- body", "--- comment")


def fail(message):
    print(f"review-json.py: {message}", file=sys.stderr)
    sys.exit(2)


def split_sections(text):
    """Return a list of (header, lines) in file order."""
    lines = text.split("\n")
    sections = []
    for line in lines:
        if line in HEADERS:
            sections.append((line, []))
        elif sections:
            sections[-1][1].append(line)
        elif line != "":
            fail("text before the first '--- ' header")
    for _, body in sections:
        # The last element is the blank line before the next header, or the
        # empty piece after the final line break of the file.
        if body and body[-1] == "":
            body.pop()
    return sections


def check_marker(label, text):
    if not text.split("\n")[-1].startswith(MARKER):
        fail(f"the last line of {label} does not start with '{MARKER}'")


def parse_comment(index, lines):
    fields = {}
    for key in ("path", "line", "side"):
        if not lines or not lines[0].startswith(key + ": "):
            fail(f"comment {index} needs a '{key}: ' line in order path, line, side")
        fields[key] = lines.pop(0)[len(key) + 2:]
    if not lines or lines[0] != "":
        fail(f"comment {index} needs one blank line after its fields")
    lines.pop(0)
    try:
        fields["line"] = int(fields["line"])
    except ValueError:
        fail(f"comment {index} has a line that is not an integer")
    text = "\n".join(lines)
    check_marker(f"comment {index}", text)
    return {"path": fields["path"], "line": fields["line"],
            "side": fields["side"], "body": text}


def main(argv):
    if len(argv) != 6 or argv[2] != "--commit" or argv[4] != "--event":
        fail("usage: review-json.py <draft path> --commit <sha> --event <EVENT>")
    path, commit, event = argv[1], argv[3], argv[5]
    try:
        with open(path, "rb") as f:
            text = f.read().decode("utf-8")
    except (OSError, UnicodeDecodeError) as e:
        fail(f"cannot read {path}: {e}")
    sections = split_sections(text)
    bodies = [lines for header, lines in sections if header == "--- body"]
    if len(bodies) != 1:
        fail("the draft needs exactly one '--- body' section")
    body = "\n".join(bodies[0])
    check_marker("the body", body)
    comments = [parse_comment(i, list(lines)) for i, (header, lines)
                in enumerate((s for s in sections if s[0] == "--- comment"), 1)]
    out = {"commit_id": commit, "event": event, "body": body, "comments": comments}
    sys.stdout.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")


main(sys.argv)
