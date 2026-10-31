"""Cleaning + simple rule-based features. Plain code, no LLM (cheap, fast, testable)."""
import re
import pandas as pd

JUNK_NAMES = {"na", "asdf", "aaa", "test", "abc", "xyz", "qwerty", "name", "none", "n/a"}
JUNK_ADDR = {".", "xyz", "home", "call me", "na", "test", "asdf", "abc", "address", "-"}
LANDMARK = re.compile(r"(near|opp|ke paas|ke saamne|ke peeche|ke baad|se left|se right|chowk|mandir|school|bank|station)", re.I)
HAS_NUMBER = re.compile(r"\d")


def clean_phone(p):
    d = re.sub(r"\D", "", str(p))
    if len(d) == 12 and d.startswith("91"):
        d = d[2:]
    return d


def load_clean(path, for_training=True):
    df = pd.read_csv(path, dtype={"phone": str})
    df = df.drop_duplicates()                       # 30 exact duplicate rows in the sample
    df["final_status"] = df["final_status"].astype(str).str.strip().str.upper()
    if for_training:
        df = df[df["final_status"].isin(["DELIVERED", "RTO"])]   # drop IN_TRANSIT (outcome unknown)
        df = df[df["order_value"] > 0]                           # 3 zero-value rows
    df["rto"] = (df["final_status"] == "RTO").astype(int)
    df["order_datetime"] = pd.to_datetime(df["order_datetime"])
    return df.reset_index(drop=True)


def name_is_junk(name):
    n = str(name).strip().lower()
    if n in JUNK_NAMES or len(n) < 3:
        return True
    if re.fullmatch(r"(.)\1+", n):                  # aaa, bbb
        return True
    return not re.search(r"[aeiou]", n)             # no vowels -> keyboard mash


def address_score_rules(addr, city=""):
    """0 (junk) .. 1 (complete). Fast rule-based score; the LLM refines it when enabled."""
    a = str(addr).strip().lower()
    if a in JUNK_ADDR or a == str(city).strip().lower() or len(a) < 8:
        return 0.0
    s = 0.4
    if HAS_NUMBER.search(a): s += 0.3          # house / flat number
    if LANDMARK.search(a): s += 0.2
    if len(a) >= 25: s += 0.1
    return min(s, 1.0)


def build_features(df, addr_scores=None):
    """addr_scores: optional Series from the LLM (overrides the rule score where present)."""
    X = pd.DataFrame(index=df.index)
    rule = [address_score_rules(a, c) for a, c in zip(df["address"], df["city"].fillna(""))]
    X["addr_score"] = pd.Series(rule, index=df.index)
    if addr_scores is not None:
        X["addr_score"] = addr_scores.reindex(df.index).fillna(X["addr_score"])
    X["addr_junk"] = (X["addr_score"] < 0.3).astype(int)
    X["name_junk"] = df["customer_name"].map(name_is_junk).astype(int)
    X["phone_bad"] = (df["phone"].map(clean_phone).str.len() != 10).astype(int)
    X["pin_missing"] = df["pincode"].isna().astype(int)
    X["is_new"] = (df["customer_prior_orders"] == 0).astype(int)
    X["prior_rto"] = df["customer_prior_rto"].clip(upper=2)
    X["num_items"] = df["num_items"]
    X["high_value"] = (df["order_value"] > 1999).astype(int)
    X["val_bin"] = pd.cut(df["order_value"], [-1, 399, 599, 899, 1299, 1999, 1e9],
                          labels=["v0", "v1", "v2", "v3", "v4", "v5"]).astype(str)
    X["city"] = df["city"].fillna("unknown")
    X["utm"] = df["utm_source"]
    X["courier"] = df["courier"]
    return X