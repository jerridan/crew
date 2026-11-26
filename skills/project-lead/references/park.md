# Park

This file owns the park: when a project lead ends its large session at a long
wait, the call that does it, the rules of the small waiter session that takes
its place, and the wake. `crew-step.md` owns the `park` and `unpark` command
lines. `record-format.md` owns `run.park`, `run.parks` and the `park/` files.

A park ends your session and starts a **waiter** in its place. The waiter has
your session name, working directory and model, and it holds only its first
prompt. A wake after hours then rewrites the waiter's small context, not the
build context. The run goes on from the record, as `resume.md` says.

For now, a park needs `run.orchestrator`. The orchestrator record holds the
launch identity of your session, and a hand-started session has none. A run
with no orchestrator waits in place, as `autonomy-contract.md` says. This is
the current limit, and a later change can add a park for a hand-started run. A `/crew:review`
run never parks.

## When you park

Every goal-run path parks the same way: the simple, light, full and
investigation paths.

| The wait | What you do |
|---|---|
| `stopped` at the usage limit, or a pause message for the usage window | Do steps 1 to 4 of `autonomy-contract.md`'s "The usage limit line". Then arm `crew-usage.py wait`. A project lead parks with `--reason usage` and `--until <reset epoch>` when the reset is more than 30 minutes away. Otherwise it waits in place. |
| A pause or stop message from the orchestrator | Commit. Then park with `--reason pause --by <the principal's name>` at once, whatever the length. The principal's name is `run.principal`. With an orchestrator, that is the orchestrator. When the pause is for the usage window, arm `wait` first and pass `--until`. |
| An escalation, sent | When no IC works and no background task the run needs is armed, arm a background timer of 30 minutes. An answer before it ends goes on in place. When the timer exits, park with `--reason question`. |

**Never park while an IC works or a worktree is dirty.** An IC dies with the
session. Tell each IC to commit its work and stop first, as the usage limit
line says, and wait for its report.

## The call

1. Write `handover.md` with all nine headings filled, as at the hand-over.
   Heading 8 holds one line that points at `run.park`.
2. Commit.
3. Arm the in-place wait of the table above, when it has one. A failed park
   leaves this session alive, and its wait then runs as it would have.
4. Run `crew-step.py park` as `crew-step.md` says, with `--next` set to the
   step the resumed run takes first.
5. On exit 0, end your turn. The helper starts the waiter, then stops this
   session after its delay. A wake during that delay is safe: the helper
   reads the record again before each write and each stop, as
   `crew-step.md` says.
6. On exit 1, read the line. Nothing was parked. Fix the cause or wait in
   place.

A park that fails after the waiter started rolls back. The waiter stops, the
park moves to `run.parks` with a `failed` entry, and this session stays.

## The waiter

Follow this section when your first prompt names it. You hold the record
directory and the goal slug and nothing else.

1. Answer the prompt with one line. Read `run.park` from `state.json`.
2. When `run.park.reason` is `usage`, or is `pause` for the usage window, and
   the charter has a `Usage limit:` line, arm `crew-usage.py wait` as a
   background Bash command.
3. When `run.park.until` is set and no `crew-usage.py wait` runs, arm a
   background timer that ends at that epoch:
   `sleep $(( <until> - $(date +%s) ))`. No `wait` runs when step 2 armed
   none, or when `wait` exited 1. A time in the past ends the timer at once.
4. Wait. A message or typed text wakes you only as the table says.

| `run.park.reason` | What wakes the run |
|---|---|
| `usage` | `crew-usage.py wait` exits 0, or a resume word from the principal |
| `pause` | a resume word from the principal, or `wait` exits 0 when the pause was for the usage window |
| `question` | a message that answers the open question |
| any reason, with `run.park.until` set | the timer of step 3 exits |

**Only exit 0 of `wait` is a reset.** Exit 1 means no usage figures exist.
Arm the timer of step 3 when `run.park.until` is set. Else stay parked, say
in one line that you wait for a word, and wait for one.

**Any other message keeps you parked.** A `rejoin` after an orchestrator
restart is one, and so is a status request, and so is a pause or stop word.
Answer in one line from the record: the stage, the park reason, the until
time when `run.park.until` is set, and the open question. Re-arm `wait` or
the timer when the reason needs one and none runs. Do not resume.

## The wake

On a wake, invoke `crew:project-lead` with `--resume <goal-slug>`. The wake
message stays in your context, and the resumed run acts on it. `resume.md`
owns what the resumed run does first.
