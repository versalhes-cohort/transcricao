# RUNBOOK — Transcrição Universal

Operational procedures for the live MVP.
**Live URL:** https://transcricao-production-1dac.up.railway.app

---

## 1. Upgrade `yt-dlp`

When source platforms (YouTube/Instagram/TikTok) break their HTML and yt-dlp stops extracting:

1. Find the latest stable `yt-dlp` release: https://pypi.org/project/yt-dlp/
2. Edit `requirements.txt` — bump the pinned version (e.g., `yt-dlp==2025.X.X`).
3. Test locally:
   ```bash
   pip install -r requirements.txt
   python3 -m pytest
   # expect: 85 passed
   ```
4. Commit + push:
   ```bash
   git commit -am "chore(deps): bump yt-dlp to <version>"
   git push origin main
   ```
5. Railway auto-redeploys. Confirm with:
   ```bash
   railway deployment list | head -3
   # expect: BUILDING → SUCCESS within ~10-15 min
   ```
6. Re-run smoke test cases 1–4 from `docs/smoke-tests.md` to confirm extraction works on the breaking platform.

---

## 2. Rotate the OpenAI API Key

When the existing key is compromised, leaked, or simply due for rotation:

1. Generate a new key: https://platform.openai.com/api-keys → **"Create new secret key"**.
2. **Confirm the same monthly $20 cap still applies** to the org/account (architecture §6.2 NFR3 — the cap is per-org, not per-key, so this is automatic, but verify the cap dashboard once at https://platform.openai.com/settings/organization/limits).
3. In Railway: project `transcricao` → **Variables** → edit `OPENAI_API_KEY` → paste new value → save.
4. Railway redeploys automatically (~10–15 min).
5. Verify boot: tail logs for the boot-check from Story 1.4:
   ```bash
   railway logs | grep -i "api key"
   # expect: NO "OPENAI_API_KEY environment variable is required" RuntimeError
   ```
6. Run smoke test case 1 (any short video) to confirm transcription works with the new key.
7. **Revoke the old key** on https://platform.openai.com/api-keys.

---

## 3. Inspect Railway Logs

When a deploy fails or a user reports a transcription error:

```bash
# Tail recent logs
railway logs | head -100

# Stream live logs
railway logs --tail
```

Filter by event prefix (Story 1.3 + 1.4 emit structured INFO lines):

| Prefix | Source story | Means |
|---|---|---|
| `download_ok` | Story 1.3 | yt-dlp completed audio extraction |
| `transcription_ok` | Story 1.4 | Whisper returned a transcript (length-only logged, NFR10) |
| `Unexpected error in pipeline` | Story 1.6 | top-level catch-all triggered (something genuinely unexpected) |

**Privacy notes:**
- URLs in tracebacks are redacted to `[URL]` by `SafeLogFilter` (Story 1.3, NFR10).
- Transcripts are NEVER logged — only `transcript_chars=N` length.
- To correlate events across a single user session, use the `url_hash` field — same hash across `download_ok` + `transcription_ok` lines means same source URL.

---

## 4. Roll Back a Bad Deploy

See `README.md` "Production Deployment / Rollback Procedure" — copied here for self-containment:

1. Open Railway dashboard → project `transcricao` → service `transcricao` → **Deployments** tab.
2. Locate the last known-good deploy (status `SUCCESS`, was active before the bad one).
3. Click `⋮` → **Redeploy**.
4. Wait for `SUCCESS` (~10–15 min).
5. Verify:
   ```bash
   curl -fsS https://transcricao-production-1dac.up.railway.app/_stcore/health
   # expect: HTTP 200 OK
   ```

**Faster alternative** (if Git history is clean):
```bash
git revert <bad-commit-sha>
git push origin main
# Railway auto-redeploys from the reverted commit
```

Use the `git revert` path when the bad deploy's root cause is clear in the diff. Use the dashboard rollback when the issue is environmental (e.g., bad env var) and the previous build is known good.

---

## Quick References

- **Architecture:** [`docs/architecture.md`](docs/architecture.md) — deployment §2, errors §6, NFRs §6.2
- **Smoke tests:** [`docs/smoke-tests.md`](docs/smoke-tests.md)
- **PRD:** [`docs/prd.md`](docs/prd.md)
- **Stories:** [`docs/stories/`](docs/stories/)
