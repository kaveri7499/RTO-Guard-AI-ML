"""All the Rs maths in one place. Pure arithmetic - no AI needed."""


def rto_cost(cfg):
    m = cfg["money"]
    return m["forward_ship"] + m["return_ship"] + m["packaging"] + m["damage_rate"] * m["product_cost"]


def margin(order_value, cfg):
    return cfg["money"]["gross_margin"] * order_value


def breakeven_risk(order_value, cfg):
    """Risk above which SHIPPING COD loses money: (1-p)*M = p*C  ->  p = M/(M+C)."""
    M, C = margin(order_value, cfg), rto_cost(cfg)
    return M / (M + C)


def max_prepaid_discount(order_value, risk, cfg):
    """Biggest Rs discount at which a prepaid conversion still beats shipping COD."""
    M, C, m = margin(order_value, cfg), rto_cost(cfg), cfg["money"]
    v_cod = (1 - risk) * M - risk * C
    pre = m["prepaid_rto_rate"]
    v_prepaid_no_disc = (1 - pre) * M - pre * C
    return max(0.0, (v_prepaid_no_disc - v_cod) / (1 - pre))


def prepaid_discount(order_value, risk, cfg):
    d = cfg["prepaid_discount"]
    raw = d["share_of_breakeven"] * max_prepaid_discount(order_value, risk, cfg)
    return int(round(min(d["max_rupees"], max(d["min_rupees"], raw)) / 5) * 5)


def action_value(action, y, order_value, is_new, cfg):
    """Estimated Rs change vs. 'ship as-is' for one order whose real outcome is y (1=RTO).
    Returns (saved, lost). Uses the assumptions block in config.yaml."""
    a, m = cfg["assumptions"], cfg["money"]
    M, C = margin(order_value, cfg), rto_cost(cfg)
    if action == "SHIP":
        return 0.0, 0.0
    if action == "CONFIRM":
        cost = a["whatsapp_msg_cost"]
        if y == 1:
            return a["confirm_catch_rate"] * C - cost, 0.0
        return 0.0, a["confirm_drop_genuine"] * M + cost
    if action == "NUDGE":
        acc, pre = a["nudge_accept_rate"], m["prepaid_rto_rate"]
        disc = prepaid_discount(order_value, 0.4, cfg)
        base = -C if y == 1 else M
        new = (1 - pre) * (M - disc) - pre * C
        delta = acc * (new - base)
        return (delta, 0.0) if delta >= 0 else (0.0, -delta)
    if action == "HOLD":
        if y == 1:
            return C, 0.0
        return 0.0, M + (a["future_value_new_customer"] if is_new else 0)
    raise ValueError(action)
