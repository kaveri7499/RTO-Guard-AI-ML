"""Train the model, score every historical order with out-of-fold predictions,
apply the rules in config.yaml, and write data/decisions.csv (used by the dashboard).
Usage:  python backtest.py            (uses config.yaml thresholds)
        python backtest.py --tune     (also searches for the best thresholds in Rs)"""
import sys, itertools
import numpy as np
import pandas as pd
from src import features as F, model as M, decide as D, economics as eco

cfg = D.load_cfg()
df = F.load_clean("data/orders_sample.csv")
X = F.build_features(df)
y = df["rto"]
p, auc = M.out_of_fold(X, y)
M.train_and_save(X, y, df)
bundle = M.load()
print(f"Orders used: {len(df)} | RTO rate {y.mean():.1%} | out-of-fold AUC {auc:.3f}")


def evaluate(cfg_local, risk):
    res = D.decide_frame(df, pd.Series(risk, index=df.index), X, bundle, cfg_local)
    sv, ls = [], []
    for i in df.index:
        s, l = eco.action_value(res.at[i, "action"], int(y[i]), df.at[i, "order_value"],
                                bool(X.at[i, "is_new"]), cfg_local)
        sv.append(s); ls.append(l)
    res["saved"], res["lost"] = sv, ls
    return res


res = evaluate(cfg, p)
res.insert(0, "order_id", df["order_id"]); res.insert(1, "order_datetime", df["order_datetime"])
res["rto"] = y; res["order_value"] = df["order_value"]; res["is_new"] = X["is_new"]
res.to_csv("data/decisions.csv", index=False)

print("\nBucket counts and Rs impact (whole 6-month sample):")
g = res.groupby("action").agg(orders=("risk", "size"), actual_rto=("rto", "mean"),
                              saved=("saved", "sum"), lost=("lost", "sum")).round(2)
print(g.to_string())
print(f"TOTAL saved Rs {res.saved.sum():,.0f} | lost Rs {res.lost.sum():,.0f} | NET Rs {res.saved.sum()-res.lost.sum():,.0f}")

sep = res[res.order_datetime >= "2026-09-01"]
print(f"\nLast month (Sep 2026, {len(sep)} orders in sample): saved Rs {sep.saved.sum():,.0f} | "
      f"lost Rs {sep.lost.sum():,.0f} | NET Rs {sep.saved.sum()-sep.lost.sum():,.0f}")
print("Scaled to 3,000 orders/month x 55% COD = ~1,650 COD orders:",
      f"NET ~Rs {(sep.saved.sum()-sep.lost.sum())/len(sep)*1650:,.0f}/month")

print("\nBreak-even risk (ship COD loses money above this):")
for v in (349, 649, 1200, 2000):
    print(f"  order Rs {v}: {eco.breakeven_risk(v, cfg):.0%}   (RTO costs Rs {eco.rto_cost(cfg):.1f})")

# Two reference policies for the memo
def policy(name, fn):
    s = l = 0
    for i in df.index:
        a = fn(p[i], X.at[i, "is_new"])
        sv, ls = eco.action_value(a, int(y[i]), df.at[i, "order_value"], bool(X.at[i, "is_new"]), cfg)
        s += sv; l += ls
    print(f"  {name:38s} saved {s:>9,.0f} lost {l:>9,.0f} NET {s-l:>9,.0f}")
print("\nPolicy comparison (same orders, same assumptions):")
policy("Ops: cancel everything risk >= 40%", lambda r, n: "HOLD" if r >= .40 else "SHIP")
policy("Marketing: ship everything", lambda r, n: "SHIP")
policy("Confirm everything risk >= 25%", lambda r, n: "CONFIRM" if r >= .25 else "SHIP")
policy("Ours (config.yaml)", lambda r, n: D.bucket_for(r, bool(n), False, cfg))

if "--tune" in sys.argv:
    print("\nTuning thresholds (grid search, out-of-fold)...")
    best = []
    for a, b, c in itertools.product([.15, .2, .25, .3, .35], [.35, .4, .45, .5], [.6, .65, .7, .75, .8, .9]):
        if not (a < b < c): continue
        c2 = {**cfg, "thresholds": {"ship_below": a, "nudge_below": b, "confirm_below": c}}
        r2 = evaluate(c2, p)
        best.append((r2.saved.sum() - r2.lost.sum(), a, b, c))
    for net, a, b, c in sorted(best, reverse=True)[:5]:
        print(f"  ship<{a} nudge<{b} confirm<{c}  NET Rs {net:,.0f}")
