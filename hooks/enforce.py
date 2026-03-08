"""PreToolUse hook for Edit/Write — enforce learned patterns."""

import fnmatch
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.store import get_state, get_patterns


def _load_guardianignore(cwd):
    """Load .guardianignore patterns from project root."""
    ignore_file = os.path.join(cwd, ".guardianignore")
    if not os.path.exists(ignore_file):
        return []
    try:
        with open(ignore_file, "r", encoding="utf-8") as f:
            patterns = []
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
            return patterns
    except OSError:
        return []


def _is_ignored(file_path, cwd, ignore_patterns):
    """Check if file matches any .guardianignore pattern."""
    # Get relative path
    rel = os.path.relpath(file_path, cwd).replace("\\", "/")
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(rel, pattern):
            return True
        if fnmatch.fnmatch(os.path.basename(file_path), pattern):
            return True
    return False


def _detect_case(name):
    if not name:
        return None
    if "-" in name and name == name.lower():
        return "kebab-case"
    if "_" in name:
        return "snake_case" if name == name.lower() else "snake_case"
    if name[0].isupper() and any(c.islower() for c in name):
        return "PascalCase"
    if name[0].islower() and any(c.isupper() for c in name[1:]):
        return "camelCase"
    if name == name.lower():
        return "lowercase"
    return None


def _check_naming(file_path, patterns_list):
    """Check if file naming matches learned conventions."""
    basename = os.path.basename(file_path)
    name, ext = os.path.splitext(basename)
    if not ext or name.startswith("."):
        return []

    file_case = _detect_case(name)
    if not file_case:
        return []

    parent = os.path.dirname(file_path).replace("\\", "/")
    parts = [p for p in parent.split("/") if p and p not in (".", "..")]
    dir_key = "/".join(parts[-2:]) if len(parts) >= 2 else parts[-1] if parts else "root"

    violations = []
    for p in patterns_list:
        pname = p.get("pattern_name", "")
        if not pname.startswith("naming:"):
            continue
        p_dir = p.get("dir_key", "")
        if p_dir and p_dir in dir_key:
            expected = p["dominant_value"]
            if file_case != expected:
                violations.append(
                    f"Naming: expected {expected} in {p_dir}/, "
                    f"got {file_case} ({basename}). "
                    f"Convention: {p['frequency']}/{p['sample_size']} files."
                )
    return violations


def _check_imports(file_path, content, patterns_list):
    """Check if imports match learned style."""
    if not content:
        return []

    ext = os.path.splitext(file_path)[1].lower()
    violations = []

    for p in patterns_list:
        pname = p.get("pattern_name", "")

        if pname == "import:export_style" and ext in (".js", ".jsx", ".ts", ".tsx"):
            expected = p["dominant_value"]
            has_default = "export default" in content
            has_named = bool(re.search(r"export\s+(?:const|function|class)\s", content))
            if expected == "named" and has_default and not has_named:
                violations.append(
                    f"Export style: project uses named exports, "
                    f"but this file uses default export. "
                    f"Convention: {p['frequency']}/{p['sample_size']} files."
                )
            elif expected == "default" and has_named and not has_default:
                violations.append(
                    f"Export style: project uses default exports, "
                    f"but this file uses named exports. "
                    f"Convention: {p['frequency']}/{p['sample_size']} files."
                )

    return violations


def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, ValueError):
        print(json.dumps({"result": "continue"}))
        return

    cwd = input_data.get("cwd", "")
    tool_input = input_data.get("tool_input", {})

    state = get_state()
    phase = state.get("phase", "OBSERVE")

    # In OBSERVE phase, always allow
    if phase == "OBSERVE":
        print(json.dumps({"result": "continue"}))
        return

    file_path = tool_input.get("file_path", "")
    if not file_path:
        print(json.dumps({"result": "continue"}))
        return

    # Check .guardianignore
    ignore_patterns = _load_guardianignore(cwd)
    if _is_ignored(file_path, cwd, ignore_patterns):
        print(json.dumps({"result": "continue"}))
        return

    # Load patterns
    patterns_data = get_patterns()
    patterns_list = patterns_data.get("patterns", [])

    # Only check high-confidence patterns
    strong_patterns = [
        p for p in patterns_list
        if p.get("confidence", 0) >= 0.85 and p.get("sample_size", 0) >= 15
    ]

    if not strong_patterns:
        print(json.dumps({"result": "continue"}))
        return

    # Collect violations
    violations = []
    violations.extend(_check_naming(file_path, strong_patterns))

    # Get content for import checks
    content = ""
    tool_name = input_data.get("tool_name", "")
    if tool_name == "Write":
        content = tool_input.get("content", "")
    elif tool_name == "Edit":
        content = tool_input.get("new_string", "")

    violations.extend(_check_imports(file_path, content, strong_patterns))

    if not violations:
        print(json.dumps({"result": "continue"}))
        return

    warning_msg = "Guardian: " + " | ".join(violations)

    if phase == "SUGGEST":
        # Warn but allow
        print(json.dumps({
            "result": "continue",
            "hookSpecificOutput": {
                "additionalContext": warning_msg
            }
        }))
    elif phase == "ENFORCE":
        # Block
        print(json.dumps({
            "result": "continue",
            "hookSpecificOutput": {
                "permissionDecision": "deny",
                "reason": warning_msg + " (Add to .guardianignore to bypass)"
            }
        }))
    else:
        print(json.dumps({"result": "continue"}))


if __name__ == "__main__":
    main()
