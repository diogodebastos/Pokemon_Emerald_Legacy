---
name: deploy-website
description: Deploy the Pokémon Emerald Legacy patcher website (the docs/ folder — index.html plus the patch.bps ROM patch) to its Cloudflare Pages project. Use this whenever the user wants to publish, redeploy, push, or update the website / patcher site / the live page, or says the patch (docs/patch.bps) has changed and the site needs refreshing. Trigger even if they don't name Cloudflare or wrangler explicitly — "redeploy the site", "push the new patch live", and "the website needs updating" all mean this.
---

# Deploy the patcher website to Cloudflare Pages

The patcher site lives in `docs/` (an `index.html` that fetches `patch.bps` and applies it in-browser, plus `pokedex.html`, `trainerdex.html`, and image assets). It is hosted on **Cloudflare Pages** — NOT GitHub Pages (this repo has no Pages site). Deploying is a manual `wrangler` step.

## Why this is a separate step from `git push`

`docs/patch.bps` is **gitignored** (`*.bps` in `.gitignore`) and is ~12 MB, so it never travels through git. That means **pushing code does not update the website** — the patch binary and the page are published only by the `wrangler` deploy below. Whenever the ROM is rebuilt and `patch.bps` regenerated, the site needs this deploy to serve the new patch.

## The deploy command

Run from the repo root:

```
npx wrangler pages deploy docs --project-name=pokemon-emerald-legacy-solo-leveling-colosseum --branch=solo-leveling-colosseum
```

- **Project:** `pokemon-emerald-legacy-solo-leveling-colosseum` → live at `pokemon-emerald-legacy-solo-leveling-colosseum.pages.dev` (a direct-upload Pages project; no Git provider attached).
- **Deploy folder:** `docs/`.
- **`--branch=solo-leveling-colosseum`** is the project's production branch, so the upload lands as a **production** deploy on the apex `.pages.dev` URL. Using a different branch name would create a non-production preview instead — only do that if the user explicitly asks for a preview.
- `wrangler` is installed globally and OAuth-authenticated (account `diogodebastos18@gmail.com`). If it reports an auth error, the user must re-run `wrangler login` themselves.
- wrangler warns "working directory ... has uncommitted changes" because `patch.bps` is untracked and there may be unstaged code. This is harmless — pass `--commit-dirty=true` to silence it if desired.

## Before deploying

Confirm `docs/patch.bps` reflects the change the user expects to publish. If they just rebuilt the ROM, the patch should already be regenerated into `docs/`; if you're unsure whether it's current, say so rather than silently shipping a stale patch. Do not try to regenerate the patch here — that's a separate build step outside this skill.

## After deploying

`wrangler` prints a deployment-specific URL (e.g. `https://<hash>.pokemon-emerald-legacy-solo-leveling-colosseum.pages.dev`) and the upload count. Report back to the user:
- the live production URL: `pokemon-emerald-legacy-solo-leveling-colosseum.pages.dev`
- the deploy-specific preview URL from wrangler's output
- how many files were newly uploaded (a single new `patch.bps` is the normal case; the rest are cache hits)

## Permissions note

A production deploy may be gated by the permission/auto-mode classifier. The project ships an allow-rule for `wrangler pages deploy` in `.claude/settings.json`, so it should run without prompting; if it's still blocked, confirm the project name with the user (it's the only Emerald-Legacy entry in `npx wrangler pages project list`) and proceed once they approve.
