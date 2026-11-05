# Severity rubric, v1

**Blocking.** Merging as-is harms a user, a customer or the business on a path people take. Any of: a defect on the normal path; a security hole; a break of a contract another service or client relies on; stored data or a customer's record lost or silently corrupted, even on an uncommon path; a missing test when the changed behaviour has no test at all, or when an existing test asserts the wrong behaviour and would pass on the bug.

**Suggestion.** Real and worth a comment; the author decides. A latent defect with no live caller; loss of unsaved work the person can redo, reached only by an unusual sequence; a missing test for one branch or case of behaviour that is otherwise tested; a wrong status code or message where the outcome is still correct.

**Nit.** Correct but minor: naming, a comment, a clearer message, a small duplication. Post only when cheap to fix.

**Don't post.** True but not worth the author's time: style the repo does not enforce, hypothetical misuse, a note that restates the PR body, a rule violation with no effect.

**Not real.** The code contradicts the claim, or the case cannot happen. A fact decided with the code open, never by vote.

**Unsure.** The repository does not settle it (needs production data, a runtime, or an external service).

Open lines: a process gap on the PR alone leans suggestion; a 500 where a 400 was due, with the write still rejected, is blocking.
