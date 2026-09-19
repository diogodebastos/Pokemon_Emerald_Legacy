#!/usr/bin/env bash
# Copy the built ROM to a 3DS running ftpd (over FTP) and verify the size landed intact.
#
# Usage: deploy-to-3ds.sh [HOST[:PORT]] [LOCAL_ROM] [REMOTE_NAME]
#   HOST[:PORT]  3DS ftpd address, e.g. 192.168.1.166:5000
#                (optional if a previous run cached one — see below)
#   LOCAL_ROM    local ROM to send   (default: ./pokeemerald.gba)
#   REMOTE_NAME  filename on the 3DS (default: same basename as LOCAL_ROM)
#
# ftpd's address changes whenever it restarts (new IP/port shown on the 3DS
# screen), so it can't be pinned in an ssh-config-style alias. Instead, the
# last address that worked is cached in .last_target next to this script —
# omit HOST[:PORT] on a later run to reuse it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CACHE_FILE="$SCRIPT_DIR/.last_target"
REMOTE_DIR="${FTP_REMOTE_DIR:-/GBA}"

TARGET="${1:-}"
if [[ -z "$TARGET" ]]; then
  if [[ -f "$CACHE_FILE" ]]; then
    TARGET="$(cat "$CACHE_FILE")"
    echo "==> No address given, reusing last known 3DS address: $TARGET"
  else
    echo "error: no 3DS address given and none cached yet." >&2
    echo "       Usage: deploy-to-3ds.sh HOST:PORT [LOCAL_ROM] [REMOTE_NAME]" >&2
    echo "       (find HOST:PORT on the ftpd screen on your 3DS)" >&2
    exit 1
  fi
else
  shift
fi

LOCAL_ROM="${1:-./pokeemerald.gba}"
REMOTE_NAME="${2:-$(basename "$LOCAL_ROM")}"

if [[ ! -f "$LOCAL_ROM" ]]; then
  echo "error: local ROM not found: $LOCAL_ROM" >&2
  echo "       build it first (make) so pokeemerald.gba exists." >&2
  exit 1
fi

FTP_URL="ftp://$TARGET$REMOTE_DIR/$REMOTE_NAME"
LOCAL_SIZE=$(wc -c < "$LOCAL_ROM" | tr -d ' ')

echo "==> Uploading $LOCAL_ROM ($LOCAL_SIZE bytes) -> $FTP_URL"
if ! curl -sS -T "$LOCAL_ROM" --ftp-create-dirs "$FTP_URL"; then
  echo "error: upload failed — is ftpd still running on the 3DS at $TARGET?" >&2
  exit 1
fi

echo "==> Verifying remote file size..."
REMOTE_SIZE="$(curl -sS -I "$FTP_URL" | grep -i '^Content-Length:' | tr -d '\r' | awk '{print $2}')"

if [[ -z "$REMOTE_SIZE" || "$REMOTE_SIZE" != "$LOCAL_SIZE" ]]; then
  echo "error: size mismatch — transfer may be corrupted or incomplete!" >&2
  echo "       local : $LOCAL_SIZE bytes" >&2
  echo "       remote: ${REMOTE_SIZE:-unknown} bytes" >&2
  exit 1
fi

echo "$TARGET" > "$CACHE_FILE"

echo
echo "Deployed and verified."
echo "   $FTP_URL"
echo "   $LOCAL_SIZE bytes"
