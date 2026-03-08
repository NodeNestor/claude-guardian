"""Event store — JSONL file + JSON state/patterns storage."""

import json
import os
import time

GUARDIAN_DIR = os.path.join(os.path.expanduser("~"), ".claude", "guardian")
EVENTS_FILE = os.path.join(GUARDIAN_DIR, "events.jsonl")
STATE_FILE = os.path.join(GUARDIAN_DIR, "state.json")
PATTERNS_FILE = os.path.join(GUARDIAN_DIR, "patterns.json")

DEFAULT_STATE = {
    "session_count": 0,
    "phase": "OBSERVE",
    "last_analysis_ts": 0,
    "last_analysis_event_count": 0,
    "project_sessions": {},
}

def _ensure_dir():
    os.makedirs(GUARDIAN_DIR, exist_ok=True)

def append_event(event):
    """Append a single event dict to events.jsonl."""
    _ensure_dir()
    event.setdefault("ts", time.time())
    line = json.dumps(event, separators=(",", ":")) + "\n"
    with open(EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(line)

def get_events(limit=0, since_ts=0):
    """Read events from JSONL. If limit>0, return last N. If since_ts>0, filter."""
    _ensure_dir()
    if not os.path.exists(EVENTS_FILE):
        return []
    events = []
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                if since_ts and ev.get("ts", 0) < since_ts:
                    continue
                events.append(ev)
            except json.JSONDecodeError:
                continue
    if limit > 0:
        events = events[-limit:]
    return events

def get_events_for_project(cwd, limit=0, since_ts=0):
    """Get events filtered by project working directory."""
    events = get_events(limit=0, since_ts=since_ts)
    filtered = [e for e in events if e.get("cwd", "").startswith(cwd)]
    if limit > 0:
        filtered = filtered[-limit:]
    return filtered

def get_state():
    """Load state.json, return default if missing."""
    _ensure_dir()
    if not os.path.exists(STATE_FILE):
        return dict(DEFAULT_STATE)
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_STATE)

def save_state(state):
    """Save state.json atomically."""
    _ensure_dir()
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

def get_patterns():
    """Load patterns.json."""
    _ensure_dir()
    if not os.path.exists(PATTERNS_FILE):
        return {}
    try:
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}

def save_patterns(patterns):
    """Save patterns.json atomically."""
    _ensure_dir()
    tmp = PATTERNS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(patterns, f, indent=2)
    os.replace(tmp, PATTERNS_FILE)

def count_events():
    """Count total events without loading all into memory."""
    if not os.path.exists(EVENTS_FILE):
        return 0
    count = 0
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count
