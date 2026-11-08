#!/usr/bin/env python3
"""Paper-Trading-Bot (nur Alpaca-PAPER-Konto, nie echtes Geld).

Aktive Strategie: Hedgefonds-Mix aus dem Strategie-Labor (seit 2026-11-09), vier Teile:
  nasdaq-3x     35 %  ruhig (Vola20 < 1,2 x Jahresschnitt) UND QQQ ueber 200-Tage-Schnitt -> TQQQ, sonst IEF
  sp500-ibs-3x  25 %  IBS-Ruecksetzer auf den S&P 500 (Schluss im unteren 15 % der Tagesspanne,
                      raus ueber dem Vortageshoch) -> UPRO, sonst Cash
  sp500-wr-3x   25 %  Williams-%R(10) < -90 im Aufwaertstrend (ueber 200-Tage-Schnitt), raus bei > -30
                      -> UPRO, sonst Cash
  gold-2x       15 %  GLD ueber 200-Tage-Schnitt -> UGL, sonst Cash
Signale aus dem Tagesschluss (Yahoo, dividendenbereinigt), Orders am naechsten Handelstag um 9:31 New York.
    python paperbot.py mix --dry       # Signale und geplante Orders anzeigen, nichts handeln
    python paperbot.py mix             # jetzt pruefen und handeln (nur bei offener Boerse)
    python paperbot.py status          # Konto, Positionen, Teile
    python paperbot.py bericht --force # Wochenbericht bot_bericht.md schreiben

Fruehere Strategien (abgeschaltet): Vola-Regime 1x+2x (27.10.-8.11.2026), Opening-Range-Breakout (Daytrading).
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
    "orb_aktiv": False,        # Daytrading (Opening-Range-Breakout): im Strategie-Labor durchgefallen -> aus
    "mix": {                   # Hedgefonds-Mix: aktiv seit 2026-11-09
        "aktiv": True, "start": "2026-11-09",
        "teile": {
            "nasdaq-3x":    {"anteil": 0.35, "regel": "vola+trend", "signal": "QQQ", "an": "TQQQ", "aus": "IEF"},
            "sp500-ibs-3x": {"anteil": 0.25, "regel": "ibs", "signal": "SPY", "an": "UPRO", "aus": "CASH"},
            "sp500-wr-3x":  {"anteil": 0.25, "regel": "williams", "signal": "SPY", "an": "UPRO", "aus": "CASH"},
            "gold-2x":      {"anteil": 0.15, "regel": "trend200", "signal": "GLD", "an": "UGL", "aus": "CASH"},
        },
    },
    "swing": {                 # Vola-Regime 1x + 2x: abgeschaltet seit 2026-11-09
        "aktiv": False, "signal": "QQQ", "k": 1.2, "vol_n": 20, "avg_n": 252, "ausweich": "IEF",
        "teile": {"vola-1x": {"anteil": 0.5, "ruhig": "QQQ"}, "vola-2x": {"anteil": 0.5, "ruhig": "QLD"}},
    },
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
            flat_orb()
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
    flat_orb()
    s["flat_day"] = str(now.date()); save(s)
    print("%s NY: Alpaca-Paper glattgestellt." % now.strftime("%H:%M"))

def ny_now():
    u = dt.datetime.utcnow(); return u + dt.timedelta(hours=ny_offset(u))

# ---------- ORB-Positionen (nur Watchlist-Aktien, nie die Vola-Regime-Positionen) ----------
def flat_orb():
    wl = set(CFG["watchlist"])
    for o in alpaca("GET", "/v2/orders?status=open&limit=500") or []:
        if o.get("symbol") in wl:
            alpaca("DELETE", "/v2/orders/%s" % o["id"])
    for p in alpaca("GET", "/v2/positions") or []:
        if p.get("symbol") in wl:
            alpaca("DELETE", "/v2/positions/%s" % p["symbol"])
            print("  ORB-Position %s geschlossen" % p["symbol"])

# ---------- Vola-Regime (Swing) ----------
def daily_closes(sym, rng="2y"):
    """Dividendenbereinigte Tagesschlusskurse von Yahoo, ohne den laufenden Handelstag."""
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (sym, rng)
    err = None
    for host in ("query2", "query1"):
        try:
            req = urllib.request.Request(url.replace("query2", host), headers={"User-Agent": "Mozilla/5.0 paperbot"})
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            adj = res["indicators"]["adjclose"][0]["adjclose"]
            today = str(ny_now().date())
            out = []
            for ts, c in zip(res["timestamp"], adj):
                d = str(ny(ts).date())
                if c is not None and d < today:
                    out.append((d, c))
            return out
        except Exception as e:
            err = e
            time.sleep(3)
    raise RuntimeError("Yahoo-Tageskurse %s nicht ladbar: %s" % (sym, err))

def vola_signal():
    """Wie im Strategie-Labor: Vola = Standardabweichung der letzten 20 Log-Renditen x Wurzel(252);
    ruhig, wenn Vola < k x Durchschnitt der letzten 252 Vola-Werte."""
    import math
    c = CFG["swing"]
    closes = daily_closes(c["signal"])
    px = [v for _, v in closes]
    rets = [math.log(px[i] / px[i - 1]) for i in range(1, len(px))]
    n, m = c["vol_n"], c["avg_n"]
    vols = []
    for i in range(n, len(rets) + 1):
        w = rets[i - n:i]
        mu = sum(w) / n
        vols.append(math.sqrt(max(0.0, sum(x * x for x in w) / n - mu * mu)) * math.sqrt(252))
    if len(vols) < m:
        raise RuntimeError("zu wenige Kurse fuer das Signal")
    vol, avg = vols[-1], sum(vols[-m:]) / m
    ruhig = vol < c["k"] * avg
    return ruhig, {"datum": closes[-1][0], "vola20": round(vol, 4), "schnitt252": round(avg, 4),
                   "grenze": round(c["k"] * avg, 4), "ruhig": ruhig}

def wait_fill(order, sekunden=600):
    """Wartet bis zu 10 Minuten auf die Ausfuehrung. Gibt (Order, abgeschlossen) zurueck.
    abgeschlossen=False heisst: Order noch offen -> beim naechsten Lauf nachpruefen, NICHT neu kaufen."""
    if not order or "id" not in order:
        return None, True
    o = order
    for _ in range(sekunden // 5):
        o = alpaca("GET", "/v2/orders/%s" % order["id"]) or o
        st = o.get("status")
        if st == "filled":
            return o, True
        if st in ("canceled", "expired", "rejected", "done_for_day"):
            print("  Order %s %s: %s" % (o.get("symbol"), o.get("side"), st))
            return o, True
        time.sleep(5)
    print("  Order %s %s nach %d s noch offen (Status %s) -> wird beim naechsten Lauf nachgeprueft"
          % (o.get("symbol"), o.get("side"), sekunden, o.get("status")))
    return o, False

def swing_syms():
    c = CFG["swing"]
    return {p["ruhig"] for p in c["teile"].values()} | {c["ausweich"]}

def swing_reconcile(s, dry=False):
    """Gleicht den gespeicherten Stand mit dem echten Alpaca-Konto ab:
    1) offene Orders aus frueheren Laeufen nachtragen, 2) Ueberschuss (z. B. Doppelkauf) verkaufen,
    3) fehlende Stuecke im Stand korrigieren."""
    st = s.setdefault("swing", {})
    for name, v in st.items():
        oid = v.get("offene_order")
        if not oid:
            continue
        o = alpaca("GET", "/v2/orders/%s" % oid) or {}
        if o.get("status") == "filled":
            if o.get("side") == "buy":
                v.update(sym=o["symbol"], qty=o["filled_qty"], preis=float(o["filled_avg_price"]))
            print("  Abgleich: offene Order fuer %s inzwischen ausgefuehrt (%s %s Stk)" % (name, o.get("symbol"), o.get("filled_qty")))
            v.pop("offene_order", None)
        elif o.get("status") in ("canceled", "expired", "rejected", "done_for_day"):
            print("  Abgleich: offene Order fuer %s wurde %s" % (name, o.get("status")))
            v.pop("offene_order", None)
        else:
            print("  Abgleich: Order fuer %s noch offen (%s) -> heute keine weiteren Orders fuer diesen Teil" % (name, o.get("status")))
    if any(v.get("offene_order") for v in st.values()):
        return
    pos = {p["symbol"]: float(p["qty"]) for p in alpaca("GET", "/v2/positions") or []}
    for sym in sorted(swing_syms()):
        parts = [v for v in st.values() if v.get("sym") == sym]
        need = sum(float(v.get("qty") or 0) for v in parts)
        have = pos.get(sym, 0.0)
        diff = round(have - need, 9)
        if diff > 0.001:
            print("  Abgleich: %.6f %s mehr im Konto als in den Strategien (z. B. Doppelkauf) -> Ueberschuss verkaufen" % (diff, sym))
            if not dry:
                o, fertig = wait_fill(market_order(sym, "sell", qty=diff))
                if o and o.get("status") == "filled":
                    s.setdefault("swing_log", []).append({"tag": str(ny_now().date()), "teil": "abgleich", "von": sym,
                                                          "nach": "Cash", "qty": o["filled_qty"],
                                                          "preis": float(o["filled_avg_price"]), "grund": "Ueberschuss"})
        elif diff < -0.001 and need > 0:
            print("  Abgleich: %.6f %s fehlen im Konto -> Stand wird an das Konto angepasst" % (-diff, sym))
            if not dry:
                for v in parts:
                    v["qty"] = "%.9f" % (float(v["qty"]) * have / need)

def market_order(sym, side, qty=None, notional=None):
    body = {"symbol": sym, "side": side, "type": "market", "time_in_force": "day"}
    if qty is not None:
        body["qty"] = str(qty)
    else:
        body["notional"] = "%.2f" % notional
    return alpaca("POST", "/v2/orders", body)

def swing_rebalance(s, dry=False):
    c = CFG["swing"]
    ruhig, info = vola_signal()
    print("Vola-Regime Signal (Schluss %s): Vola20 %.1f %% | Grenze %.1f %% (1,2 x Jahresschnitt %.1f %%) -> %s"
          % (info["datum"], 100 * info["vola20"], 100 * info["grenze"], 100 * info["schnitt252"],
             "RUHIG: Nasdaq halten" if ruhig else "UNRUHIG: Anleihen (IEF)"))
    st = s.setdefault("swing", {})
    log = s.setdefault("swing_log", [])
    today = str(ny_now().date())
    if alpaca_on():
        swing_reconcile(s, dry=dry)
    for name, part in c["teile"].items():
        target = part["ruhig"] if ruhig else c["ausweich"]
        cur = st.get(name)
        if cur and cur.get("offene_order"):
            print("  %s: wartet noch auf offene Order -> nichts tun" % name)
            continue
        if cur and cur.get("sym") == target and float(cur.get("qty") or 0) > 0:
            print("  %s: bleibt in %s (%.4f Stk)" % (name, target, float(cur["qty"])))
            continue
        held = cur and float(cur.get("qty") or 0) > 0
        budget_info = ("Erloes aus %s" % cur["sym"]) if held else ("%.0f %% des Kontos" % (100 * part["anteil"]))
        if dry or not alpaca_on():
            print("  %s: wuerde %s -> %s wechseln (%s)" % (name, cur["sym"] if held else "Cash", target, budget_info))
            continue
        proceeds = None
        if held:
            o, fertig = wait_fill(market_order(cur["sym"], "sell", qty=cur["qty"]))
            if not fertig:
                cur["offene_order"] = o["id"]
                continue
            if not o or o.get("status") != "filled":
                print("  %s: Verkauf %s fehlgeschlagen -> kein Kauf" % (name, cur["sym"]))
                continue
            proceeds = float(o["filled_qty"]) * float(o["filled_avg_price"])
            log.append({"tag": today, "teil": name, "von": cur["sym"], "nach": "Cash", "qty": o["filled_qty"],
                        "preis": float(o["filled_avg_price"]), "signal": info})
            cur.update(qty="0")
        acct = alpaca("GET", "/v2/account") or {}
        equity, cash = float(acct.get("equity") or 0), float(acct.get("cash") or 0)
        budget = proceeds if proceeds else equity * part["anteil"]
        budget = min(budget, cash - 50.0)              # nie auf Kredit (Margin) kaufen
        if budget < 100:
            print("  %s: zu wenig Cash ($%.2f) -> kein Kauf" % (name, cash))
            continue
        base = {"start_wert": cur.get("start_wert") if cur else round(budget, 2),
                "start": cur.get("start", today) if cur else today}
        o, fertig = wait_fill(market_order(target, "buy", notional=round(budget * 0.995, 2)))
        if not fertig:
            st[name] = dict(base, sym=target, qty="0", seit=today, offene_order=o["id"])
            continue
        if not o or o.get("status") != "filled":
            st[name] = dict(base, sym="CASH", qty="0", seit=today)
            print("  %s: Kauf %s fehlgeschlagen -> vorerst Cash" % (name, target))
            continue
        st[name] = dict(base, sym=target, qty=o["filled_qty"], preis=float(o["filled_avg_price"]), seit=today)
        log.append({"tag": today, "teil": name, "von": cur["sym"] if cur else "Cash", "nach": target,
                    "qty": o["filled_qty"], "preis": float(o["filled_avg_price"]), "signal": info})
        print("  %s: -> %s, %s Stk zu %.2f" % (name, target, o["filled_qty"], float(o["filled_avg_price"])))
    s["swing_signal"] = info

def market_open():
    clk = alpaca("GET", "/v2/clock") or {}
    return bool(clk.get("is_open"))

def cmd_swing(a):
    s = load()
    if not a.dry and not alpaca_on():
        print("Keine Alpaca-Keys -> nur Anzeige.")
        a.dry = True
    if not a.dry and not market_open():
        print("Boerse geschlossen -> nur Anzeige (Orders erst bei offener Boerse).")
        a.dry = True
    swing_rebalance(s, dry=a.dry)
    if not a.dry:
        save(s)

# ---------- Push-Nachricht (optional) ----------
def notify(title, body):
    """Kurze Push-Nachricht ueber ntfy.sh, nur wenn das Secret NTFY_TOPIC gesetzt ist."""
    topic = os.environ.get("NTFY_TOPIC")
    if not topic or not body:
        return
    req = urllib.request.Request("https://ntfy.sh/" + topic, data=body.encode("utf-8"), method="POST",
                                 headers={"Title": title.encode("ascii", "ignore").decode(), "Tags": "robot"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print("  Push fehlgeschlagen: %s" % e)

# ---------- Hedgefonds-Mix ----------
def daily_ohlc(sym, rng="5y"):
    """Tageskerzen von Yahoo, dividendenbereinigt wie im Strategie-Labor, ohne den laufenden Handelstag."""
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (sym, rng)
    err = None
    for host in ("query2", "query1"):
        try:
            req = urllib.request.Request(url.replace("query2", host), headers={"User-Agent": "Mozilla/5.0 paperbot"})
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read())["chart"]["result"][0]
            q, adj = res["indicators"]["quote"][0], res["indicators"]["adjclose"][0]["adjclose"]
            today = str(ny_now().date())
            out = []
            for i, ts in enumerate(res["timestamp"]):
                o, h, l, c, a = q["open"][i], q["high"][i], q["low"][i], q["close"][i], adj[i]
                if c is None or a is None or c <= 0 or a <= 0:
                    continue
                d = str(ny(ts).date())
                if d >= today:
                    continue
                o = o if o and o > 0 else c
                h = max(h if h and h > 0 else c, o, c)
                l = min(l if l and l > 0 else c, o, c)
                f = a / c
                out.append((d, o * f, h * f, l * f, a))
            return out
        except Exception as e:
            err = e
            time.sleep(3)
    raise RuntimeError("Yahoo-Tageskerzen %s nicht ladbar: %s" % (sym, err))

def sig_series(regel, bars):
    """Signal je Tag (1 = investiert), genau wie im Strategie-Labor berechnet."""
    import math
    C = [b[4] for b in bars]
    H = [b[2] for b in bars]
    Lo = [b[3] for b in bars]
    n = len(C)
    S = [0] * n

    def sma(k, t):
        return sum(C[t - k + 1:t + 1]) / k if t >= k - 1 else None
    if regel == "vola+trend":
        rets = [None] + [math.log(C[i] / C[i - 1]) for i in range(1, n)]
        vol = [None] * n
        for t in range(20, n):
            w = rets[t - 19:t + 1]
            mu = sum(w) / 20
            vol[t] = math.sqrt(max(0.0, sum(x * x for x in w) / 20 - mu * mu)) * math.sqrt(252)
        for t in range(20 + 251, n):
            avg = sum(vol[t - 251:t + 1]) / 252
            m = sma(200, t)
            S[t] = 1 if vol[t] < 1.2 * avg and m is not None and C[t] > m else 0
    elif regel == "trend200":
        for t in range(199, n):
            S[t] = 1 if C[t] > sma(200, t) else 0
    elif regel == "ibs":
        inpos = False
        for t in range(1, n):
            rg = H[t] - Lo[t]
            ibs = (C[t] - Lo[t]) / rg if rg > 0 else 0.5
            if inpos:
                if C[t] > H[t - 1]:
                    inpos = False
            elif ibs < 0.15:
                inpos = True
            S[t] = 1 if inpos else 0
    elif regel == "williams":
        inpos = False
        for t in range(10, n):
            hh, ll = max(H[t - 9:t + 1]), min(Lo[t - 9:t + 1])
            wr = -100.0 * (hh - C[t]) / (hh - ll) if hh > ll else -50.0
            m = sma(200, t)
            if inpos:
                if wr > -30:
                    inpos = False
            elif wr < -90 and m is not None and C[t] > m:
                inpos = True
            S[t] = 1 if inpos else 0
    else:
        raise ValueError(regel)
    return S

def mix_targets():
    cache, out = {}, {}
    for name, t in CFG["mix"]["teile"].items():
        if t["signal"] not in cache:
            cache[t["signal"]] = daily_ohlc(t["signal"])
        bars = cache[t["signal"]]
        an = bool(sig_series(t["regel"], bars)[-1])
        out[name] = {"an": an, "sym": t["an"] if an else t["aus"], "datum": bars[-1][0]}
    return out

def mix_syms():
    syms = set(swing_syms())                         # Reste der frueheren Vola-Regime-Teile
    for t in CFG["mix"]["teile"].values():
        syms |= {t["an"], t["aus"]}
    syms.discard("CASH")
    return syms

def mix_reconcile(s, dry=False):
    """Gleicht die Teile mit dem echten Konto ab: offene Orders nachtragen, Ueberschuss verkaufen
    (z. B. Reste der alten Strategie oder Doppelkaeufe), fehlende Stuecke im Stand korrigieren."""
    st = s.setdefault("teile", {})
    for name, v in st.items():
        oid = v.get("offene_order")
        if not oid:
            continue
        o = alpaca("GET", "/v2/orders/%s" % oid) or {}
        if o.get("status") == "filled":
            if o.get("side") == "buy":
                v.update(sym=o["symbol"], qty=o["filled_qty"], preis=float(o["filled_avg_price"]))
            else:
                v.update(sym="CASH", qty="0")
            v.pop("offene_order", None)
            print("  Abgleich: offene Order fuer %s ausgefuehrt" % name)
        elif o.get("status") in ("canceled", "expired", "rejected", "done_for_day"):
            v.pop("offene_order", None)
        else:
            print("  Abgleich: Order fuer %s noch offen (%s)" % (name, o.get("status")))
    if any(v.get("offene_order") for v in st.values()):
        return
    pos = {p["symbol"]: float(p["qty"]) for p in alpaca("GET", "/v2/positions") or []}
    for sym in sorted(mix_syms() | set(pos)):
        if sym not in mix_syms():
            continue
        parts = [v for v in st.values() if v.get("sym") == sym]
        need = sum(float(v.get("qty") or 0) for v in parts)
        diff = round(pos.get(sym, 0.0) - need, 9)
        if diff > 0.001:
            print("  Abgleich: %.6f %s im Konto, die keinem Teil gehoeren -> verkaufen" % (diff, sym))
            if not dry:
                o, fertig = wait_fill(market_order(sym, "sell", qty=diff))
                if o and o.get("status") == "filled":
                    s.setdefault("mix_log", []).append({"tag": str(ny_now().date()), "teil": "abgleich", "von": sym,
                                                        "nach": "Cash", "qty": o["filled_qty"],
                                                        "preis": float(o["filled_avg_price"])})
        elif diff < -0.001 and need > 0:
            print("  Abgleich: %.6f %s fehlen im Konto -> Stand wird angepasst" % (-diff, sym))
            if not dry:
                have = pos.get(sym, 0.0)
                for v in parts:
                    v["qty"] = "%.9f" % (float(v["qty"]) * have / need)

def mix_rebalance(s, dry=False):
    cfg = CFG["mix"]
    if "swing" in s and "swing_alt" not in s:          # einmaliger Umzug der alten Strategie
        s["swing_alt"] = s.pop("swing")
    st = s.setdefault("teile", {})
    log = s.setdefault("mix_log", [])
    today = str(ny_now().date())
    targets = mix_targets()
    print("Hedgefonds-Mix, Signale aus dem Schluss vom %s:" % next(iter(targets.values()))["datum"])
    for name, tg in targets.items():
        print("  %-13s %-4s -> soll halten: %s" % (name, "AN" if tg["an"] else "aus", tg["sym"]))
    if alpaca_on() and not st:
        # Start des Mix: Positionen, die schon im Konto liegen und ein Teil halten soll, werden diesem
        # Teil zugeordnet (bis zu seinem Zielanteil), statt sie zu verkaufen und neu zu kaufen.
        pos = {p["symbol"]: p for p in alpaca("GET", "/v2/positions") or []}
        equity = float((alpaca("GET", "/v2/account") or {}).get("equity") or 0)
        frei = {sym: float(p["qty"]) for sym, p in pos.items()}
        for name, tg in targets.items():
            p = pos.get(tg["sym"])
            if not p or frei.get(tg["sym"], 0) <= 0:
                continue
            qty = min(frei[tg["sym"]], cfg["teile"][name]["anteil"] * equity / float(p["current_price"]))
            frei[tg["sym"]] -= qty
            print("  Start: %s uebernimmt %.4f %s aus dem Bestand" % (name, qty, tg["sym"]))
            st[name] = {"sym": tg["sym"], "qty": "%.9f" % qty, "preis": float(p["current_price"]), "seit": today}
    if alpaca_on():
        mix_reconcile(s, dry=dry)
    # 1) zuerst verkaufen, was nicht mehr gehalten werden soll
    for name, tg in targets.items():
        cur = st.get(name) or {"sym": "CASH", "qty": "0"}
        if cur.get("offene_order"):
            print("  %s: wartet auf offene Order" % name); continue
        held = cur["sym"] != "CASH" and float(cur.get("qty") or 0) > 0
        if not held or cur["sym"] == tg["sym"]:
            continue
        if dry or not alpaca_on():
            print("  %s: wuerde %s verkaufen" % (name, cur["sym"])); continue
        o, fertig = wait_fill(market_order(cur["sym"], "sell", qty=cur["qty"]))
        if not fertig:
            cur["offene_order"] = o["id"]; st[name] = cur; continue
        if o and o.get("status") == "filled":
            log.append({"tag": today, "teil": name, "von": cur["sym"], "nach": "Cash", "qty": o["filled_qty"],
                        "preis": float(o["filled_avg_price"])})
            print("  %s: %s verkauft (%s Stk zu %.2f)" % (name, cur["sym"], o["filled_qty"], float(o["filled_avg_price"])))
            st[name] = {"sym": "CASH", "qty": "0", "seit": today}
    # 2) dann kaufen (Anteil x Kontowert, nie mehr als vorhandenes Cash)
    acct = (alpaca("GET", "/v2/account") or {}) if alpaca_on() else {}
    equity = float(acct.get("equity") or 0)
    for name, tg in targets.items():
        cur = st.get(name) or {"sym": "CASH", "qty": "0"}
        if cur.get("offene_order") or tg["sym"] == "CASH":
            continue
        if cur["sym"] == tg["sym"] and float(cur.get("qty") or 0) > 0:
            print("  %s: bleibt in %s" % (name, tg["sym"])); continue
        if dry or not alpaca_on():
            print("  %s: wuerde %s kaufen (%.0f %% des Kontos)" % (name, tg["sym"], 100 * cfg["teile"][name]["anteil"])); continue
        cash = float((alpaca("GET", "/v2/account") or {}).get("cash") or 0)
        budget = min(cfg["teile"][name]["anteil"] * equity, cash - 50.0)
        if budget < 100:
            print("  %s: zu wenig Cash ($%.2f) -> kein Kauf" % (name, cash)); continue
        o, fertig = wait_fill(market_order(tg["sym"], "buy", notional=round(budget * 0.995, 2)))
        if not fertig:
            st[name] = {"sym": tg["sym"], "qty": "0", "seit": today, "offene_order": o["id"]}; continue
        if not o or o.get("status") != "filled":
            print("  %s: Kauf %s fehlgeschlagen" % (name, tg["sym"])); continue
        st[name] = {"sym": tg["sym"], "qty": o["filled_qty"], "preis": float(o["filled_avg_price"]), "seit": today}
        log.append({"tag": today, "teil": name, "von": "Cash", "nach": tg["sym"], "qty": o["filled_qty"],
                    "preis": float(o["filled_avg_price"])})
        print("  %s: %s gekauft (%s Stk zu %.2f)" % (name, tg["sym"], o["filled_qty"], float(o["filled_avg_price"])))
    # 3) einmal im Monat: Teile, die stark vom Zielanteil abweichen, angleichen
    monat = today[:7]
    if not dry and alpaca_on() and s.get("ausgleich_monat") != monat:
        pos = {p["symbol"]: p for p in alpaca("GET", "/v2/positions") or []}
        acct = alpaca("GET", "/v2/account") or {}
        equity = float(acct.get("equity") or 0)
        for name, cur in st.items():
            p = pos.get(cur.get("sym"))
            if not p or cur.get("offene_order") or name not in cfg["teile"]:
                continue
            px = float(p["current_price"])
            wert, ziel = float(cur["qty"]) * px, cfg["teile"][name]["anteil"] * equity
            if wert > 1.25 * ziel:
                qty = round((wert - ziel) / px, 6)
                o, fertig = wait_fill(market_order(cur["sym"], "sell", qty=qty))
                if o and o.get("status") == "filled":
                    cur["qty"] = "%.9f" % (float(cur["qty"]) - float(o["filled_qty"]))
                    print("  Ausgleich %s: %s Stk %s verkauft" % (name, o["filled_qty"], cur["sym"]))
            elif wert < 0.8 * ziel:
                cash = float((alpaca("GET", "/v2/account") or {}).get("cash") or 0)
                nb = min(ziel - wert, cash - 50.0)
                if nb >= 100:
                    o, fertig = wait_fill(market_order(cur["sym"], "buy", notional=round(nb, 2)))
                    if o and o.get("status") == "filled":
                        cur["qty"] = "%.9f" % (float(cur["qty"]) + float(o["filled_qty"]))
                        print("  Ausgleich %s: %s Stk %s gekauft" % (name, o["filled_qty"], cur["sym"]))
        s["ausgleich_monat"] = monat
    s["mix_signal"] = targets
    heute = [e for e in log if e.get("tag") == today]
    if heute and not dry:
        zeilen = ["%s: %s -> %s (%s Stk zu %.2f)" % (e["teil"], e["von"], e["nach"], round(float(e["qty"]), 2), e["preis"])
                  for e in heute]
        notify("Paperbot hat gehandelt", "\n".join(zeilen))

def cmd_mix(a):
    s = load()
    if not a.dry and not alpaca_on():
        print("Keine Alpaca-Keys -> nur Anzeige."); a.dry = True
    if not a.dry and not market_open():
        print("Boerse geschlossen -> nur Anzeige (Orders erst bei offener Boerse)."); a.dry = True
    mix_rebalance(s, dry=a.dry)
    if not a.dry:
        save(s)

def cmd_auto(a):
    """Fuer GitHub Actions: startet zu beliebiger Zeit, entscheidet selbst, wartet selbst.
    Jeder Teil laeuft hoechstens einmal pro Tag (run_day / flat_day im Kontostand)."""
    s = load(); now = ny_now(); today = str(now.date())
    print("auto: NY %s" % now.strftime("%a %Y-%m-%d %H:%M"))
    if now.weekday() >= 5:
        print("Wochenende."); return
    if now.time() < dt.time(11, 5) and s.get("run_day") != today:
        if (CFG["mix"]["aktiv"] or CFG["swing"]["aktiv"]) and alpaca_on():
            while ny_now().time() < dt.time(9, 31):
                time.sleep(30)
            if market_open():
                if CFG["mix"]["aktiv"]:
                    mix_rebalance(s)
                else:
                    swing_rebalance(s)
            else:
                print("Boerse heute geschlossen (Feiertag) -> keine Orders.")
            save(s)
        if CFG["orb_aktiv"]:
            if alpaca_on() and ny_now().time() < dt.time(9, 30):
                flat_orb()                         # ORB-Reste vom Vortag
            a.until, a.once = "11:05", False
            cmd_run(a)
        s = load(); s["run_day"] = today; save(s); return
    if CFG["orb_aktiv"] and now.time() < dt.time(16, 0) and s.get("flat_day") != today:
        while ny_now().time() < dt.time(15, 45):
            time.sleep(60)
        a.force = True; cmd_flat(a); return
    print("Heute nichts mehr zu tun.")

# ---------- Wochenbericht ----------
BERICHT, WOCHEN = "bot_bericht.md", "bot_wochen.json"
START = {"datum": "2026-10-27", "basis": "2026-10-26", "equity": 100000.0}   # Start des Papierhandels

def _de(v, nach=1, plus=False):
    t = ("%+." if plus else "%.") + str(nach) + "f"
    return (t % v).replace(".", ",")

def _usd(v):
    return "$" + ("{:,.0f}".format(v)).replace(",", ".")

def _woche_zu_ende(last):
    """True, wenn der naechste Handelstag nach 'last' in einer neuen Kalenderwoche liegt."""
    d = dt.date.fromisoformat(last)
    cal = alpaca("GET", "/v2/calendar?start=%s&end=%s" % (last, (d + dt.timedelta(days=14)).isoformat())) or []
    nxt = [c["date"] for c in cal if c["date"] > last]
    return not nxt or dt.date.fromisoformat(nxt[0]).isocalendar()[:2] != d.isocalendar()[:2]

def cmd_bericht(a):
    if not alpaca_on():
        print("Keine Alpaca-Keys."); return
    spy, qqq = dict(daily_closes("SPY", "6mo")), dict(daily_closes("QQQ", "6mo"))
    last = max(spy)
    weeks = json.load(open(WOCHEN, encoding="utf-8")) if os.path.exists(WOCHEN) else []
    if weeks and weeks[-1]["datum"] >= last and not a.force:
        print("Bericht fuer %s gibt es schon." % last); return
    if a.nur_wochenende and not a.force and not _woche_zu_ende(last):
        print("%s ist nicht der letzte Handelstag der Woche - kein Bericht." % last); return
    acct = alpaca("GET", "/v2/account") or {}
    eq = float(acct.get("equity") or 0)
    pos = {p["symbol"]: p for p in alpaca("GET", "/v2/positions") or []}
    base = {"datum": START["basis"], "equity": START["equity"], "spy": spy[START["basis"]], "qqq": qqq[START["basis"]]}
    prev = weeks[-1] if weeks else base
    snap = {"datum": last, "equity": round(eq, 2), "spy": round(spy[last], 4), "qqq": round(qqq[last], 4)}
    weeks = [w for w in weeks if w["datum"] < last] + [snap]
    with open(WOCHEN, "w", encoding="utf-8") as f:
        json.dump(weeks, f, indent=1)
    ch = lambda new, old: 100 * (new / old - 1)
    ruhig, info = vola_signal()
    s = load()
    L = ["# Bot-Bericht: Woche bis %s" % dt.date.fromisoformat(last).strftime("%d.%m.%Y"), "",
         "Papiergeld (Alpaca Paper), keine Anlageberatung. Start des Papierhandels: %s. "
         "Strategie seit 09.11.2026: Hedgefonds-Mix aus 4 Teilen (35 %% Nasdaq-100 mit 3-fach-Hebel, nur bei ruhiger Börse "
         "im Aufwärtstrend, sonst Anleihen; je 25 %% zwei Rücksetzer-Strategien auf den S&P 500 mit 3-fach-Hebel; "
         "15 %% Gold mit 2-fach-Hebel im Aufwärtstrend). Davor (27.10.-06.11.): Vola-Regime auf den Nasdaq-100 (1x + 2x)." % START["datum"], "",
         "## Kontostand", "", "| | Stand | diese Woche | seit Start |", "|---|---|---|---|",
         "| **Bot (Konto)** | %s | %s %% | %s %% |" % (_usd(eq), _de(ch(eq, prev["equity"]), plus=True), _de(ch(eq, base["equity"]), plus=True)),
         "| S&P 500 halten (SPY) | %s | %s %% | %s %% |" % (_de(spy[last], 2), _de(ch(spy[last], prev["spy"]), plus=True), _de(ch(spy[last], base["spy"]), plus=True)),
         "| Nasdaq-100 halten (QQQ) | %s | %s %% | %s %% |" % (_de(qqq[last], 2), _de(ch(qqq[last], prev["qqq"]), plus=True), _de(ch(qqq[last], base["qqq"]), plus=True)),
         "", "## Die Teile", "", "| Teil | Zielanteil | hält gerade | Wert |", "|---|---|---|---|"]
    teile = s.get("teile") or {}
    for name, cfg_t in CFG["mix"]["teile"].items():
        v = teile.get(name) or {"sym": "CASH", "qty": "0"}
        p = pos.get(v.get("sym"))
        wert = float(v["qty"]) * float(p["current_price"]) if p else 0.0
        L.append("| %s | %s %% | %s | %s |" % (name, _de(100 * cfg_t["anteil"], 0), v.get("sym") if v.get("sym") != "CASH" else "Cash",
                                             _usd(wert) if wert else "-"))
    L.append("| Cash | | | %s |" % _usd(float(acct.get("cash") or 0)))
    L += ["", "## Signale für den nächsten Handelstag", "", "| Teil | Signal | soll halten |", "|---|---|---|"]
    for name, tg in mix_targets().items():
        L.append("| %s | %s | %s |" % (name, "an" if tg["an"] else "aus", "Cash" if tg["sym"] == "CASH" else tg["sym"]))
    L += ["", "Nasdaq-Teil: Schwankung der letzten 20 Tage %s %%, Grenze %s %% (1,2 x Jahresschnitt) -> %s." % (
              _de(100 * info["vola20"]), _de(100 * info["grenze"]), "ruhig" if ruhig else "unruhig"), ""]
    orders = alpaca("GET", "/v2/orders?status=closed&after=%sT23:59:59Z&limit=100&direction=asc" % prev["datum"]) or []
    filled = [o for o in orders if o.get("status") == "filled"]
    L += ["## Trades diese Woche", ""]
    if filled:
        L += ["| Datum | Aktion | Wert | Stück | Kurs |", "|---|---|---|---|---|"]
        for o in filled:
            q, px = float(o["filled_qty"]), float(o["filled_avg_price"])
            L.append("| %s | %s %s | %s | %s | %s |" % (o["filled_at"][:10], "Kauf" if o["side"] == "buy" else "Verkauf",
                                                     o["symbol"], _usd(q * px), _de(q, 2), _de(px, 2)))
    else:
        L.append("Keine Trades.")
    L += ["", "## Verlauf (Wochenschluss)", "", "| Woche bis | Bot | S&P 500 | Nasdaq-100 |", "|---|---|---|---|",
          "| Start (%s) | %s | 0,0 %% | 0,0 %% |" % (START["datum"], _usd(base["equity"]))]
    for w in weeks:
        L.append("| %s | %s (%s %%) | %s %% | %s %% |" % (w["datum"], _usd(w["equity"]), _de(ch(w["equity"], base["equity"]), plus=True),
                                                    _de(ch(w["spy"], base["spy"]), plus=True), _de(ch(w["qqq"], base["qqq"]), plus=True)))
    with open(BERICHT, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print("Bericht geschrieben: %s (Woche bis %s)" % (BERICHT, last))
    notify("Wochenbericht Paperbot", "Woche bis %s\nBot: %s %% (seit Start %s %%)\nS&P 500: %s %%\nNasdaq-100: %s %%" % (
        last, _de(ch(eq, prev["equity"]), plus=True), _de(ch(eq, base["equity"]), plus=True),
        _de(ch(spy[last], prev["spy"]), plus=True), _de(ch(qqq[last], prev["qqq"]), plus=True)))

def cmd_status(a):
    s = load()
    if CFG["orb_aktiv"] or s.get("trades"):
        report(s)
    if alpaca_on():
        acct = alpaca("GET", "/v2/account") or {}
        print("\nAlpaca-Paper-Konto: Equity $%s, Cash $%s" % (acct.get("equity"), acct.get("cash")))
        pos = {p["symbol"]: p for p in alpaca("GET", "/v2/positions") or []}
        for p in pos.values():
            print("  %s %s Stk, Wert $%s, unreal. P&L $%s" % (p["symbol"], p["qty"], p["market_value"], p["unrealized_pl"]))
        if s.get("teile"):
            print("\nHedgefonds-Mix (je Teil):")
            for name, v in s["teile"].items():
                p = pos.get(v.get("sym"))
                wert = float(v["qty"]) * float(p["current_price"]) if p else 0.0
                print("  %-13s %-5s Wert $%.2f%s" % (name, v.get("sym"), wert, " (offene Order)" if v.get("offene_order") else ""))
        st = s.get("swing", {})
        if st:
            print("\nVola-Regime (je Teil):")
            for name, v in st.items():
                p = pos.get(v.get("sym"))
                wert = float(v["qty"]) * float(p["current_price"]) if p else None
                if wert and v.get("start_wert"):
                    print("  %s: %s, Wert $%.2f, seit Start %+.2f %% (Start %s)" % (
                        name, v["sym"], wert, 100 * (wert / v["start_wert"] - 1), v.get("start")))
                else:
                    print("  %s: %s" % (name, v.get("sym")))
    if s.get("swing_signal"):
        print("Letztes Signal: %s" % s["swing_signal"])

def main():
    ap = argparse.ArgumentParser(description="Paper-Trading-Bot (Vola-Regime, nur Alpaca-Paper). Handelt nie live.")
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("backtest"); b.add_argument("--skip-today", action="store_true", default=True)
    r = sp.add_parser("run"); r.add_argument("--once", action="store_true")
    r.add_argument("--until", help="beenden um diese NY-Zeit (HH:MM)")
    f = sp.add_parser("flat"); f.add_argument("--force", action="store_true")
    w = sp.add_parser("swing"); w.add_argument("--dry", action="store_true", help="nur anzeigen, nichts handeln")
    mx = sp.add_parser("mix"); mx.add_argument("--dry", action="store_true", help="nur anzeigen, nichts handeln")
    br = sp.add_parser("bericht"); br.add_argument("--nur-wochenende", action="store_true"); br.add_argument("--force", action="store_true")
    sp.add_parser("status"); sp.add_parser("auto")
    a = ap.parse_args()
    {"backtest": cmd_backtest, "run": cmd_run, "flat": cmd_flat, "status": cmd_status, "auto": cmd_auto,
     "swing": cmd_swing, "mix": cmd_mix, "bericht": cmd_bericht}[a.cmd](a)

if __name__ == "__main__":
    main()
