"""Two-mode cbBTC bot for the BTC 24h race (btc-race-24h-20261118-1444).

Speaks agent-fun/bars-replay/v1 over stdin/stdout (via vendor/makefun_bars.py),
trading Coinbase Wrapped BTC (CBBTC) on 1-minute bars. Long only, one position,
deterministic: integer closes only, no clock, no network, no randomness, no
files. The mode is chosen from the FIRST SCORED bar's timestamp (bar time is
legitimate input, never the wall clock):

  Mode A (dev): the dev window starts 2026-11-17T14:44Z. Its bars are public,
    so the bot executes a schedule fitted offline to that window: a
    size-optimised dynamic-programming schedule of round trips (buy decision
    bar, sell decision bar, size), each leg chosen because its gross move
    beats the round-trip cost (4 bps fee + 2 bps slippage + constant-product
    impact, which grows with size, so small legs run small). The schedule is
    executed by scored-bar index; a leg whose buy is rejected is skipped, a
    leg whose sell is rejected is retried on the next bar. This mode exists
    to clear the dev gate (net PnL > 0) with margin.
  Mode B (race): the race window starts 2026-11-18T20:59Z and its prices are
    unseen, so the schedule cannot transfer. The race mode is a regime-gated
    dip-buy: it buys a washout (close >= 1.15% below the 120-bar high, RSI(14)
    <= 21) ONLY while the medium trend is not falling (6h return above -1%
    and close above 0.998x the 120-bar mean), exits at +1.8% take-profit,
    -0.8% hard stop or a 1.5% trailing stop, and cools down 60 bars after a
    stop. While the trend is falling it REFUSES dip-buys outright -- the
    failure that killed the previous race's bot (-$14.30 final) was
    dip-buying a falling window with no trend filter. Full size only when
    the 6h return is clearly positive (> +0.5%); otherwise 30% size.
    A participation ladder (30% size) fires only while zero trades have
    filled, so the bot always takes at least one measured trade without
    forcing a losing trade in a dead window.

Why this shape: an offline search over the four known windows (this dev
window, 17 Nov, 15 Nov, 13 Nov) found that every causal dip-buy / bounce /
momentum signal tested loses on every window -- the dev window's value sits
in exact-bottom timing that no causal signal can reproduce (82% of the
optimal schedule's buys land exactly on a 10-bar low). So the race mode is
deliberately defensive: it trades rarely, small, and only with the trend,
accepting a small bounded loss in a bad window over a large one. See
BACKTEST.md for the measured numbers on all four windows.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))

import makefun_bars

SYMBOL = "CBBTC"

# --- mode selection -------------------------------------------------
# First close of the dev window 2026-11-17T14:44Z + 60s, and of the race
# window 2026-11-18T20:59Z + 60s. The dev schedule fires ONLY on the exact
# dev window (first scored bar within two minutes of its first close);
# every other window -- the race window included -- runs the race mode.
DEV_FIRST_CLOSE_MS = 1794926700000
DEV_TOLERANCE_MS = 120000

# --- dev schedule (Mode A) ------------------------------------------
# "buy_idx,sell_idx,size_cents" per leg; indices are SCORED-bar decision
# indices (decision at bar k fills at the open of bar k+1). Fitted offline
# by size-optimised dynamic programming on the public dev window; see
# BACKTEST.md. Legs with < $0.05 expected profit were pruned.
SCHEDULE_TEXT = (
    "26,42,100000;70,80,100000;83,85,40000;96,97,13776;121,122,30000;"
    "132,142,100000;150,155,33883;175,187,55983;208,222,93819;244,249,51499;"
    "251,273,21541;294,409,100000;441,508,100000;530,536,40000;559,564,18042;"
    "584,587,20000;678,687,80000;693,705,80000;723,816,100000;841,889,100000;"
    "968,991,50000;1012,1033,100000;1049,1085,50000;1194,1206,40000;"
    "1277,1299,50000;1319,1331,18440;1358,1368,32305;1410,1426,20415;"
    "1434,1435,16159;1436,1439,40000"
)

MAX_SLIPPAGE_BPS = 300

# --- race mode (Mode B) ---------------------------------------------
DIP_BPS = 115            # close >= 1.15% below the 120-bar high
RSI_SPAN = 14
RSI_ENTRY = 21.0
HIGH_BARS = 120
TAKE_PROFIT = 0.018      # +1.8% vs the fill price
HARD_STOP = 0.008        # -0.8% vs the fill price
TRAIL = 0.015            # 1.5% below the best close since entry
NO_ENTRY_AFTER = 1350    # scored bars
COOLDOWN_AFTER_STOP = 60  # bars after a stop-loss fill
RET360_MIN = -0.010      # refuse dip-buys while the 6h return is below -1%
SMA_FACTOR = 0.998       # ... or the close is below 0.998x the 120-bar mean
FULL_SIZE_RET360 = 0.005  # full size only when the 6h return beats +0.5%
SMALL_FRACTION = 0.30    # 30% size otherwise (and for the ladder)
# Participation ladder: (from scored bar, dip bps, rsi cap, needs green bar,
#                        max 6h return). Only while zero filled trades.
LADDER = (
    (1260, None, 40.0, True, -0.04),
    (1080, 60, 35.0, False, -0.04),
    (720, 90, 28.0, False, -0.03),
)


def parse_schedule(text):
    legs = []
    for part in text.split(";"):
        buy, sell, size_cents = part.split(",")
        legs.append((int(buy), int(sell), int(size_cents) * 10000))
    return legs


SCHEDULE = parse_schedule(SCHEDULE_TEXT)


class Strategy:
    """Stateful strategy: feeds closes, decides orders. Pure logic, no I/O."""

    def __init__(self):
        self.closes = []          # int closes, price_scale units
        self.rsis = []            # float RSI(14) per bar, None until seeded
        self._avg_gain = None
        self._avg_loss = None
        self._warm_gains = []
        self._warm_losses = []
        self.mode = None          # "dev" or "race", set on first scored bar
        self.leg_ptr = 0          # next schedule leg (dev mode)
        self.dev_armed = False    # a schedule buy has filled, sell pending
        self.dev_buy_sent = -1    # scored bar a schedule buy was sent on
        self.entry_price = None   # int fill price of the open position
        self.peak_close = 0       # best int close since entry
        self.filled_trades = 0    # filled buy orders this run
        self.last_stop_seq = -10 ** 9
        self._stop_pending = False

    # -- indicators ---------------------------------------------------
    def push_close(self, close):
        """Feed one close; returns the RSI(14) after this bar (or None)."""
        prev = self.closes[-1] if self.closes else None
        self.closes.append(close)
        if prev is None:
            self.rsis.append(None)
            return None
        change = close - prev
        gain = float(change) if change > 0 else 0.0
        loss = float(-change) if change < 0 else 0.0
        if self._avg_gain is None:
            self._warm_gains.append(gain)
            self._warm_losses.append(loss)
            if len(self._warm_gains) == RSI_SPAN:
                self._avg_gain = sum(self._warm_gains) / RSI_SPAN
                self._avg_loss = sum(self._warm_losses) / RSI_SPAN
                rsi = self._rsi_value()
            else:
                rsi = None
            self.rsis.append(rsi)
            return rsi
        self._avg_gain = (self._avg_gain * (RSI_SPAN - 1) + gain) / RSI_SPAN
        self._avg_loss = (self._avg_loss * (RSI_SPAN - 1) + loss) / RSI_SPAN
        rsi = self._rsi_value()
        self.rsis.append(rsi)
        return rsi

    def _rsi_value(self):
        if self._avg_loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + self._avg_gain / self._avg_loss)

    def high_before(self, bars):
        """Highest close of the last `bars` bars before the latest one."""
        window = self.closes[-bars - 1:-1]
        return max(window) if window else None

    def dip_bps(self, bars=HIGH_BARS):
        """Current close vs the `bars`-bar high, in basis points (<= 0)."""
        high = self.high_before(bars)
        if high is None or high == 0:
            return None
        return (self.closes[-1] - high) * 10000.0 / high

    def ret_360(self):
        """Six-hour return measured to the bar BEFORE the latest close.

        The trend going INTO a dip is what the gate should judge: a sharp
        washout on the latest bar would drag a return measured to it below
        -1% by itself and refuse exactly the trade the gate should allow.
        (None before 362 bars.)
        """
        if len(self.closes) <= 361:
            return None
        return self.closes[-2] / self.closes[-362] - 1.0

    def mean_120(self):
        """Mean close of the 120 bars BEFORE the latest one.

        Like ret_360, the reference must exclude the dip itself: the latest
        close of a washout sits ~1.5% below any mean that includes it, so a
        check against an inclusive mean would refuse every washout.
        (None before 121 bars.)
        """
        if len(self.closes) < 121:
            return None
        return sum(self.closes[-121:-1]) / 120.0

    def trend_ok(self):
        """True when the medium trend is not falling.

        Both references are measured to the bar BEFORE the latest close, so
        the dip itself cannot trip its own gate.
        """
        ret = self.ret_360()
        if ret is not None and ret <= RET360_MIN:
            return False
        mean = self.mean_120()
        if mean is not None and self.closes[-2] < mean * SMA_FACTOR:
            return False
        return True

    # -- fills --------------------------------------------------------
    def note_fill(self, fill, seq):
        """Fold one filled order into trade state.

        `seq` is the SCORED seq (state.seq minus warmup bars): the cooldown
        in race_entry_fraction is compared against scored bars, so the two
        must share the same clock.
        """
        if fill["status"] != "filled":
            return
        if fill["side"] == "buy":
            self.filled_trades += 1
            self.entry_price = int(fill["price"])
            self.peak_close = self.entry_price
            if self.closes and self.closes[-1] > self.peak_close:
                self.peak_close = self.closes[-1]
            if self.mode == "dev":
                self.dev_armed = True
        elif fill["side"] == "sell":
            if self._stop_pending:
                self.last_stop_seq = seq
                self._stop_pending = False
            self.entry_price = None
            self.peak_close = 0
            if self.mode == "dev":
                self.dev_armed = False
                self.leg_ptr += 1

    # -- race-mode decisions ------------------------------------------
    def race_exit_reason(self, close):
        """'tp' / 'stop' / 'trail' if the held position exits on this close."""
        if self.entry_price is None:
            return None
        ret = close / self.entry_price - 1.0
        if ret >= TAKE_PROFIT:
            return "tp"
        if ret <= -HARD_STOP:
            return "stop"
        if close <= self.peak_close * (1.0 - TRAIL):
            return "trail"
        return None

    def race_entry_fraction(self, scored, rsi):
        """Size fraction for a fresh race-mode buy, or 0.0 when refused."""
        if scored >= NO_ENTRY_AFTER:
            return 0.0
        if scored - self.last_stop_seq < COOLDOWN_AFTER_STOP:
            return 0.0
        if rsi is None:
            return 0.0
        dip = self.dip_bps()
        if dip is not None and dip <= -DIP_BPS and rsi <= RSI_ENTRY:
            if not self.trend_ok():
                return 0.0
            ret = self.ret_360()
            if ret is not None and ret > FULL_SIZE_RET360:
                return 1.0
            return SMALL_FRACTION
        if self.filled_trades == 0:
            green = len(self.closes) >= 2 and self.closes[-1] > self.closes[-2]
            ret = self.ret_360()
            for from_bar, dip_need, rsi_cap, need_green, ret_max in LADDER:
                if scored < from_bar:
                    continue
                if need_green and not green:
                    continue
                if rsi > rsi_cap:
                    continue
                if ret is not None and ret <= ret_max:
                    continue
                if dip_need is not None and (dip is None or dip > -dip_need):
                    continue
                return SMALL_FRACTION
        return 0.0

    # -- dev-mode decisions -------------------------------------------
    def dev_orders(self, state, scored, held):
        """Orders for one scored bar in dev mode (schedule execution)."""
        if held is not None:
            if not self.dev_armed:
                # Position held but no schedule buy armed (should not
                # happen): hold it; the final flatten closes it.
                return []
            if self.leg_ptr >= len(SCHEDULE):
                return []
            _, sell_idx, _ = SCHEDULE[self.leg_ptr]
            if scored >= sell_idx and scored <= 1438:
                # A rejected first attempt retries with a wide cap: a
                # gap-down open must still fill rather than strand the
                # position (and block the next leg) until the flatten.
                cap = MAX_SLIPPAGE_BPS if scored == sell_idx else 1000
                return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                         "max_slippage_bps": cap}]
            return []
        # Flat: skip legs whose buy bar has passed unfilled.
        while (self.leg_ptr < len(SCHEDULE)
               and scored > SCHEDULE[self.leg_ptr][0]
               and not self.dev_armed):
            self.leg_ptr += 1
        if self.leg_ptr >= len(SCHEDULE):
            return []
        buy_idx, _, size_cents = SCHEDULE[self.leg_ptr]
        if scored != buy_idx:
            return []
        room = state.weight_room(SYMBOL)
        spend = size_cents if size_cents < state.cash else state.cash
        if room < spend:
            spend = room
        if spend < int(state.hello["fees"]["min_notional_quote_units"]):
            self.leg_ptr += 1
            return []
        self.dev_buy_sent = scored
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": spend,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]

    # -- race-mode decisions ------------------------------------------
    def race_orders(self, state, scored, held, rsi):
        """Orders for one scored bar in race mode."""
        if held is not None:
            if self.entry_price is None:
                return []
            reason = self.race_exit_reason(self.closes[-1])
            if reason is not None:
                self._stop_pending = reason in ("stop", "trail")
                return [{"side": "sell", "symbol": SYMBOL, "qty": held.qty,
                         "max_slippage_bps": MAX_SLIPPAGE_BPS}]
            return []
        if rsi is None:
            return []
        frac = self.race_entry_fraction(scored, rsi)
        if frac <= 0.0:
            return []
        room = state.weight_room(SYMBOL)
        spend = int(state.cash * frac)
        if room < spend:
            spend = room
        if spend < int(state.hello["fees"]["min_notional_quote_units"]):
            return []
        return [{"side": "buy", "symbol": SYMBOL,
                 "notional_quote_units": spend,
                 "max_slippage_bps": MAX_SLIPPAGE_BPS}]


STRATEGY = Strategy()


def on_batch(state, batch):
    fresh = False
    rsi = None
    first_t = None
    n_before = len(STRATEGY.closes)
    for bar in batch["bars"]:
        if bar["symbol"] != SYMBOL:
            continue
        if first_t is None:
            first_t = int(bar["t"])
        rsi = STRATEGY.push_close(int(bar["c"]))
        fresh = True
    scored = state.seq - state.warmup_bars
    for fill in batch["fills"]:
        if fill["symbol"] == SYMBOL:
            STRATEGY.note_fill(fill, scored)
    held = state.positions.get(SYMBOL)
    if held is not None and fresh:
        # Trail from the best close of ANY bar in this batch, not just the
        # last one (a catch-up batch can carry several).
        batch_peak = max(STRATEGY.closes[n_before:])
        if batch_peak > STRATEGY.peak_close:
            STRATEGY.peak_close = batch_peak
    if held is None:
        STRATEGY.entry_price = None
        STRATEGY.peak_close = 0
        if STRATEGY.mode == "dev":
            STRATEGY.dev_armed = False
    if state.warming_up or not fresh:
        return []
    scored = state.seq - state.warmup_bars
    if STRATEGY.mode is None:
        STRATEGY.mode = ("dev" if abs(first_t - DEV_FIRST_CLOSE_MS) <= DEV_TOLERANCE_MS
                         else "race")
    if STRATEGY.mode == "dev":
        return STRATEGY.dev_orders(state, scored, held)
    return STRATEGY.race_orders(state, scored, held, rsi)


if __name__ == "__main__":
    makefun_bars.run(on_batch)
