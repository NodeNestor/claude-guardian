"""Stop hook — run analyzers on collected events, update patterns, generate rules."""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.store import get_state, save_state, get_events_for_project, get_patterns, save_patterns
from server.analyzers import run_all_analyzers
from server.rule_generator import generate_rules


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"result": "continue"}))
        return

    cwd = input_data.get("cwd", os.getcwd())
    state = get_state()
    phase = state.get("phase", "OBSERVE")

    last_ts = state.get("last_analysis_ts", 0)

    # Get events for this project since last analysis
    events = get_events_for_project(cwd, since_ts=last_ts)
    if not events:
        print(json.dumps({"result": "continue"}))
        return

    # Run all analyzers
    new_patterns = run_all_analyzers(events)

    # Merge with existing patterns
    existing = get_patterns()
    existing_patterns = existing.get("patterns", [])

    # Build lookup of existing patterns by name
    pattern_map = {p["pattern_name"]: p for p in existing_patterns}

    # Update with new patterns (keep the one with higher sample_size)
    for p in new_patterns:
        name = p["pattern_name"]
        if name in pattern_map:
            old = pattern_map[name]
            # Merge: accumulate sample sizes
            p["sample_size"] = old.get("sample_size", 0) + p.get("sample_size", 0)
            p["frequency"] = old.get("frequency", 0) + p.get("frequency", 0)
            if p["sample_size"] > 0:
                p["confidence"] = round(p["frequency"] / p["sample_size"], 3)
        pattern_map[name] = p

    merged = list(pattern_map.values())
    save_patterns({"patterns": merged, "updated_at": time.time()})

    # Generate rules if in SUGGEST or ENFORCE phase
    if phase in ("SUGGEST", "ENFORCE"):
        generate_rules(merged, cwd)

    # Update state
    state["last_analysis_ts"] = time.time()
    state["last_analysis_event_count"] = len(events)
    save_state(state)

    print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
