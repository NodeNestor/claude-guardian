"""Pattern detection — frequency counting + string matching + regex. No ML, no deps."""

import os
import re
from collections import Counter, defaultdict

# ── Naming detection ──

def _detect_case(name):
    """Detect naming convention of a file/dir name (without extension)."""
    if not name:
        return None
    if "-" in name:
        if name == name.lower():
            return "kebab-case"
        return None
    if "_" in name:
        if name == name.lower():
            return "snake_case"
        if name == name.upper():
            return "SCREAMING_SNAKE"
        return "snake_case"
    if name[0].isupper():
        if any(c.islower() for c in name):
            return "PascalCase"
        return "UPPERCASE"
    if name[0].islower() and any(c.isupper() for c in name[1:]):
        return "camelCase"
    if name == name.lower():
        return "lowercase"
    return None

def naming_analyzer(events):
    """Detect file naming conventions per directory prefix."""
    dir_cases = defaultdict(Counter)
    seen_files = set()

    for ev in events:
        fp = ev.get("file_path", "")
        if not fp or fp in seen_files:
            continue
        seen_files.add(fp)

        basename = os.path.basename(fp)
        name, ext = os.path.splitext(basename)
        if not ext or name.startswith("."):
            continue

        # Group by parent dir relative pattern
        parent = os.path.dirname(fp)
        # Normalize to forward slashes and get last 2 segments
        parent = parent.replace("\\", "/")
        parts = parent.split("/")
        # Use last 2 meaningful dir segments as key
        key_parts = [p for p in parts if p and p not in (".", "..")][-2:]
        dir_key = "/".join(key_parts) if key_parts else "root"

        case = _detect_case(name)
        if case:
            dir_cases[dir_key][case] += 1

    results = []
    for dir_key, counter in dir_cases.items():
        total = sum(counter.values())
        if total < 3:
            continue
        dominant, count = counter.most_common(1)[0]
        confidence = count / total
        results.append({
            "pattern_name": f"naming:{dir_key}",
            "dominant_value": dominant,
            "frequency": count,
            "sample_size": total,
            "confidence": round(confidence, 3),
            "dir_key": dir_key,
        })
    return results


def structure_analyzer(events):
    """Detect where different file types live."""
    ext_dirs = defaultdict(Counter)
    seen = set()

    for ev in events:
        fp = ev.get("file_path", "")
        if not fp or fp in seen:
            continue
        seen.add(fp)

        basename = os.path.basename(fp)
        _, ext = os.path.splitext(basename)
        if not ext:
            continue

        parent = os.path.dirname(fp).replace("\\", "/")
        parts = parent.split("/")
        # Find structural markers
        for part in parts:
            low = part.lower()
            if low in ("src", "lib", "app", "pages", "components", "hooks",
                        "utils", "helpers", "services", "api", "models",
                        "types", "interfaces", "constants", "config",
                        "tests", "__tests__", "test", "spec", "__pycache__"):
                ext_dirs[ext][low] += 1

    # Detect test location patterns
    test_patterns = Counter()
    for ev in events:
        fp = ev.get("file_path", "").replace("\\", "/")
        if not fp:
            continue
        if "test" in fp.lower() or "spec" in fp.lower():
            if "__tests__" in fp:
                test_patterns["__tests__/"] += 1
            elif "/test/" in fp or "/tests/" in fp:
                test_patterns["test_dir"] += 1
            elif ".test." in fp or ".spec." in fp:
                test_patterns["colocated"] += 1

    results = []
    for ext, counter in ext_dirs.items():
        total = sum(counter.values())
        if total < 3:
            continue
        dominant, count = counter.most_common(1)[0]
        confidence = count / total
        results.append({
            "pattern_name": f"structure:{ext}",
            "dominant_value": dominant,
            "frequency": count,
            "sample_size": total,
            "confidence": round(confidence, 3),
        })

    if test_patterns:
        total = sum(test_patterns.values())
        dominant, count = test_patterns.most_common(1)[0]
        if total >= 3:
            results.append({
                "pattern_name": "structure:tests",
                "dominant_value": dominant,
                "frequency": count,
                "sample_size": total,
                "confidence": round(count / total, 3),
            })

    return results


# ── Import patterns ──

_JS_IMPORT_RE = re.compile(
    r'''(?:import\s+(?:(?:type\s+)?(?:\{[^}]*\}|[\w*]+(?:\s*,\s*\{[^}]*\})?)\s+from\s+)?['"]([^'"]+)['"])'''
)
_PY_IMPORT_RE = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)

def _classify_js_import(path):
    if path.startswith("."):
        return "relative"
    if path.startswith("@/") or path.startswith("~/"):
        return "alias"
    return "package"

def import_analyzer(events):
    """Detect import style patterns from code content."""
    js_import_types = Counter()
    py_import_types = Counter()
    export_styles = Counter()
    seen = set()

    for ev in events:
        fp = ev.get("file_path", "")
        content = ev.get("new_content", "") or ev.get("content", "")
        if not content or not fp:
            continue

        key = fp + ":" + str(ev.get("ts", ""))
        if key in seen:
            continue
        seen.add(key)

        ext = os.path.splitext(fp)[1].lower()

        if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs"):
            for m in _JS_IMPORT_RE.finditer(content):
                js_import_types[_classify_js_import(m.group(1))] += 1

            # Export style
            if "export default" in content:
                export_styles["default"] += 1
            if re.search(r"export\s+(?:const|function|class|type|interface)\s", content):
                export_styles["named"] += 1

        elif ext == ".py":
            for m in _PY_IMPORT_RE.finditer(content):
                mod = m.group(1) or m.group(2)
                if mod and mod.startswith("."):
                    py_import_types["relative"] += 1
                else:
                    py_import_types["absolute"] += 1

    results = []

    if js_import_types:
        total = sum(js_import_types.values())
        if total >= 5:
            dominant, count = js_import_types.most_common(1)[0]
            results.append({
                "pattern_name": "import:js_style",
                "dominant_value": dominant,
                "frequency": count,
                "sample_size": total,
                "confidence": round(count / total, 3),
            })

    if py_import_types:
        total = sum(py_import_types.values())
        if total >= 5:
            dominant, count = py_import_types.most_common(1)[0]
            results.append({
                "pattern_name": "import:py_style",
                "dominant_value": dominant,
                "frequency": count,
                "sample_size": total,
                "confidence": round(count / total, 3),
            })

    if export_styles:
        total = sum(export_styles.values())
        if total >= 5:
            dominant, count = export_styles.most_common(1)[0]
            results.append({
                "pattern_name": "import:export_style",
                "dominant_value": dominant,
                "frequency": count,
                "sample_size": total,
                "confidence": round(count / total, 3),
            })

    return results


# ── Code pattern detection ──

def pattern_analyzer(events):
    """Detect common code patterns — error handling, etc."""
    error_styles = Counter()
    seen = set()

    for ev in events:
        fp = ev.get("file_path", "")
        content = ev.get("new_content", "") or ev.get("content", "")
        if not content or not fp:
            continue

        key = fp + ":" + str(ev.get("ts", ""))
        if key in seen:
            continue
        seen.add(key)

        ext = os.path.splitext(fp)[1].lower()

        if ext in (".js", ".jsx", ".ts", ".tsx"):
            if "try {" in content or "try{" in content:
                error_styles["try-catch"] += 1
            if ".catch(" in content:
                error_styles[".catch()"] += 1
            if "Result<" in content or "Result[" in content:
                error_styles["Result"] += 1

        elif ext == ".py":
            if "try:" in content:
                error_styles["try-except"] += 1
            if "raise " in content:
                error_styles["raise"] += 1

    results = []
    if error_styles:
        total = sum(error_styles.values())
        if total >= 5:
            dominant, count = error_styles.most_common(1)[0]
            results.append({
                "pattern_name": "pattern:error_handling",
                "dominant_value": dominant,
                "frequency": count,
                "sample_size": total,
                "confidence": round(count / total, 3),
            })

    return results


def run_all_analyzers(events):
    """Run all analyzers and return combined results."""
    results = []
    results.extend(naming_analyzer(events))
    results.extend(structure_analyzer(events))
    results.extend(import_analyzer(events))
    results.extend(pattern_analyzer(events))
    return results


def cold_start_scan(project_root, max_files=500):
    """Walk project tree and extract features from existing files to bootstrap patterns."""
    events = []
    count = 0

    skip_dirs = {
        ".git", "node_modules", "__pycache__", ".next", ".nuxt",
        "dist", "build", ".venv", "venv", ".tox", ".mypy_cache",
        ".pytest_cache", "coverage", ".claude", ".guardian",
    }

    code_exts = {
        ".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".mts",
        ".vue", ".svelte", ".go", ".rs", ".java", ".kt",
        ".rb", ".php", ".css", ".scss", ".less", ".html",
    }

    for dirpath, dirnames, filenames in os.walk(project_root):
        # Prune skip dirs
        dirnames[:] = [d for d in dirnames if d not in skip_dirs and not d.startswith(".")]

        for fname in filenames:
            if count >= max_files:
                return events

            _, ext = os.path.splitext(fname)
            if ext.lower() not in code_exts:
                continue

            full_path = os.path.join(dirpath, fname)
            ev = {
                "type": "cold_start",
                "file_path": full_path,
                "cwd": project_root,
                "ts": 0,
            }

            # Try to read first 200 lines for import/pattern analysis
            try:
                with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= 200:
                            break
                        lines.append(line)
                    content = "".join(lines)
                    if content:
                        ev["content"] = content
            except OSError:
                pass

            events.append(ev)
            count += 1

    return events
