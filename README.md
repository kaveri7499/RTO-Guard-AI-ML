# RTO Guard – AI decision engine for COD orders

Decides for every new COD order: **Ship / Nudge to prepaid / Ship after confirmation / Hold-cancel**,
with a plain-English reason. Includes a WhatsApp flow mock and a founder dashboard.

## Run it in under 5 minutes
```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python backtest.py          # trains model, scores 1,984 clean orders, prints Rs impact, writes data/decisions.csv
python app.py               # open http://localhost:5000
```
* `/`      founder dashboard (pick a day; default = latest day in data)
* `/chat`  WhatsApp simulator (try "haan", "2", random text, or the +24h button)
* `POST /api/decide` with one order as JSON -> `{action, risk, reason, discount}`

Optional LLM (works fine without it, falls back to rules):
```bash
export ANTHROPIC_API_KEY=...   USE_LLM=1   # optionally LLM_MODEL=<model name>
```

## Change the rules without code
Open **`config.yaml`**. Change `thresholds` (risk cut-offs), `protect_first_time_customers`,
money facts, or assumptions. Restart `python app.py` (or re-run `python backtest.py`).

## Where AI is used – and where it is not
| Job | Tool | Why |
|---|---|---|
| Is the address complete/real? Hinglish landmarks ("Hanuman Mandir ke saamne") | **LLM** (`src/llm_checks.py`) | fuzzy language judgement; rules can't read Hinglish |
| Fake name ("asdf", "test") | rules first, LLM for the grey zone | obvious junk needs no AI |
| Risk of RTO | **Logistic regression** (`src/model.py`) | numbers + 2k rows: simple, explainable, calibrated, free |
| Thresholds, Rs maths, discount | **Plain code** (`src/economics.py`) | arithmetic must be exact and auditable |
| Understanding "haan / nahi / 1 / 2" replies | keyword rules | cheap, instant, predictable; unclear -> ask again -> human |

## Files
`backtest.py` train + simulate + write decisions · `app.py` dashboard/API/WhatsApp mock ·
`src/` features, model, decide, economics, whatsapp, llm_checks · `config.yaml` rules ·
`docs/MEMO.md` business memo · `docs/DECISION_LOG.md` · `docs/AI_USAGE_LOG.md`

## Honest limits
* Backtest uses out-of-fold predictions (each order scored by a model that never saw it).
* Rs impact depends on 4 behavioural assumptions (confirm catch rate, drop rate, nudge accept rate, repeat value) that the data cannot tell us. They sit in `config.yaml`; see memo section 4.
* LLM path is optional and is not part of the backtest numbers.
