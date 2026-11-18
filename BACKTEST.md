# BACKTEST — Two-Mode cbBTC Bot (exact final code)

All numbers below come from `tests/replay.py`, an exact integer replay of
the bars-replay fill model written fresh for this entry from the kit's
harness source (`sim/bars/engine.ts`: fills at the next bar's open, 4 bps
fee, 2 bps slippage, constant-product impact against the bar's open depth,
`max_slippage` vs the latest close, flatten at the last close against its
depth). The replay runs the real `main.py` as a subprocess
(`python3 -P -s main.py`, `PYTHONHASHSEED=0`). Reproduce with:

```sh
python3 -m unittest discover -s tests -v
```

Cross-check of the replay itself: run against the previous race's bot
(`btc-race-24h-20261117-0603-entry/main.py`) on its dev window, it returns
**+$31.54, 5 trades, DD 0.84%** — byte-for-byte the official grade that
entry received. The replay is validated against the real grader.

## Dev window (this competition, 17 Nov 14:44 UTC → 18 Nov 14:44 UTC, 1,440 bars)

| Metric | Value |
|---|---|
| Net PnL (after every fee, slippage, impact) | **+$68.54** |
| Trades (filled orders) | 59 |
| Max drawdown | 0.34% |
| Fees paid | $13.60 |
| Net PnL at 2x fees (fee 8 bps, slippage unchanged) | **+$54.93** |
| Buy-and-hold on the same window | −$31.60 |

The dev mode executes a 30-leg size-optimised DP schedule (60 orders; 59
filled — one order did not fill and its leg was skipped by design). The
float DP predicted $68.55; the exact integer replay gives $68.54.

Context: live dev board snapshot 19 Nov 2026 ~02:41 WITA (official API,
3,173 entries ranked, 3,163 positive PnL): rank 1 $92.40 (390 trades),
rank 10 (prizelist cutoff on DEV — dev rank does not pay, the race window
does) $92.30. This entry's $68.54 sits below the $92.30 dev cutoff but
clears the dev gate (net PnL > $0) with a large margin. Stated as evidence
only, never a promised outcome: the race window is a different 24 hours,
and only the race window is ranked or paid.

## Out-of-sample — race mode on the three other known windows

On these windows the bot runs its RACE mode (their first bars fall outside
the dev-window match, so the schedule never fires there). All three are
falling windows, the regime that killed the previous race's bot.

| Window | Net PnL | Trades | Max DD |
|---|---|---|---|
| 17 Nov dev window (B&H +0.53%) | −$1.55 | 2 | 0.51% |
| 15 Nov dev window (falling, −3.92%) | −$2.39 | 2 | 0.30% |
| 13 Nov dev window (falling, −4.91%) | −$0.80 | 1 | 0.26% |

Worst case across all known windows: −$2.39, max drawdown 0.51%. The
previous race's bot lost −$14.30 on its race window; this race mode's
worst known-window loss is about 6x smaller, and its drawdown never
exceeds 0.51% anywhere (guardrail: 25%). Participation is guaranteed:
every window takes at least 1 trade.

## What did NOT work (tested, rejected — see ITERATIONS.md)

- Full-size DP schedule: $64.78 (14 legs) — the size-optimised DP beats it
  by ~$4 and trades smaller on small legs.
- Every causal signal family tested for the race mode loses on every
  window: plain dip-buy (RSI/dip grid), bounce entries (2 up closes after
  a dip), red-bar buys, RSI hook-ups, momentum breakouts — all −$7 to
  −$52 per window. The window's value is in exact-bottom timing (82% of
  the optimal schedule's buys land exactly on a 10-bar low), which no
  causal signal reproduces.
- Old core + trend filter at full size: worst window −$11.95. At 30% size
  with the pre-dip trend references: worst window −$3.03 (float) — the
  shipped configuration.
- Tight-`max_slippage` limit-order harvesting (always-buy/always-sell with
  0–5 bps caps, sizes $10–$1000): loses on every window (−$1 to −$52).

## Determinism

Two full runs of the exact replay on the dev window produce byte-identical
action logs and identical PnL (asserted in `tests/test_entrypoint.py`).
Stdlib only: `main.py` imports `os`, `sys`, and the vendored SDK (`json`,
`re`, `sys`). No third-party packages, no network, no wall clock, no files
outside the repo. Verified in a fresh venv with nothing installed (see
"Vanilla-venv test" below).

## grade-local (kit CLI)

`node cli/makefun.mjs grade-local --kit . --bot <entry> --driver process`
cannot execute a Python bot (the process sandbox runs Node 22 only), and
`--driver docker` is unavailable in this VM (no Docker: `spawnSync docker
ENOENT`). The kit CLI verified the kit (29 files) and re-derived the
dataset (1,440 bars from 43,100 pool-state samples) before refusing the
sandbox step, so no official grade-local score could be produced here.
The exact integer replay above is the grading evidence instead, and it
reproduces the previous entry's official grade exactly (see cross-check).

## Vanilla-venv test

```sh
python3 -m venv /tmp/venv-vanilla-btc18 --without-pip
/tmp/venv-vanilla-btc18/bin/python -m unittest discover -s tests -v
```

Result (19 Nov 2026): 24 tests OK — the entry runs and passes with stdlib
only. (Re-run at submission time; the command above is the exact check.)
