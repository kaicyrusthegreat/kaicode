#!/usr/bin/env bash
# scripts/repository_audit.sh
# KAI CODE — RELEASE GATE AUDIT SCRIPT
# This script enforces the Public Release Policy. It fails if any violations are found.

set -e

echo "======================================"
echo "KAI CODE REPOSITORY AUDIT - RELEASE GATE"
echo "======================================"
echo ""

VIOLATIONS=0

echo "[1/4] Checking for secrets using gitleaks..."
if command -v gitleaks >/dev/null 2>&1; then
    if gitleaks detect --source . -v; then
        echo "✅ No secrets detected."
    else
        echo "❌ SECRETS DETECTED! Run 'gitleaks detect -v' for details."
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
else
    echo "⚠️  gitleaks not installed. Please install gitleaks to run secret scanning."
    VIOLATIONS=$((VIOLATIONS + 1))
fi

echo ""
echo "[2/4] Checking for forbidden file extensions and directories..."
FORBIDDEN=(
    "*.db"
    "*.sqlite"
    "*.sqlite3"
    "*.log"
    ".env*"
    "sessions"
    "workspace_state"
    "memory_store"
    "secrets"
    "credentials"
    "tokens"
    "chat_history"
    "build"
    "dist"
)

# Use git ls-files to only check tracked files (ignoring safe local files)
TRACKED_FILES=$(git ls-files)

for pattern in "${FORBIDDEN[@]}"; do
    # Using glob matching on tracked files
    MATCHES=$(echo "$TRACKED_FILES" | grep -E "(/|^)${pattern}(/|$)" || true)
    if [ ! -z "$MATCHES" ]; then
        echo "❌ FORBIDDEN FILES TRACKED IN GIT ($pattern):"
        echo "$MATCHES"
        VIOLATIONS=$((VIOLATIONS + 1))
    fi
done

if [ $VIOLATIONS -eq 0 ]; then
    echo "✅ No forbidden extensions or directories tracked."
fi

echo ""
echo "[3/4] Checking for large files (>50MB)..."
# Check tracked files for size exceeding 50MB
LARGE_FILES=$(git ls-files | xargs -I {} find {} -type f -size +50M 2>/dev/null || true)
if [ ! -z "$LARGE_FILES" ]; then
    echo "❌ LARGE FILES DETECTED (>50MB):"
    echo "$LARGE_FILES"
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No large files detected."
fi

echo ""
echo "[4/4] Checking for internal business/research documents..."
# Simple keyword heuristic on tracked markdown files
PRIVATE_DOCS=$(git ls-files "*.md" | grep -E -i "(revenue|business_plan|internal_roadmap|antigravity-logs|proprietary)" || true)
if [ ! -z "$PRIVATE_DOCS" ]; then
    echo "❌ POTENTIAL INTERNAL DOCUMENTS DETECTED:"
    echo "$PRIVATE_DOCS"
    echo "Please review manually."
    VIOLATIONS=$((VIOLATIONS + 1))
else
    echo "✅ No obvious internal documents detected."
fi

echo ""
echo "======================================"
if [ $VIOLATIONS -eq 0 ]; then
    echo "🎉 AUDIT PASSED! The repository is clean for release."
    exit 0
else
    echo "💥 AUDIT FAILED with $VIOLATIONS category violation(s)."
    echo "Please resolve these issues before pushing or releasing."
    exit 1
fi
