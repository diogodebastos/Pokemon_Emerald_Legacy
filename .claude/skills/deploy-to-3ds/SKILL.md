---
name: deploy-to-3ds
description: Copy the built ROM (pokeemerald.gba) to the 3DS over FTP (ftpd) so it can be played on-device, then verify the transfer. Use whenever the user wants to send/push/copy/deploy the ROM (or the game/build) to the 3DS, "put it on the 3DS", "test on the 3DS", or move pokeemerald.gba to the 3DS. Triggers even if they don't say FTP or ftpd.
---

# Deploy the ROM to the 3DS

Sends this repo's `./pokeemerald.gba` to the 3DS over FTP and verifies the byte
size landed intact. Requires **ftpd** running on the 3DS (Homebrew Launcher).

## Run it

```
.claude/skills/deploy-to-3ds/scripts/deploy-to-3ds.sh [HOST[:PORT]] [LOCAL_ROM] [REMOTE_NAME]
```

- `HOST[:PORT]` — the address ftpd shows on the 3DS screen (e.g. `192.168.1.166:5000`).
  Optional after the first successful run — it's cached in `scripts/.last_target`
  and reused automatically if omitted.
- `LOCAL_ROM` — defaults to `./pokeemerald.gba`.
- `REMOTE_NAME` — defaults to the same basename as `LOCAL_ROM`.

## How it works

Uploads via `curl` (anonymous FTP, no login needed for ftpd) to `/GBA/` on the
SD card, then re-queries the remote file's size with `curl -I` and compares it
against the local byte count. Refuses to call it done on a mismatch.

The remote folder is fixed at `/GBA` (matches this project's convention) —
override with `FTP_REMOTE_DIR` if needed.

## Before running

The script sends whatever `./pokeemerald.gba` currently is — it does **not**
build. For recent code changes to be on the 3DS, build first (`make`), then
run this.

## If the 3DS is unreachable

"Couldn't connect to server" means ftpd isn't running, the 3DS went to sleep,
or it's off the LAN. ftpd's address changes every time it (re)starts — ask the
user for the new `HOST:PORT` shown on the 3DS screen rather than assuming the
cached one still works.
