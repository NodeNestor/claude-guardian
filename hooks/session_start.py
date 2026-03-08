"""SessionStart hook — increment session count, determine phase, cold-start if needed."""

import json
import os
import sys
import time

# Add parent dir to path so we can import server modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.store import get_state, save_state, get_patterns, count_events
from server.analyzers import cold_start_scan, run_all_analyzers
from server.store import save_patterns, append_event


def determine_phase(session_count):
    if session_count <= 5:
        return "OBSERVE"
    elif session_count <= 10:
        return "SUGGEST"
    else:
        return "ENFORCE"


def main():
    input_data = json.loads(sys.stdin.read())
    cwd = input_data.get("cwd", os.getcwd())
    session_id = input_data.get("session_id", "unknown")

    state = get_state()

    # Track per-project session counts
    project_sessions = state.get("project_sessions", {})
    proj_count = project_sessions.get(cwd, 0) + 1
    project_sessions[cwd] = proj_count

    state["session_count"] = state.get("session_count", 0) + 1
    state["project_sessions"] = project_sessions
    state["phase"] = determine_phase(proj_count)
    state["current_project"] = cwd
    state["current_session"] = session_id
    save_state(state)

    # Cold-start scan on first session for this project
    if proj_count == 1:
        events = cold_start_scan(cwd, max_files=500)
        for ev in events:
            append_event(ev)

        if events:
            patterns = run_all_analyzers(events)
            if patterns:
                save_patterns({"patterns": patterns, "updated_at": time.time()})

    # Build status message
    patterns_data = get_patterns()
    pattern_count = len(patterns_data.get("patterns", []))
    event_count = count_events()

    phase = state["phase"]
    phase_emoji = {"OBSERVE": "[OBSERVE]", "SUGGEST": "[SUGGEST]", "ENFORCE": "[ENFORCE]"}
    phase_label = phase_emoji.get(phase, phase)

    msg = (
        f"Guardian {phase_label} | "
        f"Project session #{proj_count} | "
        f"{event_count} events tracked | "
        f"{pattern_count} patterns learned"
    )

    if phase == "OBSERVE":
        remaining = 6 - proj_count
        msg += f" | {remaining} sessions until SUGGEST phase"
    elif phase == "SUGGEST":
        remaining = 11 - proj_count
        msg += f" | {remaining} sessions until ENFORCE phase"

    print(json.dumps({"result": "continue", "hookSpecificOutput": {"additionalContext": msg}}))


if __name__ == "__main__":
    main()
