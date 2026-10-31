"""LLM is used ONLY for fuzzy text judgement: is this address complete/real? is the name fake?
Does it understand Hinglish? Everything numeric (risk, Rs, thresholds) stays in plain code.

Works offline: if USE_LLM != "1" or no ANTHROPIC_API_KEY, we use the rule-based score instead.
Results are cached in data/llm_cache.json so each order is only judged once (cheap + repeatable).
"""
import json, os, hashlib
from .features import address_score_rules, name_is_junk

CACHE = os.path.join(os.path.dirname(__file__), "..", "data", "llm_cache.json")
MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")   # change if your account uses another model

PROMPT = """You check Indian e-commerce COD orders for delivery-readiness.
City: {city}, State: {state}, Pincode: {pin}
Name: {name}
Address: {address}

Addresses may be in English, Hindi or Hinglish (e.g. "ph krke aana, Hanuman Mandir ke saamne").
A landmark-only address with "call before coming" is OK-ish but weaker than a full house address.
Reply with ONLY JSON, no markdown:
{{"address_score": <0.0-1.0, 1 = a courier could find it>, "name_fake": <true/false>,
  "reason": "<max 12 words, plain English>"}}"""


def _load():
    try:
        return json.load(open(CACHE))
    except Exception:
        return {}


def _save(c):
    json.dump(c, open(CACHE, "w"))


def check_order(o):
    """o: dict with name, address, city, state, pincode. Returns dict(address_score, name_fake, reason, source)."""
    fallback = {"address_score": address_score_rules(o["address"], o.get("city", "")),
                "name_fake": name_is_junk(o["name"]), "reason": "rule-based check", "source": "rules"}
    if os.getenv("USE_LLM") != "1" or not os.getenv("ANTHROPIC_API_KEY"):
        return fallback
    key = hashlib.md5(json.dumps(o, sort_keys=True).encode()).hexdigest()
    cache = _load()
    if key in cache:
        return cache[key]
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(
            model=MODEL, max_tokens=150,
            messages=[{"role": "user", "content": PROMPT.format(
                city=o.get("city"), state=o.get("state"), pin=o.get("pincode"),
                name=o["name"], address=o["address"])}])
        txt = msg.content[0].text.strip().replace("```json", "").replace("```", "")
        out = json.loads(txt)
        out = {"address_score": float(out["address_score"]), "name_fake": bool(out["name_fake"]),
               "reason": str(out.get("reason", ""))[:120], "source": "llm"}
        cache[key] = out
        _save(cache)
        return out
    except Exception as e:           # LLM down / bad JSON -> never block an order
        fallback["reason"] = f"rule-based (LLM failed: {type(e).__name__})"
        return fallback
