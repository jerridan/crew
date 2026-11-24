The change has a new head. In this session you reviewed <previous head sha>.
This working directory is now a detached checkout at <pending head sha>.

<later-round block>

Follow your first instructions on the suite. Use the same two verdict
strings as before. Open the report with this line, and nothing before it:

Reviewed: <pending head sha>

Give every finding a `Severity:` line. End the report with the three closing
lines: `Findings:`, `Verdict:` and `Blocking count:`. Your first instructions
may name an older count line. Write `Blocking count:` instead.

<output sentence>

Do not write to <previous report path>. That file is the
report of your last round.
