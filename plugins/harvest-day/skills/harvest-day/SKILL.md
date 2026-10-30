---
name: harvest-day
description: Log a day's Claude Code work time to Harvest, rebuilt from session transcripts and grouped by project folder. Use when the user says "/harvest-day", "log my time", "log today in Harvest", "what did I work on today", or asks to fill in their timesheet for a date. Optional argument is a date (YYYY-MM-DD, "yesterday", a weekday) or a range.
---

# harvest-day

Rebuild time from `~/.claude/projects/*/*.jsonl`, map each folder to a Harvest project, show the user a table, and log only what they approve.

Files in this skill folder:
- `harvest_day.py`: prints JSON for one day: entries per project with `hours`, `blocks`, and sample `prompts`, plus `total_hours`, `wall_clock_hours` and `overlap_hours`.
- `map.example.json`: template for the folder map.

The folder map lives at `~/.claude/harvest-day/map.json`, outside this folder so plugin updates keep it. The script copies `map.example.json` there on first run. It maps folder prefixes to Harvest project and task ids. `roots` lists parent folders (default `~/Developer`, `~/Developer/projects`) whose direct children count as one repo when grouping unmapped work.

Needs the Harvest connector (`list_time_entries`, `list_projects`, `list_project_assignments`, `log_time`).

## Steps

1. Resolve the date (default today, local time). For a range, repeat steps 2–6 per day, then show one table.
2. Run `python3 ${CLAUDE_SKILL_DIR}/harvest_day.py <YYYY-MM-DD>`. Defaults: a gap of more than 15 min ends a work block, and 5 min is added after each block. Pass `--gap` or `--tail` only if the user asks.
3. Call Harvest `list_time_entries` with `from`/`to` set to that date. Any project that already has time logged that day is a likely duplicate: show the existing hours next to the new hours and default to skipping it.
4. Unmapped entries have `key: null` and a `folder`. Group them and ask the user with AskUserQuestion which Harvest project and task each belongs to, or whether to ignore it. Options come from `list_projects` and `list_project_assignments`. Save each answer to `~/.claude/harvest-day/map.json`: add to `projects` if new, add the folder prefix to `folders` (or to `ignore`), so it never gets asked again.
5. Build the table: project, task, `split_hours` (the default to log), raw `hours`, and a one-line note summarizing the prompts in the user's words (no "Claude", no tool names). `split_hours` counts every minute once: when sessions overlap, each minute goes to the project the user prompted most recently, because their attention is what gets billed, not Claude's run time. They add up to `wall_clock_hours`. If an overlap involves a fixed-fee or personal project, suggest moving the overlap there so hourly clients get only clean time. Bill the raw `hours` (double-counting) only if the user says so for that row.
6. Get explicit approval for the final table. Then call `log_time` once per row with `project_id`, `task_id`, `hours`, `spent_at`, `notes`. Report each result. Never claim a row was logged unless the tool returned success.

## Rules

- Never log without approval in this run. An approval doesn't carry over to another day.
- Harvest rounds displayed hours up to 6 min. Log raw hours and let Harvest round.
- Transcripts are deleted after `cleanupPeriodDays` (30 by default). Past that, the day can't be rebuilt; say so.
- The task in `map.json` is only a default. If the prompts show other work (design, a meeting or call prep, admin), suggest that project's task instead.
