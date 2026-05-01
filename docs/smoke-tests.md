# Smoke Test Suite — Production Validation

> Recorded against the live Railway deploy: https://transcricao-production-1dac.up.railway.app
> Each case logs URL **hash** (per NFR10), NOT the full URL. Use `python3 -c "from app.logging_config import hash_url; print(hash_url('<url>'))"` to compute.

## Required Cases (Story 1.7 AC4 + AC5)

| # | Source | Expected Outcome | URL Hash | Timestamp | Transcript Chars | Pass/Fail | Notes |
|---|---|---|---|---|---|---|---|
| 1 | YouTube long-form (10–30 min) | Full PT-BR transcript + duration line | _________ | _________ | _________ | _________ | |
| 2 | YouTube Shorts (<60s) | Full PT-BR transcript + duration line | _________ | _________ | _________ | _________ | |
| 3 | Instagram Reel | Full PT-BR transcript + duration line | _________ | _________ | _________ | _________ | |
| 4 | TikTok | Full PT-BR transcript + duration line | _________ | _________ | _________ | _________ | |
| 5 | Generic HTML page with embedded `<video>` | Full PT-BR transcript + duration line | _________ | _________ | _________ | _________ | |
| 6 | Video >60 min | PT-BR rejection: "Vídeo excede o limite de 60 minutos." | _________ | _________ | n/a | _________ | (AC5) |

## Additional Error Cases (architecture §9.3 — recommended)

| # | Source | Expected Outcome | Pass/Fail | Notes |
|---|---|---|---|---|
| 7 | Malformed URL (e.g., `not-a-url`) | PT-BR rejection: "URL inválida..." | _________ | |
| 8 | Unreachable URL (e.g., `https://example.invalid/nope`) | PT-BR rejection: "Não foi possível acessar este vídeo..." | _________ | |

## OpenAI Spending Cap Verification (AC6)

- **Account:** _____________ (email — match Railway env)
- **Monthly cap:** $20.00 USD
- **Verified on:** _________ (date)
- **Evidence:** see `docs/screenshots/openai-cap-YYYY-MM-DD.png`

## Cold-Start Measurement (AC8)

- **Sleep induction:** wait ≥30 min after last request (or wait until Railway logs show a sleep event).
- **Measurement:** time from first browser hit to interactive form. Use browser DevTools → Network tab → "Time to Interactive". If TTI is unavailable, use wall-clock from browser hit to clickable form.
- **Result:** _____ seconds.
- **Threshold:** 60s (NFR16) — if exceeded, add an investigation entry to `## Known Issues` below. **Not launch-blocking** per AC8.

## Known Issues

> Add any AC8 cold-start exceptions or other launch-blocking observations here.

_None recorded._

## Sign-Off

- **Owner:** Andre (`andremaass.ita@gmail.com`)
- **Date:** _________
- **Decision:** ☐ LAUNCH APPROVED · ☐ LAUNCH BLOCKED (see Known Issues)

---

## Hash Computation Helper

```bash
# From the project root, with the virtualenv active (or system Python with deps installed):
python3 -c "from app.logging_config import hash_url; print(hash_url('https://your-source-url-here'))"
```

The output is an 8-character SHA-256 prefix — paste it into the URL Hash column. **Never paste the full URL anywhere in this file** (NFR10).
