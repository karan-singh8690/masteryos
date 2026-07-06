#!/bin/bash
# Test all admin pages for errors

BASE="https://masteryos-production.up.railway.app"

ADMIN_PAGES=(
  "/admin/dashboard"
  "/admin/users"
  "/admin/organizations"
  "/admin/rbac"
  "/admin/feature-flags"
  "/admin/workers"
  "/admin/outbox"
  "/admin/dead-letters"
  "/admin/scheduler"
  "/admin/notifications"
  "/admin/email"
  "/admin/audit"
  "/admin/security"
  "/admin/analytics"
  "/admin/billing"
  "/admin/system-config"
  "/admin/search"
  "/admin/invites"
  "/admin/beta-ops"
  "/admin/beta-ops/funnel"
  "/admin/beta-ops/learning"
  "/admin/beta-ops/feedback"
  "/admin/beta-ops/success"
  "/admin/beta-ops/instructor"
  "/admin/beta-ops/operations"
  "/admin/beta-ops/releases"
  "/admin/beta-ops/reports"
  "/admin/beta-ops/experiments"
)

echo "=== Testing Admin Pages ==="
for page in "${ADMIN_PAGES[@]}"; do
  echo -n "  $page: "
  agent-browser open "$BASE$page" >/dev/null 2>&1
  agent-browser wait 1500 >/dev/null 2>&1
  URL=$(agent-browser get url 2>&1)
  ERRORS=$(agent-browser errors 2>&1 | head -3)
  if [[ "$URL" == "$BASE$page" ]] && [[ -z "$ERRORS" ]]; then
    echo "✅ OK"
  elif [[ "$URL" != "$BASE$page" ]]; then
    echo "⚠️  Redirected to: $URL"
  else
    echo "❌ Errors: $ERRORS"
  fi
done

echo ""
echo "=== Testing Learner Pages ==="
LEARNER_PAGES=(
  "/dashboard"
  "/subjects"
  "/study/start"
  "/reviews"
  "/recommendations"
  "/achievements"
  "/profile"
  "/settings"
  "/settings/security"
  "/notifications"
  "/mastery"
  "/search"
  "/welcome"
)

for page in "${LEARNER_PAGES[@]}"; do
  echo -n "  $page: "
  agent-browser open "$BASE$page" >/dev/null 2>&1
  agent-browser wait 1500 >/dev/null 2>&1
  URL=$(agent-browser get url 2>&1)
  ERRORS=$(agent-browser errors 2>&1 | head -3)
  if [[ "$URL" == "$BASE$page" ]] && [[ -z "$ERRORS" ]]; then
    echo "✅ OK"
  elif [[ "$URL" != "$BASE$page" ]]; then
    echo "⚠️  Redirected to: $URL"
  else
    echo "❌ Errors: $ERRORS"
  fi
done

echo ""
echo "=== Testing Public Pages ==="
PUBLIC_PAGES=(
  "/"
  "/login"
  "/register"
  "/features"
  "/pricing"
  "/security"
  "/docs"
  "/status"
  "/about"
  "/contact"
  "/support"
)

for page in "${PUBLIC_PAGES[@]}"; do
  echo -n "  $page: "
  agent-browser open "$BASE$page" >/dev/null 2>&1
  agent-browser wait 1500 >/dev/null 2>&1
  URL=$(agent-browser get url 2>&1)
  ERRORS=$(agent-browser errors 2>&1 | head -3)
  if [[ -z "$ERRORS" ]]; then
    echo "✅ OK"
  else
    echo "❌ Errors: $ERRORS"
  fi
done
