---
name: gen-patch
description: Generate the distributable BPS patch (docs/patch.bps) for Pokémon Emerald Legacy by diffing the clean base ROM against this project's freshly built pokeemerald.gba. Use this whenever the user wants to (re)generate the patch, "make the .bps", "update patch.bps", "build the patch for the website", or has just rebuilt the ROM and needs a new patch to distribute. This is the scripted replacement for manually diffing the two ROMs in RomPatcher.js. Trigger even if they don't say "bps" — "regenerate the patch" and "the ROM changed, remake the download" mean this.
---

# Generate the BPS patch (docs/patch.bps)

The website distributes the hack as a **BPS patch**, not a ROM (legal reasons — players supply their own clean Emerald). `docs/patch.bps` is the delta between:

- **Clean base ROM:** `/Users/ketchum/Desktop/decomps/pokeemerald-main/pokeemerald.gba` (vanilla Emerald — the "Original ROM" in the manual RomPatcher.js flow)
- **Modified ROM:** this repo's `./pokeemerald.gba` (the build output — the "Modified ROM")

Manually this is done at https://www.marcrobledo.com/RomPatcher.js/. This skill does the same diff on the command line with **flips** (Floating IPS), which produces a standard BPS that applies correctly in that same RomPatcher.js on the site — and is far smaller (~1.5 MB vs ~12 MB).

## Run it

```
.claude/skills/gen-patch/scripts/gen-patch.sh
```

The script (`scripts/gen-patch.sh`) takes optional `[CLEAN_ROM] [MODIFIED_ROM] [OUT_BPS]` args but defaults to the paths above and writes `docs/patch.bps`. It:
1. sanity-checks both ROMs exist, are the same size, and actually differ;
2. creates the patch with `flips --create --bps-delta`;
3. **verifies the round-trip** — applies the new patch to the clean ROM and byte-compares the result against the modified ROM;
4. only then moves it into `docs/patch.bps`;
5. also copies it to `~/Downloads/patch.bps` for convenience (handing to a tester, manual upload). This copy is best-effort — the canonical output is `docs/patch.bps`.

Step 3 is the important one: a patch that doesn't reproduce the modified ROM exactly is worthless, so the script refuses to overwrite the live patch unless the round-trip matches. If it aborts, `docs/patch.bps` is left as-is.

## Before running

The patch reflects whatever `./pokeemerald.gba` currently is — it does **not** build. If the user wants the patch to include recent code changes, build first (`make`) so `pokeemerald.gba` is current, then run this. If `pokeemerald.gba` is missing, the build hasn't been run.

## After running

Report the new `docs/patch.bps` size and that the round-trip verified. `docs/patch.bps` is gitignored and is *not* published by a git push — to put the new patch live, follow up with the **deploy-website** skill (which uploads `docs/` to Cloudflare Pages). A natural chain is: `make` → gen-patch → deploy-website.

## Installing flips (one-time, if `flips` isn't on PATH)

There's no Homebrew formula; build the CLI from source (small, no GTK needed):

```
git clone --depth 1 https://github.com/Alcaro/Flips.git /tmp/Flips
cd /tmp/Flips && make TARGET=cli
cp flips /usr/local/bin/flips && chmod +x /usr/local/bin/flips
```

`flips --version` should then print "Floating IPS v1". The `TARGET=cli` build is CLI-only (`-DFLIPS_CLI`), so it doesn't need the GUI/GTK dependencies.
