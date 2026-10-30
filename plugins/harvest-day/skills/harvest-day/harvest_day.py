#!/usr/bin/env python3
"""Rebuild a day's Claude Code work time from transcripts, grouped by Harvest project.

Usage: harvest_day.py [YYYY-MM-DD] [--gap MIN] [--tail MIN]
Prints JSON. Reads ~/.claude/projects/*/*.jsonl (main sessions only, not subagents).
Folder map: ~/.claude/harvest-day/map.json, copied from map.example.json on first run.
"""
import argparse, glob, json, os, re, shutil
from datetime import datetime, date, timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
WORKTREE = re.compile(r"/\.claude/worktrees/[^/]+")
IGNORE = "!ignore"
# Outside the skill folder so plugin updates don't wipe the user's mappings.
MAP = os.path.expanduser("~/.claude/harvest-day/map.json")


def under(path, prefix):
    return path == prefix or path.startswith(prefix.rstrip("/") + "/")


def load_map():
    if not os.path.exists(MAP):
        os.makedirs(os.path.dirname(MAP), exist_ok=True)
        shutil.copy(os.path.join(HERE, "map.example.json"), MAP)
    m = json.load(open(MAP))
    folders = sorted(((os.path.expanduser(k), v) for k, v in m["folders"].items()), key=lambda kv: -len(kv[0]))
    roots = sorted((os.path.expanduser(r).rstrip("/") for r in m.get("roots", [])), key=len, reverse=True)
    return m["projects"], folders, [os.path.expanduser(p) for p in m.get("ignore", [])], roots


def repo_folder(cwd, roots):
    """Group an unmapped cwd under its repo: the first folder below the longest matching root."""
    for r in roots:
        if under(cwd, r) and cwd != r:
            return r + "/" + cwd[len(r) + 1:].split("/")[0]
    return cwd


def prompt_text(msg):
    c = msg.get("content")
    if isinstance(c, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in c):
            return None
        c = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
    c = (c or "").strip()
    # skip hook/command/system-injected turns
    if not c or c.startswith(("<", "Caveat:", "[Request interrupted", "[Image", "Base directory for this skill")):
        return None
    return " ".join(c.split())[:140]


def blocks(times, gap, tail):
    """Merge sorted datetimes into [start, end] blocks; gaps > gap split; each block gets tail added."""
    out = []
    for t in times:
        if out and t - out[-1][1] <= gap:
            out[-1][1] = t
        else:
            out.append([t, t])
    return [(s, e + tail) for s, e in out]


def merge(spans):
    out = []
    for s, e in sorted(spans):
        if out and s <= out[-1][1]:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def attention_split(spans_by, asked):
    """Hours per project with overlaps counted once: each minute where several projects are
    active goes to the one the user prompted most recently; if none was prompted yet, split evenly."""
    out = {}
    if not spans_by:
        return out
    t = min(s for sp in spans_by.values() for s, _ in sp).replace(second=0, microsecond=0)
    end = max(e for sp in spans_by.values() for _, e in sp)
    step = timedelta(minutes=1)
    while t < end:
        active = [k for k, sp in spans_by.items() if any(s <= t < e for s, e in sp)]
        if len(active) == 1:
            out[active[0]] = out.get(active[0], 0) + 1 / 60
        elif active:
            last = [k for at, k in asked if at <= t and k in active]
            for k in ([last[-1]] if last else active):
                out[k] = out.get(k, 0) + 1 / 60 / (1 if last else len(active))
        t += step
    return out


def hours(spans):
    return sum((e - s).total_seconds() for s, e in spans) / 3600


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("day", nargs="?", default=date.today().isoformat())
    ap.add_argument("--gap", type=int, default=15, help="minutes of silence that end a work block")
    ap.add_argument("--tail", type=int, default=5, help="minutes added after a block's last event")
    a = ap.parse_args()

    projects, folders, ignore, roots = load_map()
    day = date.fromisoformat(a.day)
    start = datetime.combine(day, datetime.min.time()).astimezone()
    end = start + timedelta(days=1)
    gap, tail = timedelta(minutes=a.gap), timedelta(minutes=a.tail)

    def resolve(cwd):
        if any(under(cwd, p) for p in ignore):
            return IGNORE
        return next((v for k, v in folders if under(cwd, k)), None)

    events = {}   # key -> [datetime]
    prompts = {}  # key -> [str]
    asked = []    # (datetime, key) for every prompt the user typed
    for f in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")):
        if os.path.getmtime(f) < start.timestamp():
            continue
        # A session belongs to the mapped folder it started in, even when it reads files in
        # another client's folder; sessions started in an unmapped folder fall back to each line's cwd.
        started, session_key = False, None
        for line in open(f, errors="ignore"):
            if '"timestamp"' not in line or '"cwd"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") not in ("user", "assistant") or d.get("isSidechain") or not d.get("cwd"):
                continue
            cwd = WORKTREE.sub("", d["cwd"])
            if not started:
                started, session_key = True, resolve(cwd)
            if session_key == IGNORE:
                break
            t = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")).astimezone()
            if not (start <= t < end):
                continue
            key = session_key or resolve(cwd)
            if key == IGNORE:
                continue
            if key is None:
                # unmapped: group subfolders under their repo folder
                key = "?" + repo_folder(cwd, roots)
            events.setdefault(key, []).append(t)
            if d["type"] == "user" and isinstance(d.get("message"), dict):
                p = prompt_text(d["message"])
                if p:
                    asked.append((t, key))
                if p and len(prompts.setdefault(key, [])) < 8 and p not in prompts[key]:
                    prompts[key].append(p)

    entries, all_spans = [], []
    spans_by = {k: blocks(sorted(ts), gap, tail) for k, ts in events.items()}
    split = attention_split(spans_by, sorted(asked))
    for key, spans in spans_by.items():
        all_spans += spans
        unmapped = key.startswith("?")
        entries.append({
            "key": None if unmapped else key,
            "folder": key[1:] if unmapped else None,
            "harvest": None if unmapped else projects[key],
            "hours": round(hours(spans), 2),
            "split_hours": round(split.get(key, 0), 2),
            "blocks": [f"{s:%H:%M}-{e:%H:%M}" for s, e in spans],
            "prompts": prompts.get(key, []),
        })
    entries.sort(key=lambda e: -e["hours"])
    total = sum(e["hours"] for e in entries)
    wall = hours(merge(all_spans))
    print(json.dumps({
        "date": a.day,
        "gap_min": a.gap,
        "tail_min": a.tail,
        "total_hours": round(total, 2),
        "wall_clock_hours": round(wall, 2),
        "overlap_hours": round(total - wall, 2),
        "entries": entries,
    }, indent=2))


def _selftest():
    t0 = datetime(2026, 1, 1, 9, 0)
    m = lambda n: t0 + timedelta(minutes=n)
    g, tl = timedelta(minutes=15), timedelta(minutes=5)
    assert blocks([m(0), m(10), m(40)], g, tl) == [(m(0), m(15)), (m(40), m(45))]
    assert merge([(m(0), m(30)), (m(20), m(50)), (m(60), m(70))]) == [[m(0), m(50)], [m(60), m(70)]]
    assert under("/a/b/c", "/a/b") and not under("/a/bc", "/a/b")
    roots = ["/d/projects", "/d"]
    assert repo_folder("/d/projects/x/src", roots) == "/d/projects/x"
    assert repo_folder("/d/y/z", roots) == "/d/y" and repo_folder("/d/projects", roots) == "/d/projects"
    assert repo_folder("/elsewhere/q", roots) == "/elsewhere/q"
    # A 0-60, B 30-90; prompt B at 40 -> A gets 0-40 (40m), B gets 40-90 (50m)
    s = attention_split({"A": [(m(0), m(60))], "B": [(m(30), m(90))]}, [(m(0), "A"), (m(40), "B")])
    assert round(s["A"] * 60) == 40 and round(s["B"] * 60) == 50, s


if __name__ == "__main__":
    _selftest()
    main()
