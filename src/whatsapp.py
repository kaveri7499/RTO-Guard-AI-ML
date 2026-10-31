"""WhatsApp confirmation / prepaid-nudge flow (mock). Pure code: templates + a small state machine.
Reply understanding = keyword rules (handles English + Hinglish). Anything else -> one polite
re-ask, then a human. (Optional upgrade: send only the 'unclear' replies to an LLM.)"""
import re
from dataclasses import dataclass, field

YES = {"yes", "y", "yep", "ok", "okay", "confirm", "confirmed", "haan", "han", "ha", "haa", "ji", "theek", "sahi", "1"}
NO = {"no", "n", "cancel", "nahi", "nahin", "na", "mat", "2", "nope"}
PAY = {"pay", "online", "upi", "prepaid", "link", "3"}

HINDI_BELT = {"Uttar Pradesh", "Bihar", "Madhya Pradesh", "Rajasthan", "Delhi", "Maharashtra", "West Bengal", "Assam"}


def language_for(state):
    """Hinglish for Hindi-belt states, English for the South (simple, editable)."""
    return "hinglish" if state in HINDI_BELT else "english"


T = {
 ("CONFIRM", "hinglish"): "Namaste {name}! 🙏 Aapka KT order ({items}, Rs {value}) COD par hai. Kya hum ship kar dein? Reply *1* = Haan, ship karo | *2* = Cancel | *3* = Online pay karke Rs {disc} off lo.",
 ("CONFIRM", "english"): "Hi {name}! 🙏 Your order ({items}, Rs {value}) is Cash on Delivery. Shall we ship it? Reply *1* = Yes, ship | *2* = Cancel | *3* = Pay online and get Rs {disc} off.",
 ("NUDGE", "hinglish"): "Hi {name}! Aapka order ({items}) confirm ho gaya ✅ Abhi online pay karoge toh Rs {disc} off milega aur delivery priority se hogi. Reply *PAY* for link, ya *COD* rakhna ho toh *COD*.",
 ("NUDGE", "english"): "Hi {name}! Your order ({items}) is confirmed ✅ Pay online now and get Rs {disc} off plus priority dispatch. Reply *PAY* for the link, or *COD* to keep Cash on Delivery.",
 "REMIND_hinglish": "Reminder: aapka order abhi ruka hua hai. Ship karne ke liye *1* bhejein, cancel ke liye *2*.",
 "REMIND_english": "Reminder: your order is on hold. Reply *1* to ship it or *2* to cancel.",
 "UNCLEAR_hinglish": "Maaf kijiye, samajh nahi aaya 🙏 Kripya *1* (ship), *2* (cancel) ya *3* (online pay) bhejein.",
 "UNCLEAR_english": "Sorry, I didn't get that 🙏 Please reply *1* (ship), *2* (cancel) or *3* (pay online).",
 "SHIP": "Thank you! Your order is being packed 📦",
 "CANCEL": "Done, your order is cancelled. Hope to serve you again!",
 "PAYLINK": "Great! Pay securely here: https://pay.example.com/{oid} (Rs {pay_amt}). We ship as soon as payment lands.",
}


def classify_reply(text):
    t = re.sub(r"[^a-z0-9 ]", " ", str(text).lower()).split()
    w = set(t)
    if w & PAY: return "PAY"
    if "cod" in w: return "COD"
    if w & NO: return "NO"
    if w & YES: return "YES"
    return "UNCLEAR"


@dataclass
class Conversation:
    order: dict
    kind: str                      # "CONFIRM" or "NUDGE"
    discount: int
    first_time: bool = False
    state: str = "WAITING"         # WAITING / SHIP_COD / SHIP_PREPAID / CANCELLED / HUMAN
    hours: float = 0.0
    unclear: int = 0
    reminded: bool = False
    log: list = field(default_factory=list)

    def _say(self, who, text): self.log.append({"who": who, "text": text, "t": round(self.hours, 1)})

    def start(self):
        lang = language_for(self.order.get("state"))
        self.lang = lang
        msg = T[(self.kind, lang)].format(name=str(self.order["customer_name"]).split()[0],
                                          items=self.order.get("items", "your order").replace("|", ", "),
                                          value=int(self.order["order_value"]), disc=self.discount)
        self._say("bot", msg); return self

    def reply(self, text):
        if self.state != "WAITING": return self
        self._say("customer", text)
        intent = classify_reply(text)
        pay_amt = int(self.order["order_value"]) - self.discount
        if intent == "PAY":
            self._say("bot", T["PAYLINK"].format(oid=self.order.get("order_id", "X"), pay_amt=pay_amt))
            self.state = "SHIP_PREPAID"
        elif intent == "COD":
            self._say("bot", T["SHIP"]); self.state = "SHIP_COD"
        elif intent == "YES":
            self._say("bot", T["SHIP"]); self.state = "SHIP_COD"
        elif intent == "NO":
            if self.kind == "NUDGE":            # said no to discount only -> keep COD
                self._say("bot", T["SHIP"]); self.state = "SHIP_COD"
            else:
                self._say("bot", T["CANCEL"]); self.state = "CANCELLED"
        else:
            self.unclear += 1
            if self.unclear >= 2:
                self.state = "HUMAN"; self._say("bot", "Connecting you to our team 🙂 They will call you shortly.")
            else:
                self._say("bot", T[f"UNCLEAR_{self.lang}"])
        return self

    def tick(self, hours):
        """Move the clock forward. Handles reminder at 6h and the 24h no-reply rule."""
        if self.state != "WAITING": return self
        before = self.hours; self.hours += hours
        if before < 6 <= self.hours and not self.reminded and self.kind == "CONFIRM":
            self.reminded = True; self._say("bot", T[f"REMIND_{self.lang}"])
        if self.hours >= 24:
            if self.kind == "NUDGE":            # medium risk: shipping COD is still profitable
                self.state = "SHIP_COD"; self._say("system", "No reply in 24h -> shipping as COD (medium risk).")
            elif self.first_time:               # Marketing guard: a human calls before we cancel a new customer
                self.state = "HUMAN"; self._say("system", "No reply in 24h, first-time customer -> ops calls before cancelling.")
            else:
                self.state = "CANCELLED"; self._say("system", "No reply in 24h -> order cancelled, stock released.")
        return self
