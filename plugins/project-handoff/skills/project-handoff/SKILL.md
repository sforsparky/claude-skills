---
name: project-handoff
description: Rewrite HANDOFF.md at the repo root with where the work stands, so the next session picks up cold. Use when the user says "handoff", "write the handoff", "wrap up the session", or is about to end a session on ongoing project work.
argument-hint: "Optional: what the next session will focus on"
---

Rewrite `HANDOFF.md` at the root of the current project (the git root, else the working directory). A SessionStart hook loads this file into every new session here, so it is the next session's first context.

## Rules

- **Replace, never append.** It describes now, not history. Git log is the history.
- **Under one page.** Short bullets. If a section is empty, write "None."
- **Don't duplicate.** Commits, diffs, specs, CLAUDE.md, client notes: point to them by path, SHA or URL instead of restating.
- **Redact** API keys, passwords, tokens, and personal data that does not belong in the repo.
- **Facts only.** Mark anything unverified as unverified. Use absolute dates (YYYY-MM-DD), never "yesterday".
- If the user passed an argument, tailor "Next up" to it.

## Gather first

1. `git log --oneline -15` and `git status --short` for what changed and what is uncommitted.
2. The existing `HANDOFF.md`, if any: carry forward items still open, drop items now done.
3. This conversation: decisions made, things flagged to the user, what is waiting on whom.

## Format

```markdown
# Handoff — <project name>
Updated YYYY-MM-DD · branch `<branch>` @ `<short sha>`

## Current state
- What works and where it is deployed or previewable.
- Anything uncommitted or half-done.

## Waiting on others
- <person/client>: <what> (since YYYY-MM-DD)

## Next up
1. Most important next step first.

## Gotchas
- Non-obvious traps for this project: ports, workarounds, flaky tools, rules that bite.

## Suggested skills
- Skills the next session should load, and why.
```

## After writing

- Do not commit on your own. If `HANDOFF.md` is new, ask once whether to commit it or add it to `.gitignore` (gitignore if the repo is shared with a client and the file holds private notes).
- If the project's CLAUDE.md names a client notes file, ask whether to update its status line too.
- Tell the user the path and the one-line gist of "Next up".

## Session housekeeping

Last, once the questions above are settled, offer to clear the session so the next one starts fresh from `HANDOFF.md`. Ask; never clear on your own.

- On yes, in the Claude desktop app: call `mcp__ccd_session_mgmt__clear_session` (load it with ToolSearch if deferred).
- On yes, in the CLI or where that tool is missing: tell the user to type `/clear`. You cannot run it yourself.
- Warn first if anything is uncommitted or a question is still open: clearing drops this conversation.
