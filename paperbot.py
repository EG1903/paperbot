#!/usr/bin/env python3
"""Paper-Trading-Bot: Opening-Range-Breakout (gleiche Regeln wie die trader-* Skills).

Handelt NUR auf Papier (simuliertes Konto, kein Broker, kein echtes Geld).
Er prüft laufend ein "Profitabilitäts-Gate". Auch wenn es bestanden ist,
handelt der Bot NICHT live – er meldet es nur. Live gehen entscheidest du.

    python paperbot.py backtest            # letzte ~60 Tage 5m-Bars simulieren
    python paperbot.py run                 # live mitlaufen (heute), Papier-Fills
    python paperbot.py status              # Konto, Statistik, Gate
    python optimize.py                     # Parameter-Suche mit Train/Test-Split

Strategie (long only):
  Opening Range = erste 5 Min (9:30-9:35 NY). Einstieg auf dem ersten
  geschlossenen 5m-Bar, der ÜBER dem Range-Hoch schließt (bis 15:30).
  Stop = Range-Mitte, Ziel = 2R, flat um 15:55. Risiko 1% des Kontos pro Trade.
  Stop+Ziel im selben Bar -> Stop zählt (konservativ). Slippage 0.02% je Seite.
Daten: Yahoo chart JSON (kostenlos, inoffiziell, ggf. verzögert).
"""
import warnings; warnings.filterwarnings('ignore', category=DeprecationWarning)
import argparse, datetime as dt, json, os, sys, time, urllib.request, urllib.error

STATE = "paperbot_state.json"
CFG = {
    "watchlist": ["TSLA", "NVDA", "AMD", "AAPL", "META", "AMZN", "MSFT", "GOOGL", "NFLX", "COIN"],
    "start_cash": 10000.0,
    "risk_pct": 0.01,          # 1% Risiko pro Trade
    "max_pos_pct": 0.25,       # max 25% des Kontos pro Position
    "max_trades_per_day": 3,
    "daily_loss_limit_pct": 0.03,
    "or_minutes": 5,
    "target_r": 2.0,
    "slippage": 0.0002,
    "last_entry": "11:00",
    "flat_by": "15:55",
    "stop_mode": "low",        # mid = Range-Mitte, low = Range-Tief
    "min_volume_x": 0.0,       # Trigger-Bar-Volumen vs. Range-Durchschnitt (0 = aus)
    "trend_filter": False,     # nur wenn Range-Hoch > Vortagesschluss
    "max_range_pct": 1.0,      # Range-Breite max. in % vom Preis (1.0 = aus)
    # Profitabilitäts-Gate
    "gate_min_trades": 50,
    "gate_min_profit_factor": 1.3,
    "gate_max_drawdown_pct": 0.10,
}

# ---------- Zeit (New York) ----------
def ny_offset(utc):
    y = utc.year
    def nth_sun(m, n):
        d = dt.datetime(y, m, 1)
        return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))
    start = nth_sun(3, 2) + dt.timedelta(hours=7)
    end = nth_sun(11, 1) + dt.timedelta(hours=6)
    return -4 if start <= utc.replace(tzinfo=None) < end else -5

def ny(ts):
    u = dt.datetime.utcfromtimestamp(ts)
    return u + dt.timedelta(hours=ny_offset(u))

def hhmm(s):
    h, m = s.split(":"); return dt.time(int(h), int(m))

# ---------- Daten ----------
def fetch(sym, rng):
    path = "/v8/finance/chart/%s?range=%s&interval=5m" % (sym, rng)
    for host in ("query2", "query1"):
        for attempt in range(2):
            try:
                req = urllib.request.Request("https://%s.finance.yahoo.com%s" % (host, path),
                                             headers={"User-Agent": "Mozilla/5.0 paperbot"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    j = json.loads(r.read())
                res = j["chart"]["result"][0]
                q = res["indicators"]["quote"][0]
                bars = []
                for i, t in enumerate(res.get("timestamp") or []):
                    o, h, l, c, v = q["open"][i], q["high"][i], q["low"][i], q["close"][i], q["volume"][i] or 0
                    if None in (o, h, l, c):
                        continue
                    t_ny = ny(t)
                    if t_ny.minute % 5 or t_ny.second:
                        continue
                    bars.append({"t": t_ny, "o": o, "h": h, "l": l, "c": c, "v": v})
                return bars
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 0:
                    time.sleep(5); continue
                break
            except Exception:
                break
    return []

def by_day(bars):
    days = {}
    for b in bars:
        if dt.time(9, 30) <= b["t"].time() < dt.time(16, 0):
            days.setdefault(b["t"].date(), []).append(b)
    return days

# ---------- Strategie ----------
def simulate_day(bars, now=None, prev_close=None):
    """Gibt (entry_bar_idx, entry, stop, target, exit, exit_time, reason) oder None.
    now: nur Bars, die bis dahin geschlossen sind, zählen (Live-Modus)."""
    c = CFG
    if now:
        bars = [b for b in bars if b["t"] + dt.timedelta(minutes=5) <= now]
    or_end = (dt.datetime.combine(dt.date.today(), dt.time(9, 30)) + dt.timedelta(minutes=c["or_minutes"])).time()
    rng = [b for b in bars if b["t"].time() < or_end]
    if len(rng) < c["or_minutes"] // 5:
        return None
    hi, lo = max(b["h"] for b in rng), min(b["l"] for b in rng)
    stop = round((hi + lo) / 2 if c["stop_mode"] == "mid" else lo - 0.01, 2)
    if (hi - lo) / hi > c["max_range_pct"]:
        return None
    if c["trend_filter"] and prev_close and hi <= prev_close:
        return None
    avg_v = sum(b["v"] for b in rng) / len(rng)
    for i, b in enumerate(bars):
        if b["t"].time() < or_end:
            continue
        close_t = (b["t"] + dt.timedelta(minutes=5)).time()
        if close_t > hhmm(c["last_entry"]):
            return None
        if b["c"] > hi and b["v"] >= c["min_volume_x"] * avg_v:
            entry = round(b["c"] * (1 + c["slippage"]), 2)
            if entry <= stop:
                return None
            target = round(entry + c["target_r"] * (entry - stop), 2)
            for b2 in bars[i + 1:]:
                if b2["l"] <= stop:
                    return dict(entry=entry, stop=stop, target=target, exit=stop, t_in=b["t"], t_out=b2["t"], why="stop")
                if b2["h"] >= target:
                    return dict(entry=entry, stop=stop, target=target, exit=target, t_in=b["t"], t_out=b2["t"], why="target")
                if (b2["t"] + dt.timedelta(minutes=5)).time() >= hhmm(c["flat_by"]):
                    return dict(entry=entry, stop=stop, target=target, exit=b2["c"], t_in=b["t"], t_out=b2["t"], why="flat")
            return dict(entry=entry, stop=stop, target=target, exit=None, t_in=b["t"], t_out=None, why="open")
    return None

def size(cash, equity, entry, stop):
    c = CFG
    risk_sh = int(equity * c["risk_pct"] / (entry - stop))
    cap_sh = int(min(equity * c["max_pos_pct"], cash) / entry)
    return max(0, min(risk_sh, cap_sh))

# ---------- Konto ----------
def load():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"cash": CFG["start_cash"], "trades": [], "open": {}, "mode": None}

def save(s):
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2, default=str)

def book(s, sym, r, qty):
    exit_px = round(r["exit"] * (1 - CFG["slippage"]), 2) if r["why"] != "target" else r["exit"]
    pnl = round((exit_px - r["entry"]) * qty, 2)
    s["cash"] = round(s["cash"] + pnl, 2)
    s["trades"].append({"sym": sym, "day": str(r["t_in"].date()), "in": str(r["t_in"].time()), "out": str(r["t_out"].time()),
                        "qty": qty, "entry": r["entry"], "stop": r["stop"], "target": r["target"], "exit": exit_px,
                        "why": r["why"], "pnl": pnl, "R": round((exit_px - r["entry"]) / (r["entry"] - r["stop"]), 2)})
    return pnl

def stats(s):
    t = s["trades"]; c = CFG
    wins = [x["pnl"] for x in t if x["pnl"] > 0]; losses = [-x["pnl"] for x in t if x["pnl"] <= 0]
    eq, peak, mdd = c["start_cash"], c["start_cash"], 0.0
    for x in t:
        eq += x["pnl"]; peak = max(peak, eq); mdd = max(mdd, (peak - eq) / peak)
    pf = (sum(wins) / sum(losses)) if losses and sum(losses) > 0 else (float("inf") if wins else 0.0)
    pnl = s["cash"] - c["start_cash"]
    st = {"trades": len(t), "pnl": round(pnl, 2), "return_pct": round(100 * pnl / c["start_cash"], 2),
          "win_rate": round(100 * len(wins) / len(t), 1) if t else 0, "profit_factor": round(pf, 2),
          "avg_R": round(sum(x["R"] for x in t) / len(t), 2) if t else 0, "max_dd_pct": round(100 * mdd, 2)}
    checks = [("Trades >= %d" % c["gate_min_trades"], len(t) >= c["gate_min_trades"]),
              ("Netto-Gewinn > 0", pnl > 0),
              ("Profit-Faktor >= %.1f" % c["gate_min_profit_factor"], pf >= c["gate_min_profit_factor"]),
              ("Max Drawdown <= %d%%" % (100 * c["gate_max_drawdown_pct"]), mdd <= c["gate_max_drawdown_pct"])]
    return st, checks

def report(s):
    st, checks = stats(s)
    print("\n=== Papierkonto (%s) ===" % (s.get("mode") or "-"))
    print("Kapital: $%.2f  (Start $%.0f)" % (s["cash"], CFG["start_cash"]))
    for k, v in st.items():
        print("  %-14s %s" % (k, v))
    print("\nProfitabilitäts-Gate:")
    for name, ok in checks:
        print("  [%s] %s" % ("x" if ok else " ", name))
    if all(ok for _, ok in checks):
        print("\n>> GATE BESTANDEN auf Papier. Der Bot geht trotzdem NICHT live –")
        print("   ob und wie du mit echtem Geld handelst, entscheidest du selbst.")
    else:
        print("\n>> Noch nicht profitabel genug – weiter Paper-Trading.")


# ---------- Alpaca (NUR Paper-Konto) ----------
ALPACA = "https://paper-api.alpaca.markets"   # fest verdrahtet: dieser Bot kann kein Live-Konto ansprechen

def alpaca_on():
    return bool(os.environ.get("APCA_API_KEY_ID") and os.environ.get("APCA_API_SECRET_KEY"))

def alpaca(method, path, body=None):
    req = urllib.request.Request(ALPACA + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"APCA-API-KEY-ID": os.environ["APCA_API_KEY_ID"],
                                          "APCA-API-SECRET-KEY": os.environ["APCA_API_SECRET_KEY"],
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode()
            return json.loads(txt) if txt else {}
    except urllib.error.HTTPError as e:
        print("  Alpaca-Fehler %s: %s" % (e.code, e.read().decode()[:200]))
        return None

def alpaca_bracket(sym, qty, stop, target):
    return alpaca("POST", "/v2/orders", {"symbol": sym, "qty": str(qty), "side": "buy", "type": "market",
                                         "time_in_force": "day", "order_class": "bracket",
                                         "take_profit": {"limit_price": "%.2f" % target},
                                         "stop_loss": {"stop_price": "%.2f" % stop}})

# ---------- Modi ----------
def cmd_backtest(a):
    s = {"cash": CFG["start_cash"], "trades": [], "open": {}, "mode": "backtest"}
    data = {}
    for sym in CFG["watchlist"]:
        data[sym] = by_day(fetch(sym, "60d"))
        time.sleep(0.5)
    run_backtest(s, data, a.skip_today)
    with open("paperbot_backtest.json", "w") as f:
        json.dump(s, f, indent=2, default=str)
    report(s)
    print("\n(Trades in paperbot_backtest.json. Backtest != Zukunft; Live-Papier-Gate zaehlt separat.)")

def run_backtest(s, data, skip_today=True, days=None):
    alld = sorted({d for v in data.values() for d in v})
    if skip_today: alld = alld[:-1]
    days = days or alld
    for d in days:
        sigs = []
        for sym, dd in data.items():
            if d in dd:
                prev = [x for x in dd if x < d]
                r = simulate_day(dd[d], prev_close=dd[max(prev)][-1]["c"] if prev else None)
                if r and r["exit"] is not None:
                    sigs.append((r["t_in"], sym, r))
        day_loss = 0.0
        for _, sym, r in sorted(sigs, key=lambda x: x[0])[:CFG["max_trades_per_day"]]:
            if day_loss >= CFG["start_cash"] * CFG["daily_loss_limit_pct"]:
                break
            qty = size(s["cash"], s["cash"], r["entry"], r["stop"])
            if qty:
                p = book(s, sym, r, qty)
                day_loss += max(0, -p)
    return s

def cmd_run(a):
    s = load(); s["mode"] = "live-paper"
    print("Paper-Bot läuft. Strg+C zum Beenden. Watchlist:", ", ".join(CFG["watchlist"]))
    print("Alpaca-Paper:", "AN (Orders gehen an paper-api.alpaca.markets)" if alpaca_on() else "aus (nur interne Simulation)")
    done_today = set()
    u0 = dt.datetime.utcnow(); started = u0 + dt.timedelta(hours=ny_offset(u0))
    while True:
        u = dt.datetime.utcnow(); now = u + dt.timedelta(hours=ny_offset(u))
        if a.until and now.time() >= hhmm(a.until): break
        if now.weekday() >= 5 or now.time() < dt.time(9, 45) or now.time() > dt.time(16, 5):
            print("%s  Markt zu – warte..." % now.strftime("%a %H:%M"))
            if a.once or now.weekday() >= 5 or now.time() > dt.time(16, 5): break
            time.sleep(60); continue
        today = str(now.date())
        taken = [t for t in s["trades"] if t["day"] == today]
        for sym in CFG["watchlist"]:
            key = today + sym
            if key in done_today:
                continue
            bars = by_day(fetch(sym, "1d")).get(now.date(), [])
            r = simulate_day(bars, now=now)
            if not r:
                continue
            if r["t_in"] + dt.timedelta(minutes=5) < started - dt.timedelta(minutes=2) and sym not in s["open"]:
                done_today.add(key); continue   # Signal lag vor dem Bot-Start: nicht nachtraeglich buchen
            if r["exit"] is None and sym not in s["open"] and alpaca_on() and len(taken) + len(s["open"]) < CFG["max_trades_per_day"]:
                acct = alpaca("GET", "/v2/account") or {}
                eq = float(acct.get("equity", s["cash"]))
                q = size(float(acct.get("cash", eq)), eq, r["entry"], r["stop"])
                if q and alpaca_bracket(sym, q, r["stop"], r["target"]):
                    print("%s  ALPACA PAPER: Kauf %d %s, Stop %.2f, Ziel %.2f" % (now.strftime("%H:%M"), q, sym, r["stop"], r["target"]))
            if r["exit"] is None:
                print("%s  %s offen: entry %.2f stop %.2f ziel %.2f" % (now.strftime("%H:%M"), sym, r["entry"], r["stop"], r["target"]))
                s["open"][sym] = {"entry": r["entry"], "stop": r["stop"], "target": r["target"]}
                continue
            if len(taken) >= CFG["max_trades_per_day"] and sym not in s["open"]:
                done_today.add(key); continue
            qty = size(s["cash"], s["cash"], r["entry"], r["stop"])
            if qty:
                p = book(s, sym, r, qty); taken.append(s["trades"][-1])
                print("%s  %s %s  qty %d  P&L $%.2f" % (now.strftime("%H:%M"), sym, r["why"], qty, p))
            s["open"].pop(sym, None); done_today.add(key)
            time.sleep(0.3)
        if alpaca_on() and now.time() >= hhmm(CFG["flat_by"]) and s.get("flat_day") != today:
            alpaca("DELETE", "/v2/orders"); alpaca("DELETE", "/v2/positions")
            s["flat_day"] = today
            print("%s  ALPACA PAPER: alles glattgestellt" % now.strftime("%H:%M"))
        save(s)
        if a.once or (a.until and now.time() >= hhmm(a.until)): break
        time.sleep(60)
    save(s); report(s)

def cmd_flat(a):
    s = load(); u = dt.datetime.utcnow(); now = u + dt.timedelta(hours=ny_offset(u))
    if not alpaca_on():
        print("Keine Alpaca-Keys."); return
    if not (dt.time(15, 0) <= now.time() <= dt.time(16, 0)) and not a.force:
        print("%s NY: nicht im Glattstell-Fenster (15:00-16:00), nichts getan." % now.strftime("%H:%M")); return
    alpaca("DELETE", "/v2/orders"); alpaca("DELETE", "/v2/positions")
    s["flat_day"] = str(now.date()); save(s)
    print("%s NY: Alpaca-Paper glattgestellt." % now.strftime("%H:%M"))

def cmd_status(a):
    report(load())
    if alpaca_on():
        acct = alpaca("GET", "/v2/account") or {}
        print("\nAlpaca-Paper-Konto: Equity $%s, Cash $%s" % (acct.get("equity"), acct.get("cash")))
        for p in alpaca("GET", "/v2/positions") or []:
            print("  %s %s Stk, unreal. P&L $%s" % (p["symbol"], p["qty"], p["unrealized_pl"]))

def main():
    ap = argparse.ArgumentParser(description="Paper-Trading-Bot (ORB). Handelt nie live.")
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("backtest"); b.add_argument("--skip-today", action="store_true", default=True)
    r = sp.add_parser("run"); r.add_argument("--once", action="store_true")
    r.add_argument("--until", help="beenden um diese NY-Zeit (HH:MM)")
    f = sp.add_parser("flat"); f.add_argument("--force", action="store_true")
    sp.add_parser("status")
    a = ap.parse_args()
    {"backtest": cmd_backtest, "run": cmd_run, "flat": cmd_flat, "status": cmd_status}[a.cmd](a)

if __name__ == "__main__":
    main()
