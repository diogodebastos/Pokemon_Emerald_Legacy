#!/bin/sh
# Generate docs/patch.bps as the delta between the clean base ROM and this
# project's freshly built ROM, then verify the patch round-trips before it
# replaces the live patch. Exits non-zero (and leaves docs/patch.bps untouched)
# if anything looks wrong, so a broken patch can never ship.
#
# Usage: gen-patch.sh [CLEAN_ROM] [MODIFIED_ROM] [OUT_BPS]
set -eu

CLEAN="${1:-/Users/ketchum/Desktop/decomps/pokeemerald-main/pokeemerald.gba}"
MODIFIED="${2:-pokeemerald.gba}"
OUT="${3:-docs/patch.bps}"

fail() { echo "gen-patch: $1" >&2; exit 1; }

command -v flips >/dev/null 2>&1 || fail "flips not on PATH. Build it once: see SKILL.md ('Installing flips')."
[ -f "$CLEAN" ]    || fail "clean base ROM not found: $CLEAN"
[ -f "$MODIFIED" ] || fail "modified ROM not found: $MODIFIED (run 'make' first to build it)"

# A BPS diff between two unrelated ROMs is meaningless; both should be the same
# GBA image size. This catches pointing at the wrong file far more cheaply than
# a failed apply.
sz_clean=$(wc -c < "$CLEAN")
sz_mod=$(wc -c < "$MODIFIED")
[ "$sz_clean" = "$sz_mod" ] || fail "ROM sizes differ ($sz_clean vs $sz_mod) — are these both Emerald GBA images?"

if cmp -s "$CLEAN" "$MODIFIED"; then
    fail "clean and modified ROMs are identical — nothing to patch (did the build pick up your changes?)"
fi

tmp_bps=$(mktemp -t patch.bps.XXXXXX)
tmp_out=$(mktemp -t apply.gba.XXXXXX)
trap 'rm -f "$tmp_bps" "$tmp_out"' EXIT

echo "gen-patch: creating BPS ($CLEAN -> $MODIFIED)"
flips --create --bps-delta "$CLEAN" "$MODIFIED" "$tmp_bps" >/dev/null

# The patch is only useful if applying it to the clean ROM reproduces the
# modified ROM exactly. Verify that here rather than trusting the encoder.
echo "gen-patch: verifying round-trip"
flips --apply "$tmp_bps" "$CLEAN" "$tmp_out" >/dev/null
cmp -s "$tmp_out" "$MODIFIED" || fail "round-trip mismatch — patch would NOT reproduce the modified ROM. Aborting."

mkdir -p "$(dirname "$OUT")"
mv "$tmp_bps" "$OUT"
trap 'rm -f "$tmp_out"' EXIT

echo "gen-patch: wrote $OUT ($(wc -c < "$OUT" | tr -d ' ') bytes), verified OK"

# Also drop a copy in ~/Downloads for convenience (e.g. to hand to a tester or
# upload by hand). Non-fatal: the canonical output is $OUT, so a missing
# Downloads dir shouldn't fail the run.
DL="$HOME/Downloads/patch.bps"
if cp "$OUT" "$DL" 2>/dev/null; then
    echo "gen-patch: copied to $DL"
else
    echo "gen-patch: could not copy to $DL (skipped)" >&2
fi
