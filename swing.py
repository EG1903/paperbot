#!/usr/bin/env python3
"""Swing-Strategien auf Tageskursen, Backtest über ~20 Jahre (nur Standardbibliothek).

    python swing.py              # alle Strategien testen (Train bis 2015, Test ab 2016)
    python swing.py --refresh    # Kursdaten neu laden

Universum: ETFs (Index + Sektoren) – ETFs verschwinden nicht, daher kaum
Survivorship-Bias (anders als "heutige Top-Aktien").

Strategien (bekannte Standardregeln, NICHT auf diese Daten optimiert):
  rsi2   Mean Reversion (Connors): Kurs > SMA200 und RSI(2) < 10 -> Kauf zum Schluss,
         Verkauf wenn Schluss > SMA5. Max 5 Positionen à 20 %.
  mom    Momentum-Rotation: monatlich die 3 ETFs mit der besten 6-Monats-Rendite,
         nur wenn SPY > SMA200, sonst Cash.
  spy    Buy & Hold SPY (Vergleich).
Kosten: 0,05 % pro Kauf und Verkauf. Fills zum Tagesschluss.
"""
import json, os, pickle, sys, time, urllib.request, datetime as dt

UNIVERSE = ["SPY", "QQQ", "IWM", "DIA", "XLK", "XLF", "XLE", "XLV", "XLY", "XLP", "XLI", "XLU", "XLB"]
COST = 0.0005
START, SPLIT = "2004-01-01", "2016-01-01"
CACHE = "daily_cache.pkl"

def fetch(sym):
    url = "https://query2.finance.yahoo.com/v8/finance/chart/%s?period1=946684800&period2=%d&interval=1d&events=div,split" % (sym, int(time.time()))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 swing"})
    with urllib.request.urlopen(req, timeout=30) as r:
        res = json.loads(r.read())["chart"]["result"][0]
    adj = res["indicators"]["adjclose"][0]["adjclose"]   # dividenden-/split-bereinigt
    out = {}
    for t, c in zip(res["timestamp"], adj):
        if c:
            out[dt.datetime.utcfromtimestamp(t).strftime("%Y-%m-%d")] = c
    return out

def load(refresh=False):
    if os.path.exists(CACHE) and not refresh:
        return pickle.load(open(CACHE, "rb"))
    data = {}
    for s in UNIVERSE:
        data[s] = fetch(s); print("  %-4s %d Tage ab %s" % (s, len(data[s]), min(data[s]))); time.sleep(0.5)
    pickle.dump(data, open(CACHE, "wb"))
    return data

def sma(xs, n):
    return sum(xs[-n:]) / n if len(xs) >= n else None

def rsi(xs, n):
    if len(xs) <= n: return None
    g = l = 0.0
    for a, b in zip(xs[-n - 1:-1], xs[-n:]):
        d = b - a; g += max(d, 0); l += max(-d, 0)
    return 100.0 if l == 0 else 100 - 100 / (1 + g / l)

def backtest(data, strat, d0, d1):
    days = sorted(d for d in data["SPY"] if d0 <= d < d1)
    hist = {s: [] for s in data}
    for s in data:                       # Vorlauf für SMA200
        hist[s] = [data[s][d] for d in sorted(data[s]) if d < d0][-250:]
    cash, pos, eq_curve, trades = 1.0, {}, [], []
    last_month = None
    for d in days:
        px = {s: data[s][d] for s in data if d in data[s]}
        for s, p in px.items(): hist[s].append(p)
        equity = cash + sum(q * px.get(s, e) for s, (q, e) in pos.items())
        if strat == "spy":
            if not pos: pos["SPY"] = ((cash * (1 - COST)) / px["SPY"], px["SPY"]); cash = 0
        elif strat == "rsi2":
            for s in list(pos):
                if s in px and px[s] > sma(hist[s], 5):
                    q, e = pos.pop(s); cash += q * px[s] * (1 - COST); trades.append(px[s] / e - 1)
            cands = sorted((rsi(hist[s], 2), s) for s in px if s not in pos and len(hist[s]) >= 200
                           and px[s] > sma(hist[s], 200) and rsi(hist[s], 2) < 10)
            for _, s in cands:
                if len(pos) >= 5: break
                amt = min(cash, equity * 0.2)
                if amt < equity * 0.05: break
                pos[s] = (amt * (1 - COST) / px[s], px[s]); cash -= amt
        elif strat == "mom":
            if d[:7] != last_month:
                last_month = d[:7]
                for s in list(pos):
                    q, e = pos.pop(s); cash += q * px[s] * (1 - COST); trades.append(px[s] / e - 1)
                if px["SPY"] > sma(hist["SPY"], 200):
                    ranked = sorted(((hist[s][-1] / hist[s][-127] - 1, s) for s in px if len(hist[s]) > 127), reverse=True)[:3]
                    for _, s in ranked:
                        amt = cash / (3 - len(pos)) if len(pos) < 3 else 0
                        pos[s] = (amt * (1 - COST) / px[s], px[s]); cash -= amt
        equity = cash + sum(q * px.get(s, e) for s, (q, e) in pos.items())
        eq_curve.append(equity)
    return stats(eq_curve, trades, len(days))

def stats(eq, trades, n):
    years = n / 252
    cagr = eq[-1] ** (1 / years) - 1
    peak, mdd = eq[0], 0
    for e in eq: peak = max(peak, e); mdd = max(mdd, 1 - e / peak)
    rets = [b / a - 1 for a, b in zip(eq, eq[1:])]
    mu = sum(rets) / len(rets); sd = (sum((r - mu) ** 2 for r in rets) / len(rets)) ** 0.5
    wins = [t for t in trades if t > 0]; loss = [-t for t in trades if t <= 0]
    return {"CAGR %": round(100 * cagr, 1), "MaxDD %": round(100 * mdd, 1),
            "Sharpe": round(mu / sd * 252 ** 0.5, 2) if sd else 0,
            "Trades": len(trades), "Win %": round(100 * len(wins) / len(trades), 1) if trades else "-",
            "PF": round(sum(wins) / sum(loss), 2) if loss else "-", "Endwert x": round(eq[-1], 2)}

if __name__ == "__main__":
    import warnings; warnings.filterwarnings("ignore")
    data = load("--refresh" in sys.argv)
    today = max(data["SPY"])
    for name, a, b in [("TRAIN", START, SPLIT), ("TEST", SPLIT, "9999"), ("GESAMT", START, "9999")]:
        print("\n== %s %s .. %s ==" % (name, a, b if b != "9999" else today))
        print("%-6s" % "", "  ".join("%9s" % k for k in ["CAGR %", "MaxDD %", "Sharpe", "Trades", "Win %", "PF", "Endwert x"]))
        for s in ["rsi2", "mom", "spy"]:
            st = backtest(data, s, a, b)
            print("%-6s" % s, "  ".join("%9s" % v for v in st.values()))
