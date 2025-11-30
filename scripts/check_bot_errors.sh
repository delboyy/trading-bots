#!/bin/bash
# Quick script to check why bots are crashing

echo "🔍 Checking bot error logs..."
echo ""

# Check the most recent errors in each bot's log
for log in logs/*_error.log; do
    if [ -f "$log" ]; then
        bot_name=$(basename "$log" _error.log)
        last_error=$(tail -1 "$log" 2>/dev/null)
        if [ ! -z "$last_error" ]; then
            echo "❌ $bot_name:"
            echo "   $last_error"
            echo ""
        fi
    fi
done

echo ""
echo "🔍 Checking for timestamp errors..."
grep -h "extra text" logs/*_error.log 2>/dev/null | head -5

echo ""
echo "💡 If you see timestamp errors above, you need to:"
echo "   git pull"
echo "   (This will fix the timestamp format issues)"
