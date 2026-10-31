"""Run:  python app.py   then open http://localhost:5000
 /            -> founder dashboard         /chat   -> WhatsApp simulator
 POST /api/decide  (JSON order)  -> action + reason     (the 'decision engine' API)"""
import uuid
import pandas as pd
from flask import Flask, jsonify, render_template, request
from src import decide as D, model as M
from src.whatsapp import Conversation

app = Flask(__name__)
CONVOS = {}


def get_bundle():
    return M.load()


@app.route("/")
def dashboard():
    cfg = D.load_cfg()
    df = pd.read_csv("data/decisions.csv", parse_dates=["order_datetime"])
    dates = sorted(df.order_datetime.dt.date.unique())
    chosen = request.args.get("date") or str(dates[-1])          # default = latest day in the data ("yesterday")
    day = df[df.order_datetime.dt.date.astype(str) == chosen]
    order = ["SHIP", "NUDGE", "CONFIRM", "HOLD"]
    counts = {a: int((day.action == a).sum()) for a in order}
    saved, lost = float(day.saved.sum()), float(day.lost.sum())
    month = df[df.order_datetime >= df.order_datetime.max() - pd.Timedelta(days=30)]
    return render_template("dashboard.html", chosen=chosen, dates=dates[-14:], counts=counts, labels=D.LABEL,
                           saved=saved, lost=lost, net=saved - lost, n=len(day), cfg=cfg,
                           mnet=float(month.saved.sum() - month.lost.sum()), mn=len(month),
                           rows=day.sort_values("risk", ascending=False).head(25).to_dict("records"))


@app.route("/api/decide", methods=["POST"])
def api_decide():
    return jsonify(D.decide_one(request.get_json(), get_bundle(), D.load_cfg()))


@app.route("/chat")
def chat():
    return render_template("chat.html")


@app.route("/api/wa/start", methods=["POST"])
def wa_start():
    o = request.get_json()
    r = D.decide_one(o, get_bundle(), D.load_cfg())
    if r["action"] not in ("CONFIRM", "NUDGE"):
        return jsonify({"decision": r, "conversation": None})
    c = Conversation(order=o, kind=r["action"], discount=max(r["discount"], 20),
                     first_time=o.get("customer_prior_orders", 0) == 0).start()
    cid = uuid.uuid4().hex[:8]; CONVOS[cid] = c
    return jsonify({"decision": r, "id": cid, "state": c.state, "log": c.log})


@app.route("/api/wa/reply", methods=["POST"])
def wa_reply():
    j = request.get_json(); c = CONVOS[j["id"]]; c.reply(j["text"])
    return jsonify({"state": c.state, "log": c.log})


@app.route("/api/wa/tick", methods=["POST"])
def wa_tick():
    j = request.get_json(); c = CONVOS[j["id"]]; c.tick(float(j["hours"]))
    return jsonify({"state": c.state, "log": c.log, "hours": c.hours})


if __name__ == "__main__":
    app.run(debug=True)
