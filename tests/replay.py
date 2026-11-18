"""Exact integer replay of agent-fun/bars-replay/v1 for local grading.

Written fresh for this entry from the kit's RULES.txt and the harness
source (sim/bars/engine.ts: BarsPool, barsBuyFill, barsSellFill). It runs
the real main.py as a subprocess (python3 -P -s main.py, PYTHONHASHSEED=0)
over a frozen bar file and settles every order exactly the way the grader
does: fills at the next bar's open, 4 bps fee, 2 bps slippage,
constant-product impact against the bar's open depth, max_slippage checked
against the latest close, flatten at the last close against its depth.

fee_multiplier=2 doubles fee_bps only (slippage unchanged), matching the
grader's cost-sensitivity column (net PnL at 2x fees).
"""
import gzip
import json
import subprocess
import sys

BPS = 10000
QUOTE_SCALE = 6
PRICE_SCALE = 5
QTY_SCALE = 8
SCALE_POW = 10 ** (QTY_SCALE + PRICE_SCALE)  # 10**13


def load_bars(path):
    return [json.loads(line) for line in gzip.open(path, "rt")]


def value_of(qty, price):
    return qty * price * 10 ** QUOTE_SCALE // SCALE_POW


def buy_fill(notional, open_price, depth_raw, fee_bps, slippage_bps):
    """(price, qty, fee) for a buy filling at `open_price` on one hop.

    price = open * (10000 + slip) * (D + spend) / (10000 * D) with
    D = depth_raw * 10**6 and spend in quote units; qty truncates.
    """
    spend = notional * (BPS - fee_bps) // BPS
    d = depth_raw * 10 ** QUOTE_SCALE
    price = open_price * (BPS + slippage_bps) * (d + spend * 10 ** 6) // (BPS * d)
    qty = spend * SCALE_POW // (price * 10 ** QUOTE_SCALE)
    return price, qty, notional - spend


def sell_fill(qty, open_price, depth_raw, fee_bps, slippage_bps):
    """(price, gross, proceeds, fee) for a sell filling at `open_price`."""
    value = value_of(qty, open_price)
    d = depth_raw * 10 ** QUOTE_SCALE
    # slipped = open * (10000 - slip) * d / (10000 * (d + value * 10**6))
    slipped = open_price * (BPS - slippage_bps) * d // (BPS * (d + value * 10 ** 6))
    price = slipped if slipped >= 1 else 1
    gross = value_of(qty, price)
    proceeds = gross * (BPS - fee_bps) // BPS
    return price, gross, proceeds, gross - proceeds


class ReplayResult:
    def __init__(self):
        self.pnl_units = 0
        self.trades = 0
        self.max_drawdown = 0.0
        self.fees_units = 0
        self.action_log = b""


def run_replay(main_path, bars, fee_multiplier=1):
    """Run main.py as a subprocess over `bars`; return a ReplayResult."""
    fee_bps = 4 * fee_multiplier
    slippage_bps = 2
    hello = {
        "type": "hello",
        "protocol": "agent-fun/bars-replay/v1",
        "seed": "1",
        "symbols": [{"symbol": "CBBTC",
                     "mint": "cbbtcf3aa214zXHbiAZQwf4122FBYbraNdFqgw4iMij",
                     "price_scale": PRICE_SCALE, "qty_scale": QTY_SCALE}],
        "capital": {"quote": "USDC", "quote_scale": QUOTE_SCALE,
                    "quote_units": "1000000000"},
        "bar_interval": "1m",
        "first_close_ms": bars[0]["t"],
        "caps": {"max_open_positions": 1, "max_orders_per_bar": 16,
                 "max_weight_bps": 10000, "shorts": False, "leverage": False},
        "fees": {"fee_bps": fee_bps, "slippage_bps": slippage_bps,
                 "min_notional_quote_units": "1000000"},
        "latency_bars": 1,
    }
    proc = subprocess.Popen(
        [sys.executable, "-P", "-s", main_path],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
        env={"PYTHONHASHSEED": "0", "PATH": "/usr/bin:/bin:/usr/local/bin"},
    )
    wire = [{"symbol": "CBBTC", "t": b["t"], "o": b["o"], "h": b["h"],
             "l": b["l"], "c": b["c"], "v": b["v"],
             "o_depth": b["o_depth"], "c_depth": b["c_depth"]}
            for b in bars]
    bars = wire
    result = ReplayResult()
    cash = 1000000000
    qty = 0
    cost = 0
    peak_eq = cash
    max_dd = 0.0
    fees = 0
    pending = []  # (order, decided_t, close_at_decision)
    log_lines = []

    def account(cur):
        pos = []
        if qty > 0:
            pos.append({"symbol": "CBBTC", "qty": str(qty),
                        "cost_quote_units": str(cost)})
        eq = cash + (value_of(qty, int(bars[cur]["c"])) if qty > 0 else 0)
        return {"cash_quote_units": str(cash), "positions": pos,
                "equity_quote_units": str(eq)}

    def send(obj):
        proc.stdin.write(json.dumps(obj, separators=(",", ":")) + "\n")
        proc.stdin.flush()

    try:
        send(hello)
        for seq, bar in enumerate(bars):
            cur = seq
            fills = []
            for order, decided_t, close_dec in pending:
                reason = None
                if order["side"] == "buy":
                    notional = int(order["notional_quote_units"])
                    if notional < 1000000:
                        reason = "below_min_notional"
                    elif notional > cash:
                        reason = "insufficient_cash"
                    else:
                        eq = cash + value_of(qty, int(bar["c"]))
                        if value_of(qty, int(bar["c"])) + notional > eq:
                            reason = "max_weight"
                    if reason is None:
                        price, q, fee = buy_fill(notional, int(bar["o"]),
                                                 int(bar["o_depth"][0]),
                                                 fee_bps, slippage_bps)
                        if price * BPS > close_dec * (BPS + int(order["max_slippage_bps"])):
                            reason = "max_slippage"
                        elif q == 0:
                            reason = "zero_amount"
                    if reason is not None:
                        fills.append({"client_id": order["client_id"], "symbol": "CBBTC",
                                      "side": "buy", "status": "rejected", "reason": reason,
                                      "decided_bar": decided_t, "fill_bar": bar["t"],
                                      "price": "0", "qty": "0",
                                      "notional_quote_units": "0", "fee_quote_units": "0"})
                        continue
                    cash -= notional
                    qty += q
                    cost += notional
                    fees += fee
                    result.trades += 1
                    fills.append({"client_id": order["client_id"], "symbol": "CBBTC",
                                  "side": "buy", "status": "filled", "reason": None,
                                  "decided_bar": decided_t, "fill_bar": bar["t"],
                                  "price": str(price), "qty": str(q),
                                  "notional_quote_units": str(notional),
                                  "fee_quote_units": str(fee)})
                else:  # sell
                    q = int(order["qty"])
                    if q > qty:
                        reason = "insufficient_position"
                    if reason is None:
                        price, gross, proceeds, fee = sell_fill(
                            q, int(bar["o"]), int(bar["o_depth"][0]),
                            fee_bps, slippage_bps)
                        if price * BPS < close_dec * (BPS - int(order["max_slippage_bps"])):
                            reason = "max_slippage"
                    if reason is not None:
                        fills.append({"client_id": order["client_id"], "symbol": "CBBTC",
                                      "side": "sell", "status": "rejected", "reason": reason,
                                      "decided_bar": decided_t, "fill_bar": bar["t"],
                                      "price": "0", "qty": "0",
                                      "notional_quote_units": "0", "fee_quote_units": "0"})
                        continue
                    cash += proceeds
                    cost = cost * (qty - q) // qty if qty > 0 else 0
                    qty -= q
                    fees += fee
                    result.trades += 1
                    fills.append({"client_id": order["client_id"], "symbol": "CBBTC",
                                  "side": "sell", "status": "filled", "reason": None,
                                  "decided_bar": decided_t, "fill_bar": bar["t"],
                                  "price": str(price), "qty": str(q),
                                  "notional_quote_units": str(gross),
                                  "fee_quote_units": str(fee)})
            pending = []
            batch = {"type": "batch", "seq": seq, "t": bar["t"],
                     "bars": [bar], "fills": fills, "account": account(cur)}
            send(batch)
            line = proc.stdout.readline()
            if not line:
                raise RuntimeError(f"bot exited early at batch {seq}: "
                                   + proc.stderr.read()[-2000:])
            log_lines.append(line.rstrip("\n"))
            reply = json.loads(line)
            assert reply["type"] == "reply" and reply["seq"] == seq, reply
            orders = reply["orders"]
            assert len(orders) <= 16, "too many orders"
            if seq < len(bars) - 1:
                close_dec = int(bar["c"])
                for order in orders:
                    pending.append((order, bar["t"], close_dec))
            eq = cash + (value_of(qty, int(bar["c"])) if qty > 0 else 0)
            if eq > peak_eq:
                peak_eq = eq
            dd = (peak_eq - eq) / peak_eq
            if dd > max_dd:
                max_dd = dd
        done = {"type": "done", "seq": len(bars), "reason": "end_of_data",
                "account": account(len(bars) - 1)}
        send(done)
        if qty > 0:
            last = bars[-1]
            price, gross, proceeds, fee = sell_fill(
                qty, int(last["c"]), int(last["c_depth"][0]), fee_bps, slippage_bps)
            cash += proceeds
            fees += fee
            qty = 0
            cost = 0
        eq = cash
        if eq > peak_eq:
            peak_eq = eq
        dd = (peak_eq - eq) / peak_eq
        if dd > max_dd:
            max_dd = dd
        proc.stdin.close()
        proc.wait(timeout=30)
        proc.stdout.close()
        proc.stderr.close()
    finally:
        if proc.poll() is None:
            proc.kill()
    result.pnl_units = cash - 1000000000
    result.max_drawdown = max_dd
    result.fees_units = fees
    result.action_log = ("\n".join(log_lines) + "\n").encode()
    return result
