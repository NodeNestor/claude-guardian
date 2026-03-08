#!/bin/bash
# claude-guardian installer — pure stdlib, no venv needed

set -e

GUARDIAN_DIR="$HOME/.claude/guardian"

echo "Installing claude-guardian..."
echo ""

# Create data directory
mkdir -p "$GUARDIAN_DIR"

# Initialize state if not exists
if [ ! -f "$GUARDIAN_DIR/state.json" ]; then
    echo '{"session_count": 0, "phase": "OBSERVE", "last_analysis_ts": 0, "project_sessions": {}}' > "$GUARDIAN_DIR/state.json"
    echo "  Created $GUARDIAN_DIR/state.json"
fi

# Make hook runner executable
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
chmod +x "$SCRIPT_DIR/hooks/run_hook.sh"
echo "  Made hooks/run_hook.sh executable"

echo ""
echo "Done! claude-guardian is ready."
echo ""
echo "Phases:"
echo "  Sessions 1-5:   OBSERVE  — learns your patterns silently"
echo "  Sessions 6-10:  SUGGEST  — warns about violations"
echo "  Sessions 11+:   ENFORCE  — blocks violations"
echo ""
echo "Data stored at: $GUARDIAN_DIR/"
echo "Add a .guardianignore file to skip enforcement on specific files."
