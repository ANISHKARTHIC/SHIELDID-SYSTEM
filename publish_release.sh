#!/bin/bash
# Builds the release APK and uploads it to the backend as the new "latest"
# app release (backend/api/release_router.py), so the Connection settings
# screen's "Update Now" button starts offering it immediately.
#
# Usage:
#   ./publish_release.sh                          # prompts for admin login
#   VENUEPASS_ADMIN_EMAIL=admin@venuepass.local \
#   VENUEPASS_ADMIN_PASSWORD=secret \
#   ./publish_release.sh "Fixed licence scan parsing"
#
# Requires a super_admin account — publishing is admin-only
# (backend/api/release_router.py's require_super_admin).
set -euo pipefail
cd "$(dirname "$0")"

API_BASE_URL="${VENUEPASS_API_BASE_URL:-https://venuepass-api.duckdns.org/api/v1}"
RELEASE_NOTES="${1:-}"

VERSION=$(grep '^version:' flutter_app/pubspec.yaml | awk '{print $2}' | cut -d'+' -f1)
if [ -z "$VERSION" ]; then
    echo "Could not read version from flutter_app/pubspec.yaml" >&2
    exit 1
fi

echo "Publishing VenuePass v$VERSION to $API_BASE_URL"
echo

# --- 1. Build the release APK (arm64 — what nearly every real device
#         needs; see android/app/build.gradle.kts for the per-ABI split) ---
echo "==> Building release APK..."
cd flutter_app
flutter build apk --release --target-platform android-arm64
cd ..

APK_PATH="flutter_app/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk"
if [ ! -f "$APK_PATH" ]; then
    echo "Build did not produce $APK_PATH" >&2
    exit 1
fi
APK_SIZE=$(du -h "$APK_PATH" | cut -f1)
echo "Built $APK_PATH ($APK_SIZE)"
echo

# --- 2. Authenticate as a super_admin ---
if [ -z "${VENUEPASS_ADMIN_EMAIL:-}" ]; then
    read -rp "Admin email: " VENUEPASS_ADMIN_EMAIL
fi
if [ -z "${VENUEPASS_ADMIN_PASSWORD:-}" ]; then
    read -rsp "Admin password: " VENUEPASS_ADMIN_PASSWORD
    echo
fi

echo "==> Logging in as $VENUEPASS_ADMIN_EMAIL..."
LOGIN_RESPONSE=$(curl -sS -X POST "$API_BASE_URL/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"username\": \"$VENUEPASS_ADMIN_EMAIL\", \"password\": \"$VENUEPASS_ADMIN_PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('token', ''))" 2>/dev/null || true)
if [ -z "$TOKEN" ]; then
    echo "Login failed: $LOGIN_RESPONSE" >&2
    exit 1
fi
echo "Logged in."
echo

# --- 3. Upload the APK as the new release ---
echo "==> Uploading v$VERSION..."
UPLOAD_RESPONSE=$(curl -sS -X POST "$API_BASE_URL/releases" \
    -H "Authorization: Bearer $TOKEN" \
    -F "version=$VERSION" \
    -F "release_notes=$RELEASE_NOTES" \
    -F "apk=@$APK_PATH;type=application/vnd.android.package-archive")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"

IS_LATEST=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('is_latest', False))" 2>/dev/null || echo "False")
if [ "$IS_LATEST" = "True" ]; then
    echo
    echo "v$VERSION is now published and live at $API_BASE_URL/releases/latest"
else
    echo
    echo "Upload did not succeed — see response above." >&2
    exit 1
fi
