#!/bin/bash
echo "=== Security Scan for FlightTrak Repository ==="
echo ""
echo "Checking for exposed credentials in git..."
echo ""

# Check if config.json is tracked
echo "1. Checking if config.json is tracked:"
if git ls-files | grep -q "config.json"; then
    echo "   ❌ WARNING: config.json IS tracked in git!"
else
    echo "   ✅ SAFE: config.json is NOT tracked"
fi

# Check for actual credential strings in tracked files
echo ""
echo "2. Scanning for credential patterns in tracked files:"
DANGEROUS_PATTERNS=(
    "sk-ant-api"
    "mhte admi"
    "KyjyKndK"
    "sgTib5YJ"
    "AAAAAAAAAAAAAAAAAAAAAIa9wQEA"
)

FOUND=0
for pattern in "${DANGEROUS_PATTERNS[@]}"; do
    if git grep -q "$pattern" HEAD 2>/dev/null; then
        echo "   ❌ FOUND: $pattern in tracked files!"
        FOUND=1
    fi
done

if [ $FOUND -eq 0 ]; then
    echo "   ✅ SAFE: No credential patterns found in tracked files"
fi

# Check what's in config.json locally vs gitignore
echo ""
echo "3. Verifying .gitignore protection:"
if grep -q "config.json" .gitignore; then
    echo "   ✅ SAFE: config.json is in .gitignore"
else
    echo "   ❌ WARNING: config.json NOT in .gitignore!"
fi

echo ""
echo "4. Files that ARE tracked and contain 'config':"
git ls-files | grep -i config

echo ""
echo "=== Scan Complete ==="
