"""Sucht Parameter auf den ersten 2/3 der Tage (Train) und prüft sie auf dem letzten 1/3 (Test)."""
import itertools, json, os, sys, time, pickle
import paperbot as pb
WL = pb.CFG["watchlist"] + ["SPY","QQQ","PLTR","SMCI","MU","AVGO","SHOP","UBER","MSTR","HOOD"]
cache = "data_cache.pkl"
if os.path.exists(cache) and "--refresh" not in sys.argv:
    data = pickle.load(open(cache, "rb"))
else:
    data = {}
    for s in WL:
        data[s] = pb.by_day(pb.fetch(s, "60d")); time.sleep(0.5)
    pickle.dump(data, open(cache, "wb"))
days = sorted({d for v in data.values() for d in v})[:-1]
cut = len(days) * 2 // 3
train, test = days[:cut], days[cut:]
grid = dict(or_minutes=[5,15,30], target_r=[1.0,1.5,2.0,3.0], stop_mode=["mid","low"],
            min_volume_x=[0,1.0,1.5], trend_filter=[False,True], last_entry=["11:00","15:30"], max_range_pct=[1.0,0.02])
base = dict(pb.CFG)
def run(params, ds):
    pb.CFG.update(base); pb.CFG.update(params)
    s = {"cash": pb.CFG["start_cash"], "trades": [], "open": {}}
    pb.run_backtest(s, data, days=ds)
    return pb.stats(s)[0]
res = []
for vals in itertools.product(*grid.values()):
    p = dict(zip(grid, vals)); st = run(p, train)
    if st["trades"] >= 30: res.append((st["profit_factor"], p, st))
res.sort(key=lambda x: -x[0])
print("Train %s..%s (%d Tage), Test %s..%s (%d Tage)" % (train[0], train[-1], len(train), test[0], test[-1], len(test)))
out = []
for pf, p, st in res[:10]:
    t = run(p, test); out.append((p, st, t))
    print("TRAIN pf %.2f n %3d ret %5.2f%% | TEST pf %.2f n %3d ret %5.2f%% dd %.1f%% | %s" % (pf, st["trades"], st["return_pct"], t["profit_factor"], t["trades"], t["return_pct"], t["max_dd_pct"], p))
json.dump([{"params": p, "train": a, "test": b} for p, a, b in out], open("optimize_results.json","w"), indent=1)
