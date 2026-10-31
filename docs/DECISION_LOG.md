# Decision log

- **Data cleaning first.** 30 exact duplicate rows removed; `final_status` had `Rto`, `delivered`, `RTO ` variants (normalised); 1 `IN_TRANSIT` row dropped (outcome unknown); 3 orders with value Rs 0 dropped; 12 missing pincodes kept as a flag. Alternative: ignore -> RTO counts would be wrong.
- **Economics before ML.** RTO costs Rs 169.4 (65+65+25+8%*180); a delivered Rs 649 order earns Rs 402. So shipping COD only loses money above ~70% risk (88% for a Rs 2,000 order). Consequence: auto-cancel almost never pays; confirmation/prepaid nudges are the main tools.
- **Model = logistic regression**, not XGBoost/LLM. 2k rows, need explainable reasons and calibrated probabilities. Out-of-fold AUC 0.72. Alternative considered: gradient boosting (not clearly better at this size, harder to explain).
- **City, not pincode.** No pincode had enough orders to estimate a rate; the 7 problem cities carry the signal.
- **LLM only for address/name judgement.** Everything numeric is code. LLM results cached, and if the LLM fails the order is never blocked (falls back to rules).
- **Four buckets by risk:** <20% ship, 20-45% nudge, 45-85% confirm, >=85% hold. Grid search preferred a lower ship threshold and wider nudge band, but that leans on the (unmeasured) nudge acceptance rate, so I chose more conservative numbers.
- **Marketing guard:** first-time customers are never held by risk alone (they go to confirmation); only junk address AND junk name together can hold a new customer. In the sample only 2 new customers were held vs 7 repeat customers.
- **Discount = 35% of break-even, capped Rs 20-60.** Break-even for a Rs 649 order at 40% risk is ~Rs 214; offering Rs 60 keeps most of the saving and is ~9% of the order.
- **No reply in 24h:** nudge -> ship COD (medium risk still profitable); confirm -> cancel, except first-time customers get a human call first.
- **Dashboard "yesterday"** = latest day in the sample data (the sample ends 30 Sep 2026); the date picker lets you view others.
- **Rs estimates use assumptions** (confirm catch 60%, genuine drop 12%, nudge accept 25%) written in config.yaml; sensitivity shown in the memo.
- **Not built (time):** real WhatsApp API, auth, live Shopify webhook, A/B holdout.
