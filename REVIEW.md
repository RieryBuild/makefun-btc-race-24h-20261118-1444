# REVIEW — multi-model review

## OpenRouter (code/reasoning review) — DONE

- **Model:** `nvidia/nemotron-3-ultra-550b-a55b:free` (verified free via
  `GET /models` first; 14 `:free` models listed at review time).
- **Sent:** the full `main.py` source + measured scores (dev +$68.54 /
  59 trades / DD 0.34% / 2x fees +$54.93; race-mode OOS −$1.55 / −$2.39 /
  −$0.80) + the protocol context. No sensitive data (no keys, no wallet
  material, no personal details). Cost $0.
- **Verdict:** 5 weaknesses raised. Three were genuine and FIXED (all
  re-measured, dev unchanged at +$68.54, 24/24 tests pass):
  1. **Cooldown clock mismatch (real bug):** `note_fill` stored the
     absolute `state.seq`, but `race_entry_fraction` compares against
     scored bars — with any warmup the cooldown would run long by
     `warmup_bars`. Fixed: `note_fill` now receives the scored seq.
  2. **Trailing-stop peak tracked only the last close of a batch:**
     a multi-bar catch-up batch could miss an earlier higher close.
     Fixed: the peak now takes the best close of every bar in the batch.
  3. **Rejected dev sell retries at the same 300 bps cap:** a
     gap-down open could strand the position and silently drop the
     next schedule leg. Fixed: retries use a 1000 bps cap.
  Two were assessed and NOT changed:
  4. **Mode selection uses a warmup-bar timestamp:** not applicable —
     the mode is set only on the first SCORED batch (the code returns
     early on warmup batches before the mode assignment), and each
     batch carries one bar per symbol, so `first_t` is the first scored
     bar's timestamp by construction.
  5. **"No explicit final flatten":** wrong — the harness itself
     flattens everything held at the last close (RULES.txt, "Capital,
     caps and fills"); the bot must not order on the last batch
     (after_end rejection). No change.
- **Not applied:** nothing else was suggested. No dev-PnL chasing was
  requested or applied.

## Gemini (text/copy review) — SKIPPED, gap recorded (not a fail)

- **Test:** `GET /v1beta/models` works (key live, models listed). One
  `POST /v1beta/models/gemini-3.8-flash:generateContent` attempt failed
  at the transport layer with **HTTP 411 Length Required** (an HTML
  error page from the Google front-end, not a Gemini model error) —
  the helper's POST did not carry a Content-Length the endpoint
  accepts. No Gemini verdict was obtained, and no second attempt was
  made inside the build time-box. This matches the known state from
  18 Nov (text generation unusable on the replacement key); the 503s
  have not cleared in any usable sense. Skip is NOT a fail per the
  build brief.
- **Xingchiapi / GPT-6.1-sol:** NEVER used (retired per the brief).

## Self-critique

See ITERATIONS.md cycles 0–2 (2 critique cycles, then freeze). The
remaining known limits are documented in BACKTEST.md: the dev schedule
cannot transfer to the race window by construction; the race mode is
loss-bounded rather than profitable on known windows; grade-local could
not execute the Python bot in this VM (no Docker), so the official
grade-local score is unmeasured here and the exact replay — validated
against the previous entry's official grade (+$31.54 reproduced
exactly) — is the evidence instead.
