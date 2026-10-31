"""Risk model: plain logistic regression (explainable, well-calibrated on 2k rows). No LLM here."""
import pickle, os
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

CAT = ["val_bin", "city", "utm", "courier"]
NUM = ["addr_score", "addr_junk", "name_junk", "phone_bad", "pin_missing", "is_new",
       "prior_rto", "num_items", "high_value"]
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "model.pkl")


def make_pipe():
    pre = ColumnTransformer([("c", OneHotEncoder(handle_unknown="ignore"), CAT),
                             ("n", StandardScaler(), NUM)])
    return Pipeline([("pre", pre), ("lr", LogisticRegression(C=0.5, max_iter=2000))])


def out_of_fold(X, y, seed=7):
    """Honest predictions: each order is scored by a model that never saw it."""
    cv = StratifiedKFold(5, shuffle=True, random_state=seed)
    p = cross_val_predict(make_pipe(), X, y, cv=cv, method="predict_proba")[:, 1]
    return p, roc_auc_score(y, p)


def train_and_save(X, y, df):
    pipe = make_pipe().fit(X, y)
    city_rate = df.groupby("city")["rto"].agg(["mean", "count"]).to_dict("index")
    pickle.dump({"pipe": pipe, "city_rate": city_rate, "base_rate": float(y.mean())}, open(MODEL_PATH, "wb"))
    return pipe


def load():
    return pickle.load(open(MODEL_PATH, "rb"))
