# AI usage log

**Tools:** Claude (claude.ai) for analysing the CSV, drafting the code, and drafting the memo.
Optional runtime LLM (Anthropic API) for address/name judgement in `src/llm_checks.py`.

**What I used it for:** data exploration, code skeleton, backtest design, WhatsApp copy in Hinglish, first draft of memo.

## Where the AI was wrong / weak and how I caught it
> EDIT THESE: keep only what really happened to you, in your own words. Add your own after you test the app.

1. **Dirty labels.** The first look at `final_status` showed 6 values (`RTO`, `Rto`, `delivered`, `IN_TRANSIT`...). A naive group-by would split RTO rates. Caught by printing `value_counts()`; fixed by upper-casing/stripping and dropping unknown outcomes.
2. **Over-optimistic threshold search.** The automatic grid search chose a very low "ship" threshold because nudges are almost free under the assumed 25% acceptance. I noticed the result depended on an unmeasured assumption, re-ran with pessimistic assumptions (net fell from Rs 41k to Rs 7.6k and became negative in the worst case) and chose conservative thresholds instead.
3. **Backtest leakage risk.** Scoring orders with a model trained on the same orders would inflate results. Switched to 5-fold out-of-fold predictions.
4. *(Add yours: e.g. test the LLM prompt on 10 Hinglish addresses and note any it got wrong.)*
