"""PostToolUse hook for Bash — collect command events."""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.store import append_event

# Patterns to detect
TEST_CMDS = re.compile(r"\b(pytest|jest|vitest|mocha|cargo test|go test|npm test|yarn test|pnpm test|bun test)\b")
BUILD_CMDS = re.compile(r"\b(npm run build|yarn build|pnpm build|cargo build|go build|make|gradle|mvn)\b")
PKG_MANAGERS = re.compile(r"\b(npm|yarn|pnpm|bun|pip|poetry|cargo|go mod)\b")
LINT_CMDS = re.compile(r"\b(eslint|prettier|black|ruff|flake8|mypy|pylint|clippy|golint)\b")


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"result": "continue"}))
        return

    cwd = input_data.get("cwd", "")
    tool_input = input_data.get("tool_input", {})
    session_id = input_data.get("session_id", "")

    command = tool_input.get("command", "")
    if not command:
        print(json.dumps({"result": "continue"}))
        return

    event = {
        "type": "bash",
        "command": command[:500],  # Truncate long commands
        "cwd": cwd,
        "session_id": session_id,
    }

    # Classify command
    tags = []
    if TEST_CMDS.search(command):
        tags.append("test")
        m = TEST_CMDS.search(command)
        event["test_runner"] = m.group(1)

    if BUILD_CMDS.search(command):
        tags.append("build")

    if PKG_MANAGERS.search(command):
        m = PKG_MANAGERS.search(command)
        event["pkg_manager"] = m.group(1)

    if LINT_CMDS.search(command):
        tags.append("lint")
        m = LINT_CMDS.search(command)
        event["linter"] = m.group(1)

    event["tags"] = tags

    append_event(event)
    print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
