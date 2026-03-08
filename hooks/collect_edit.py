"""PostToolUse hook for Edit/Write — collect file edit events."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.store import append_event


def _detect_case(name):
    if not name:
        return None
    if "-" in name and name == name.lower():
        return "kebab-case"
    if "_" in name:
        return "snake_case" if name == name.lower() else "SCREAMING_SNAKE" if name == name.upper() else "snake_case"
    if name[0].isupper() and any(c.islower() for c in name):
        return "PascalCase"
    if name[0].islower() and any(c.isupper() for c in name[1:]):
        return "camelCase"
    if name == name.lower():
        return "lowercase"
    return None


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"result": "continue"}))
        return

    cwd = input_data.get("cwd", "")
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})
    session_id = input_data.get("session_id", "")

    file_path = tool_input.get("file_path", "")
    if not file_path:
        print(json.dumps({"result": "continue"}))
        return

    basename = os.path.basename(file_path)
    name, ext = os.path.splitext(basename)
    parent_dir = os.path.dirname(file_path).replace("\\", "/")

    event = {
        "type": "edit",
        "tool": tool_name,
        "file_path": file_path,
        "extension": ext,
        "basename": basename,
        "name_case": _detect_case(name),
        "parent_dir": parent_dir,
        "cwd": cwd,
        "session_id": session_id,
    }

    # Extract content for pattern analysis
    new_content = ""
    if tool_name == "Write":
        new_content = tool_input.get("content", "")
    elif tool_name == "Edit":
        new_content = tool_input.get("new_string", "")

    if new_content:
        # Only store first 2000 chars to keep events file manageable
        event["new_content"] = new_content[:2000]

    append_event(event)
    print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
