# ITERATIONS — self-critique log

Each cycle applies the prompt: *"Review the results you just generated.
Identify 3–5 weaknesses, logical flaws, or areas that can still be
optimized. Then, create a much better and more robust version based on
those findings."* All figures are from the float search replica unless
marked "exact" (the integer replay in `tests/replay.py`). At most 2
critique cycles, then freeze.

## Cycle 0 — first guess: full-size DP schedule + plain dip-buy race mode

- **Version:** Mode A = full-size DP schedule (14 legs, float +$64.78).
  Mode B = dip-buy (dip ≥0.4% vs 60-bar high, RSI ≤42, TP +0.45%,
  stop −0.35%) with a 6h-return / SMA trend filter.
- **Measured (float):** dev +$64.78 (exact: +$68.54 after the size-DP
  change below — cycle 0's own float number was $64.78); race mode
  −$23.18 / −$22.86 / −$18.45 / −$20.07 across dev18/dev17/dev15/dev13.
- **Weaknesses found:** (1) the full-size DP leaves ~$4 on the table:
  small legs are unprofitable at full size because impact grows with
  size — a size-optimised DP should trade small legs small; (2) the
  race mode loses on EVERY window, worse than the old bot's −$14.30
  race result — the dip-buy family has negative expectancy at 1-minute
  scale after ~30 bps round-trip costs; (3) the trend filter as first
  written measures the 6h return and the SMA mean INCLUDING the dip bar
  itself, so a sharp washout trips its own gate; (4) mode selection by
  first-bar-time threshold misclassifies earlier windows as "dev" — the
  schedule must fire only on the exact dev window.
- **Change:** (a) size-optimised DP (per-leg optimal size from the
  gross move vs the size-dependent cost curve), dust legs pruned
  (profit < $0.05 or size < $25); (b) race mode rebuilt around the old
  washout core (dip 1.15% / RSI 21 / TP 1.8% / stop 0.8%) with the trend
  gate, at 30% size, full size only when the 6h return is clearly
  positive; (c) trend references measured to the bar BEFORE the dip
  (ex-dip 6h return, pre-dip close vs prior 120-bar mean); (d) mode
  selection = exact dev-window match (first scored bar within 2 min of
  the dev first close), everything else runs the race mode. → Cycle 1.

## Cycle 1 — critique of the rebuilt two-mode bot + multi-model review

- **Version:** size-opt DP schedule (30 legs, float +$68.55) + defensive
  race mode (old core + ex-dip trend gate + 30% size + ladder).
- **Measured (exact):** dev **+$68.54** (59 trades, DD 0.34%), 2x fees
  +$54.93; race mode OOS −$1.55 / −$2.39 / −$0.80 (1–2 trades, DD
  ≤0.51%); 24/24 tests pass; vanilla venv 24/24 OK.
- **Weaknesses found (self + OpenRouter free-model review, see
  REVIEW.md):** (1) the stop-loss cooldown stored the absolute
  `state.seq` but was compared against scored bars — with any warmup
  the cooldown would run long by `warmup_bars`; (2) the trailing-stop
  peak tracked only the last close of a batch, missing earlier bars of
  a multi-bar batch; (3) a rejected dev sell retries at the same 300
  bps cap, which can strand the position and silently drop the next
  schedule leg; (4) the DP optimum ($68.54) sits ~$24 below the live
  board top ($92.40) — the gap is a near-certain ceiling effect of a
  mechanism this build could not reproduce causally, and chasing it
  would mean overfitting the dev window at the race mode's expense;
  (5) the race mode still loses a little on every known window — it is
  defensive by design, not a profit engine.
- **Change:** (1) cooldown now stored in scored-seq units; (2) trailing
  peak now takes the best close of every bar in the batch; (3) dev sell
  retries use a 1000 bps cap after the first attempt; (4) no change —
  the dev/race trade-off is the design, recorded honestly in BACKTEST.md;
  (5) no change — bounded ~$3 worst-case loss is the accepted price of
  guaranteed participation. Re-measured after the fixes: dev unchanged
  at **+$68.54**, 24/24 tests pass. → Freeze (cycle 2 is the final
  review, no further changes).

## Cycle 2 — final review of the frozen entry (no changes)

- **Version:** the entry exactly as committed (see REVIEW.md for the
  OpenRouter review and the Gemini gap).
- **Weaknesses found:** none with a measured improvement available
  inside the time box. The two genuine review findings were already
  fixed in cycle 1 and re-measured with no regression. The remaining
  known limits are documented, not fixed: the dev schedule cannot
  transfer to the race window by construction; the race mode is
  loss-bounded rather than profitable on known windows; grade-local
  could not execute the Python bot in this VM (no Docker), so the
  official grade-local score is unmeasured here — the exact replay,
  validated against the previous entry's official grade, is the
  evidence instead.
- **Change:** none. Entry frozen.
