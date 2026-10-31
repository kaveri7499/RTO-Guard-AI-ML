# Memo: Cutting COD returns without cutting growth

**To:** Founder  **From:** [Your name]  **Re:** COD decision engine

**Bottom line.** Shipping a COD order is still profitable up to roughly **70% return risk** on an average Rs 649 order, because a return costs us Rs 169 while a delivered order earns Rs 402. So cancelling "risky" orders is the most expensive way to fight RTO. The better tools are a cheap WhatsApp confirmation and a prepaid discount. On last month's orders this would have added about **Rs 6,900 net on the 329 sample orders**, roughly **Rs 34,000/month** at our real COD volume (about 1,650 orders), under my base assumptions. Under pessimistic assumptions it drops to about Rs 6,000/month, so we should measure before trusting the bigger number.

## 1. What surprised me in the data (1,984 clean orders, RTO 28.5%)
1. **Seven cities drive the problem.** Gorakhpur (62%), Bareilly (61%), Darbhanga (59%), Sagar (49%), Patna (48%), Kota (41%) and Madhubani are 16% of orders but return **53%**, against 24% everywhere else. Mumbai and Pune return only 18%.
2. **Junk details predict returns, but they are rare.** 141 orders had an address like ".", "xyz", "home" or "call me": **64% returned** vs 26% for real addresses. 22 orders had fake names (asdf, test): 64% returned. Together they are only about 8% of orders, so they cannot be the whole fix.
3. **New is risky, but "has returned before" is worse.** First-time buyers return 30%. Repeat buyers with a clean history return only **14%**. One earlier RTO means 35%, two means **76%**.
4. **Where orders come from matters.** Meta ads orders return 31%, direct orders 23%. Orders above Rs 1,999 return 41%, while Rs 900-1,299 orders return only 22%.
5. **The file itself is messy:** 30 duplicate rows, status typed 4 different ways, 3 orders worth Rs 0, 12 missing pincodes. Cleaning changed the numbers, so the same cleaning must happen on live Shopify data.

## 2. Recommended rules and what they do to last month
Each order gets a risk score (logistic regression on city, address quality, history, order value, source). Cut-offs live in `config.yaml`.

| Risk | Action | Orders last month (sample) | Actual RTO in bucket |
|---|---|---|---|
| under 20% | Ship as-is | 133 | 10% |
| 20-45% | Nudge to prepaid (Rs 20-60 off) | 144 | 32% |
| 45-85% | WhatsApp confirmation first | 51 | 51% |
| 85%+ | Hold / cancel | 1 | 100% |

Saved Rs 10,891 from avoided RTOs, lost Rs 4,027 from genuine orders we confirmed, nudged or held, **net Rs 6,864** on 329 sample orders. The 10% RTO in the "ship" bucket shows the score separates good from bad orders.
**Prepaid discount maths:** at 40% risk a Rs 649 order is worth Rs 174 shipped COD, and Rs 380 if paid online (4% RTO). We could afford up to about Rs 214 off; we offer 35% of that, capped at Rs 60 (9% of the order), so most of the saving stays with us.

## 3. Operations vs Marketing, in rupees
On the same orders and the same assumptions:
- **Ops' plan (cancel everything at 40%+ risk):** saves Rs 37,800 of RTO cost but **throws away Rs 144,000 of genuine sales margin, net -Rs 106,600** over six months of sample data. Auto-cancel only paid off above about 85% risk, which is 9 orders.
- **Marketing's plan (ship everything):** net Rs 0, and we keep paying about Rs 78,000 a month in RTO cost.
- **Our plan:** net about **+Rs 41,000** over the sample.
Ops gets a hard stop for clearly bad orders (junk address plus fake name, or repeated RTOs at 85%+). Marketing gets a guard: **a first-time customer is never cancelled on risk alone**, they get a confirmation or a prepaid offer. Only 2 first-time customers were held in six months.

## 4. What could go wrong, and how we'd notice
- **My behaviour assumptions are guesses** (60% of would-be-RTO customers don't confirm, 12% of genuine ones drop out, 25% accept prepaid). If they are all 2-3x worse, the system loses money. *Check:* weekly confirm-reply rate, drop-out rate and prepaid acceptance on the dashboard.
- **Honest customers in the 7 cities get extra friction.** *Check:* sales per city before and after; if a city's orders fall more than its RTO, loosen that bucket.
- **Scores go stale** (new couriers, festivals, new ad campaigns). *Check:* actual RTO per bucket every week; "ship" should stay near 10-15%.
- **Customers learn to ignore WhatsApp**, or messages fail to deliver. *Check:* delivery and read rates.
- **The AI misreads an address.** The LLM never decides alone; it only adjusts a score, and failures fall back to rules.

## 5. If I had 2 more weeks
1. Run a 10% random holdout (no action) for 3 weeks to measure the real catch, drop and acceptance rates.
2. Connect the real WhatsApp API and a Shopify webhook so decisions happen live.
3. Add courier-by-pincode serviceability and retrain monthly with the new outcomes.
4. Test the LLM address check on 200 real orders and keep it only if it beats the rules.
5. Add cohort tracking: do nudged or confirmed first-time buyers reorder?
