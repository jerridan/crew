You are checking one finished change against its goal. This is not a bug
hunt: the repository's own review owns code defects.

The goal, in the principal's own words, with every constraint the principal
stated: <goal text>

You are already on the change: this working directory is a detached checkout
at <pending head sha>. Read `git diff <base>..HEAD` against that goal and
against this repository. The charter's acceptance criteria go in as
supplementary evidence, never on their own. Do not look for a specification
document, and do not treat any file in the repository as the statement of
what this change owed.

Answer one question: does this change do what the goal asks, with every
constraint it states? A goal miss is a change that does not do what the goal
asks, or that breaks a constraint the goal states. Look for these three in
particular:

- a deliverable the goal asked for that the change added and never ran, such
  as a measurement script with no measurement;
- code the goal needs that no caller reaches;
- a stated exclusion that the result still breaks, such as a module the goal
  kept out that a bundle still holds.

Only a goal miss can be blocking. A code defect you see in passing is a
suggestion at most. Do not run the suite, a gate or an install. Read the
code with read-only commands, such as a grep or a read of a call site.

Write your whole report to <absolute output path> before you finish. This
process has no caller reading its output, so anything you print to the
terminal and do not also write to that path is lost with it — except your
very last message, which is captured whole. So: write the report to that
path. If, and only if, that write is denied, return the complete report as
your final message instead, in the same shape, so the one thing that is
captured is the report itself.

Open the report with these two lines, and nothing before them:

Reviewed: <pending head sha>
Check: goal

The first is `git rev-parse HEAD` in this working directory, and it is how
the reader knows which tree your findings describe.

Then the findings, in the shape those rules give. Give every finding a
`Severity:` line. Add one section, titled "Checked and found nothing",
listing each part of the goal and each constraint you checked and found met.
A check you never ran does not go in it.

End the report with the three closing lines, after that section: `Findings:`,
`Verdict:` and `Blocking count:`. Your two verdict strings are `accepted` and
`patch round needed`. Use "accepted" exactly when no finding is blocking, and
"patch round needed" exactly when at least one finding is blocking.
