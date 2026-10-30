# claude-skills

Claude Code skills by Mark Guillermo, packaged as a plugin marketplace. Install only the ones you want.

```
/plugin marketplace add sforsparky/claude-skills
/plugin install project-handoff@sforsparky
/plugin install harvest-day@sforsparky
```

## Skills

| Plugin | What it does |
|---|---|
| [project-handoff](plugins/project-handoff/skills/project-handoff/SKILL.md) | Rewrites `HANDOFF.md` at the repo root with where the work stands, so the next session picks up cold. Ends by offering to clear the session. Pair it with a SessionStart hook that loads `HANDOFF.md`. |
| [harvest-day](plugins/harvest-day/skills/harvest-day/SKILL.md) | Rebuilds a day's work time from Claude Code session transcripts, maps each project folder to a Harvest project, shows you a table, and logs only what you approve. Needs the Harvest connector. Your folder map lives at `~/.claude/harvest-day/map.json` (created from `map.example.json` on first run). |

## Storyboarding

The storyboard skills (script → storyboard → generated graphics and B-roll) live in their own repo because they need a Python venv and a brand template: [sforsparky/storyboarding-skill](https://github.com/sforsparky/storyboarding-skill). Clone it and follow its README.

## License

MIT
