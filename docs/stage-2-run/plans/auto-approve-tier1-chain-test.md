# Plan: auto-approve-tier1-chain-test

## Finding

`plugins/auto-approve/scripts/auto-approve.py` splits chained commands on
`&&`, `||`, `|`, `;`, and newline (see `_CHAIN_OPS` / `_quote_aware_split`,
lines 157-191). The existing test suite exercises `&&` chains, `cd`/`sleep`
prefixes, subshell/`-exec` escapes, and env-var prefixes, but never drives a
command through `;`, `||`, or `|` directly, and never mixes more than one
operator in a single command. That is real, currently-installed Tier 1
logic with zero test coverage.

## New test

Add `test_mixed_chain_operators()` to
`plugins/auto-approve/scripts/test-auto-approve.py`:

1. A command that mixes `&&`, `;`, `||`, and `|` where every segment is a
   known-safe command (e.g.
   `git status && ls -la; pwd || echo done | cat`) — expect `allow` /
   `T1: Safe Command`.
2. The same style of mixed-operator chain, but with one unsafe command
   buried after several safe segments (e.g.
   `git status && ls -la; pwd || rm -rf /tmp/foo`) — expect NOT Tier 1
   (`assert_not_t1`), since one unsafe segment must block the whole chain.
3. A simple `;`-only chain of safe commands, and a simple `||`-only chain
   of safe commands, each as their own case, to cover those operators in
   isolation too (not just inside the mixed case).

Follow the file's existing style: use `run_hook`, `assert_decision`, and
`assert_not_t1`; print a `--- ... ---` section header; call the new test
function from the `__main__` block after the last existing call
(`test_opus_response_parser()`).

## Verification

Run:
```
cd <worktree-root>/agent-teams && python plugins/auto-approve/scripts/test-auto-approve.py
```
Confirm baseline is `199 passed, 0 failed` before the change, and the run
after the change prints `Results: N passed, 0 failed` with `N >= 200` and
zero failures.

## Commit

One commit: add the new test function and its `__main__` call.
