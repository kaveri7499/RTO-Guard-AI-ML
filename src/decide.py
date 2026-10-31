"""Decision engine: risk -> one of 4 actions + a plain-English reason. Thresholds live in config.yaml."""
import yaml, os
import pandas as pd
from .features import build_features
from . import economics as eco

CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
LABEL = {"SHIP": "Ship as-is", "NUDGE": "Nudge to prepaid",
         "CONFIRM": "Ship after confirmation", "HOLD": "Hold / cancel"}


def load_cfg():
    return yaml.safe_load(open(CFG_PATH))


def bucket_for(risk, row_is_new, both_junk, cfg):
    t = cfg["thresholds"]
    if risk < t["ship_below"]:
        a = "SHIP"
    elif risk < t["nudge_below"]:
        a = "NUDGE"
    elif risk < t["confirm_below"]:
        a = "CONFIRM"
    else:
        a = "HOLD"
    if a == "HOLD" and cfg["protect_first_time_customers"] and row_is_new and not both_junk:
        a = "CONFIRM"        # Marketing guard
    return a


def reasons(row, X, city_rate, base_rate):
    r = []
    if X["addr_junk"]:
        r.append(f"address looks incomplete/fake (\"{str(row['address'])[:25]}\")")
    if X["name_junk"]:
        r.append(f"name looks fake (\"{row['customer_name']}\")")
    if X["phone_bad"]:
        r.append("phone number is not a valid 10-digit number")
    cr = city_rate.get(row["city"])
    if cr and cr["count"] >= 20 and cr["mean"] >= base_rate + 0.12:
        r.append(f"{row['city']} had {cr['mean']*100:.0f}% returns on past COD orders")
    if row["customer_prior_rto"] >= 1:
        r.append(f"customer returned {int(row['customer_prior_rto'])} earlier order(s)")
    if X["high_value"]:
        r.append(f"large order (Rs {int(row['order_value'])})")
    if X["is_new"] and not r:
        r.append("first-time customer, nothing else unusual")
    if not r:
        r.append("no risk signals; repeat customer with good history" if not X["is_new"] else "no risk signals")
    return r


def decide_frame(df, risk, X, bundle, cfg):
    """Vectorised helper used by backtest/dashboard. Returns DataFrame with action, reason, discount."""
    out = pd.DataFrame(index=df.index)
    out["risk"] = risk
    acts, why, disc = [], [], []
    for i in df.index:
        both = bool(X.at[i, "addr_junk"] and X.at[i, "name_junk"])
        a = bucket_for(risk[i] if not hasattr(risk, "iloc") else risk.loc[i], bool(X.at[i, "is_new"]), both, cfg)
        rs = reasons(df.loc[i], X.loc[i], bundle["city_rate"], bundle["base_rate"])
        pr = risk[i] if not hasattr(risk, "iloc") else risk.loc[i]
        acts.append(a)
        why.append(f"Risk {pr*100:.0f}%: " + "; ".join(rs) + ".")
        disc.append(eco.prepaid_discount(df.at[i, "order_value"], pr, cfg) if a in ("NUDGE", "CONFIRM") else 0)
    out["action"], out["reason"], out["discount"] = acts, why, disc
    return out


def decide_one(order, bundle, cfg, llm_result=None):
    """order: dict of raw order fields (same names as the CSV). Returns dict with action/reason/risk."""
    from .llm_checks import check_order
    df = pd.DataFrame([order])
    chk = llm_result or check_order({"name": order["customer_name"], "address": order["address"],
                                     "city": order.get("city"), "state": order.get("state"),
                                     "pincode": order.get("pincode")})
    X = build_features(df, addr_scores=pd.Series([chk["address_score"]], index=df.index))
    if chk["name_fake"]:
        X["name_junk"] = 1
    risk = float(bundle["pipe"].predict_proba(X)[:, 1][0])
    res = decide_frame(df, pd.Series([risk], index=df.index), X, bundle, cfg).iloc[0]
    return {"action": res["action"], "label": LABEL[res["action"]], "risk": round(risk, 3),
            "reason": res["reason"], "discount": int(res["discount"]), "checked_by": chk["source"]}
