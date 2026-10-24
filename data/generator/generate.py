"""
Synthetic data generator for Halcyon Botanicals (fictional Shopify DTC brand).

Produces CSVs shaped like what Graphed's connectors land for Shopify, Meta Ads,
Google Ads, GA4 and Klaviyo, plus the founder's hand-kept Monday spreadsheet.
Deterministic (seeded). Run:  python data/generator/generate.py

Five problems are planted on purpose. See customer/brief.md for the answer key.
"""
from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np

SEED = 20261024
rng = np.random.default_rng(SEED)

START = date(2026, 4, 1)
END = date(2026, 10, 23)
DAYS = [(START + timedelta(days=i)) for i in range((END - START).days + 1)]
N = len(DAYS)

OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

# Planted-issue dates
PIXEL_DOUBLE_FIRE_FROM = date(2026, 6, 12)   # Shopify Meta channel installed, old pixel left on
UTM_RENAME_FROM = date(2026, 7, 15)          # media buyer renamed campaigns
CODE_LEAK_FROM = date(2026, 8, 10)           # FERN20 hits coupon sites
FATIGUE_FROM = date(2026, 8, 1)              # Golden Hour UGC ad starts fatiguing

# ----------------------------------------------------------------------------
# Catalog
# ----------------------------------------------------------------------------
PRODUCTS = [
    # id, sku, title, price
    (8101, "HB-ROSE-750", "Rosemary Fig Aperitivo 750ml", 42.00),
    (8102, "HB-CITR-750", "Bitter Citrus Aperitivo 750ml", 38.00),
    (8103, "HB-SMOK-750", "Smoked Pear Aperitivo 750ml", 40.00),
    (8104, "HB-TRIO-3PK", "The Trio 3-Pack", 99.00),
]
SUB_DISCOUNT = 0.15

# ----------------------------------------------------------------------------
# Meta campaign structure (names are the CURRENT names, as Meta reports them)
# ----------------------------------------------------------------------------
@dataclass
class Ad:
    ad_id: int
    name: str
    adset_id: int
    adset_name: str
    campaign_id: int
    campaign_name: str
    old_utm: str
    new_utm: str
    kind: str              # prospecting | retargeting
    base_share: float      # share of campaign-kind spend
    base_ctr: float
    base_cpm: float
    fatigue: bool = False

ADS = [
    Ad(1201, "Golden Hour UGC 0:22", 1101, "Broad 25-54 US", 1001, "[P] Prospecting | Broad",
       "prospecting_broad_v1", "p_prospecting_broad", "prospecting", 0.42, 0.0160, 14.5, fatigue=True),
    Ad(1202, "Founder Story Static", 1101, "Broad 25-54 US", 1001, "[P] Prospecting | Broad",
       "prospecting_broad_v1", "p_prospecting_broad", "prospecting", 0.20, 0.0105, 13.8),
    Ad(1203, "Ingredient Flatlay Carousel", 1101, "Broad 25-54 US", 1001, "[P] Prospecting | Broad",
       "prospecting_broad_v1", "p_prospecting_broad", "prospecting", 0.13, 0.0092, 15.2),
    Ad(1204, "Sober Curious Testimonial", 1102, "Interests - Sober Curious", 1002, "[P] Prospecting | Interests",
       "prospecting_interests_v1", "p_prospecting_interests", "prospecting", 0.15, 0.0121, 19.9),
    Ad(1205, "Mocktail Recipe Reel", 1102, "Interests - Sober Curious", 1002, "[P] Prospecting | Interests",
       "prospecting_interests_v1", "p_prospecting_interests", "prospecting", 0.10, 0.0134, 18.7),
    Ad(1206, "Review Carousel 4.8 stars", 1103, "Warm - Purchasers 180d + Site 30d", 1003, "[R] Retargeting | Warm",
       "retargeting_warm_v1", "r_retargeting_warm", "retargeting", 0.55, 0.0210, 24.0),
    Ad(1207, "Subscribe & Save 15%", 1103, "Warm - Purchasers 180d + Site 30d", 1003, "[R] Retargeting | Warm",
       "retargeting_warm_v1", "r_retargeting_warm", "retargeting", 0.30, 0.0185, 23.1),
    Ad(1208, "Cart Reminder DPA", 1104, "Cart Abandoners 7d", 1004, "[R] Retargeting | Cart",
       "retargeting_cart_v1", "r_retargeting_cart", "retargeting", 0.15, 0.0290, 27.5),
]

def t_frac(d: date) -> float:
    return (d - START).days / max(N - 1, 1)

def dow_factor(d: date) -> float:
    # Sunday/Monday strongest for DTC beverage, Fri/Sat softer
    return {0: 1.06, 1: 1.02, 2: 0.99, 3: 0.98, 4: 0.93, 5: 0.92, 6: 1.10}[d.weekday()]

def noise(sd: float = 0.08) -> float:
    return float(np.clip(rng.normal(1.0, sd), 0.6, 1.5))

# ----------------------------------------------------------------------------
# Daily macro series
# ----------------------------------------------------------------------------
def meta_spend_for(d: date) -> float:
    # ~$28k/mo in April -> ~$49k/mo in Sept/Oct. The buyer scaled the "winner".
    base = 930 + 700 * t_frac(d)
    return base * dow_factor(d) * noise(0.07)

def true_new_cac_meta(d: date) -> float:
    # Real cost of a NEW customer from Meta. Rises 38 -> 61.
    f = t_frac(d)
    cac = 38 + 20 * (f ** 1.15)
    if d >= FATIGUE_FROM:  # fatigue tax on top
        cac *= 1.0 + 0.10 * min(1.0, (d - FATIGUE_FROM).days / 45)
    return cac

@dataclass
class Customer:
    id: int
    created_at: datetime
    source: str                # meta | google_brand | organic | email | influencer | coupon_leak
    subscriber: bool = False
    sub_next: date | None = None
    sub_cycles: int = 0
    orders: int = 0
    spent: float = 0.0
    first_order_at: datetime | None = None
    last_order_at: datetime | None = None
    email_opt_in: bool = True
    city: str = ""
    state: str = ""

CITIES = [("Austin","TX"),("Los Angeles","CA"),("Brooklyn","NY"),("Denver","CO"),("Portland","OR"),
          ("Chicago","IL"),("Nashville","TN"),("Seattle","WA"),("San Diego","CA"),("Atlanta","GA"),
          ("Phoenix","AZ"),("Minneapolis","MN"),("Boston","MA"),("Dallas","TX"),("Charlotte","NC")]

customers: list[Customer] = []
_next_cid = 70000

def new_customer(created: datetime, source: str) -> Customer:
    global _next_cid
    _next_cid += 1
    city, state = CITIES[rng.integers(0, len(CITIES))]
    c = Customer(id=_next_cid, created_at=created, source=source, city=city, state=state,
                 email_opt_in=bool(rng.random() < 0.82))
    customers.append(c)
    return c

# Pre-existing base: brand launched ~Oct 2024. ~13,800 customers before April 2026.
for i in range(13800):
    days_back = int(rng.integers(1, 540))
    created = datetime.combine(START - timedelta(days=days_back), datetime.min.time()) + timedelta(seconds=int(rng.integers(0, 86400)))
    src = rng.choice(["meta", "organic", "google_brand", "email", "influencer"], p=[0.62, 0.17, 0.09, 0.05, 0.07])
    c = new_customer(created, str(src))
    c.orders = int(rng.choice([1, 1, 1, 2, 2, 3, 4, 6], p=[0.30, 0.15, 0.10, 0.15, 0.10, 0.10, 0.06, 0.04]))
    c.first_order_at = created
    c.last_order_at = created + timedelta(days=int(rng.integers(0, max(1, days_back))))
    c.spent = round(c.orders * float(rng.normal(68, 14)), 2)
    if rng.random() < 0.095:  # ~1,300 active subscribers at start
        c.subscriber = True
        c.sub_next = START + timedelta(days=int(rng.integers(0, 30)))
        c.sub_cycles = int(rng.integers(1, 9))

# ----------------------------------------------------------------------------
# Order generation
# ----------------------------------------------------------------------------
@dataclass
class Order:
    id: int
    number: int
    created_at: datetime
    customer_id: int
    kind: str                 # first | repeat | renewal
    channel: str              # meta | google_brand | organic | email | influencer | coupon_leak | direct
    utm_campaign: str | None
    utm_source: str | None
    utm_medium: str | None
    referring_site: str
    source_name: str          # web | subscription_contract
    tags: str
    discount_code: str | None
    lines: list[tuple[int, str, str, int, float]] = field(default_factory=list)
    subtotal: float = 0.0
    discounts: float = 0.0
    total: float = 0.0
    meta_claims: bool = False # Meta's 7-day-click attribution claims it (truthfully or not)
    meta_adset: int | None = None
    klaviyo_claims: bool = False
    klaviyo_name: str | None = None

orders: list[Order] = []
_next_oid = 5600000
_next_onum = 24810

def pick_lines(kind: str, sub: bool) -> list[tuple[int, str, str, int, float]]:
    lines = []
    if sub:
        pid, sku, title, price = PRODUCTS[int(rng.integers(0, 3))]
        qty = int(rng.choice([1, 1, 2, 2], p=[0.40, 0.2, 0.2, 0.20]))
        lines.append((pid, sku, title, qty, price))
        return lines
    r = rng.random()
    if r < 0.36:
        pid, sku, title, price = PRODUCTS[3]
        lines.append((pid, sku, title, 1, price))
    else:
        n = int(rng.choice([1, 1, 2, 2, 3], p=[0.45, 0.15, 0.2, 0.12, 0.08]))
        idx = rng.choice([0, 1, 2], size=n, replace=False)
        for i in idx:
            pid, sku, title, price = PRODUCTS[int(i)]
            lines.append((pid, sku, title, int(rng.choice([1, 1, 2], p=[0.7, 0.15, 0.15])), price))
    return lines

def utm_for(channel: str, d: date, adset: int | None) -> tuple[str | None, str | None, str | None, str]:
    if channel == "meta":
        ad = next(a for a in ADS if a.adset_id == adset)
        camp = ad.new_utm if d >= UTM_RENAME_FROM else ad.old_utm
        return camp, "facebook", "paid_social", "https://l.facebook.com/" if rng.random() < 0.55 else "https://www.instagram.com/"
    if channel == "google_brand":
        return "brand_exact", "google", "cpc", "https://www.google.com/"
    if channel == "email":
        return None, "klaviyo", "email", ""
    if channel == "organic":
        return None, None, None, "https://www.google.com/" if rng.random() < 0.8 else "https://www.bing.com/"
    if channel == "influencer":
        return None, None, None, "https://www.instagram.com/" if rng.random() < 0.6 else ""
    if channel == "coupon_leak":
        r = rng.random()
        ref = "https://www.retailmenot.com/" if r < 0.3 else ("https://www.joinhoney.com/" if r < 0.55 else "")
        return None, None, None, ref
    return None, None, None, ""

def make_order(d: date, cust: Customer, kind: str, channel: str, adset: int | None = None,
               code: str | None = None, discount_pct: float = 0.0) -> Order:
    global _next_oid, _next_onum
    _next_oid += int(rng.integers(1, 4))
    _next_onum += 1
    hour = int(np.clip(rng.normal(14, 4.5), 0, 23))
    created = datetime.combine(d, datetime.min.time()) + timedelta(hours=hour, minutes=int(rng.integers(0, 60)), seconds=int(rng.integers(0, 60)))
    sub = kind == "renewal" or (kind == "first" and cust.subscriber)
    lines = pick_lines(kind, sub)
    subtotal = round(sum(q * p for _, _, _, q, p in lines), 2)
    discounts = 0.0
    if sub:
        discounts = round(subtotal * SUB_DISCOUNT, 2)
        code = None
    elif code:
        discounts = round(subtotal * discount_pct, 2)
    total = round(subtotal - discounts, 2)
    utm_c, utm_s, utm_m, ref = utm_for(channel, d, adset)
    if kind == "renewal":
        utm_c, utm_s, utm_m, ref = None, None, None, ""
    tags = []
    if sub and kind == "first":
        tags.append("Subscription First Order")
    if kind == "renewal":
        tags.append("Subscription Recurring Order")
    o = Order(id=_next_oid, number=_next_onum, created_at=created, customer_id=cust.id, kind=kind,
              channel=channel, utm_campaign=utm_c, utm_source=utm_s, utm_medium=utm_m, referring_site=ref,
              source_name="subscription_contract" if kind == "renewal" else "web",
              tags=", ".join(tags), discount_code=code, lines=lines, subtotal=subtotal,
              discounts=discounts, total=total)
    cust.orders += 1
    cust.spent = round(cust.spent + total, 2)
    cust.last_order_at = created
    if cust.first_order_at is None:
        cust.first_order_at = created
    orders.append(o)
    return o

# Per-day aggregates we need later for the ad platform tables
daily = []  # dicts

for d in DAYS:
    f = t_frac(d)
    spend = meta_spend_for(d)
    prospecting_spend = spend * (0.80 - 0.04 * f)   # buyer slowly shifts more into retargeting
    retargeting_spend = spend - prospecting_spend

    # New customers from Meta prospecting (truth)
    n_new_meta = int(rng.poisson(spend / true_new_cac_meta(d)))
    # Other new customers
    n_new_brand = int(rng.poisson(3.2 * dow_factor(d)))
    n_new_organic = int(rng.poisson(4.4 * dow_factor(d) * (1 + 0.12 * f)))
    n_new_email = int(rng.poisson(1.1))
    n_new_infl = int(rng.poisson(2.4 if d.day in (3, 4, 5, 17, 18, 19) else 0.9))  # seeding drops
    n_new_leak = 0
    if d >= CODE_LEAK_FROM:
        ramp = min(1.0, (d - CODE_LEAK_FROM).days / 12)
        n_new_leak = int(rng.poisson(9 * ramp * dow_factor(d)))

    new_today: list[Order] = []
    def add_new(n: int, channel: str, adset_pool=None, code=None, pct=0.0):
        for _ in range(n):
            created = datetime.combine(d, datetime.min.time()) + timedelta(seconds=int(rng.integers(0, 86400)))
            c = new_customer(created, channel)
            # Subscription take rate on first order
            take = 0.19 if channel in ("meta", "organic", "google_brand", "email") else (0.10 if channel == "influencer" else 0.03)
            if rng.random() < take:
                c.subscriber = True
                c.sub_next = d + timedelta(days=30)
            adset = None
            if adset_pool is not None:
                adset = int(rng.choice(adset_pool, p=[0.7, 0.3]))
            o = make_order(d, c, "first", channel, adset=adset, code=code, discount_pct=pct)
            if channel == "meta":
                o.meta_claims = True; o.meta_adset = adset
            new_today.append(o)

    add_new(n_new_meta, "meta", adset_pool=[1101, 1102])
    add_new(n_new_brand, "google_brand")
    add_new(n_new_organic, "organic")
    add_new(n_new_email, "email")
    # Influencer code FERN20 is legit when used by influencer-driven buyers
    for _ in range(n_new_infl):
        created = datetime.combine(d, datetime.min.time()) + timedelta(seconds=int(rng.integers(0, 86400)))
        c = new_customer(created, "influencer")
        if rng.random() < 0.12:
            c.subscriber = True; c.sub_next = d + timedelta(days=30)
        use_code = rng.random() < 0.65
        o = make_order(d, c, "first", "influencer", code="FERN20" if use_code else None, discount_pct=0.20 if use_code else 0.0)
        new_today.append(o)
    add_new(n_new_leak, "coupon_leak", code="FERN20", pct=0.20)

    # Subscription renewals due today
    renewals_today: list[Order] = []
    for c in customers:
        if c.subscriber and c.sub_next is not None and c.sub_next <= d:
            # churn per cycle: 8% normally; coupon-leak subs churn hard
            churn = 0.08 if c.source != "coupon_leak" else 0.35
            if c.sub_cycles >= 6:
                churn = 0.05
            if rng.random() < churn:
                c.subscriber = False
                c.sub_next = None
                continue
            o = make_order(d, c, "renewal", "direct")
            c.sub_cycles += 1
            c.sub_next = d + timedelta(days=int(rng.choice([28, 30, 30, 31])))
            renewals_today.append(o)

    # One-time repeat orders from existing non-renewal behavior
    eligible = [c for c in customers if c.first_order_at is not None and (d - c.first_order_at.date()).days >= 21]
    n_repeat = int(rng.poisson(len(eligible) * 0.00205 * dow_factor(d)))
    repeat_today: list[Order] = []
    if eligible:
        picks = rng.choice(len(eligible), size=min(n_repeat, len(eligible)), replace=False)
        for i in picks:
            c = eligible[int(i)]
            r = rng.random()
            if r < 0.34:
                ch = "email"
            elif r < 0.52:
                ch = "meta"            # they clicked a retargeting ad on the way back
            elif r < 0.64:
                ch = "google_brand"
            else:
                ch = "organic" if rng.random() < 0.5 else "direct"
            adset = None
            if ch == "meta":
                adset = int(rng.choice([1103, 1104], p=[0.78, 0.22]))
            o = make_order(d, c, "repeat", ch, adset=adset)
            if ch == "meta":
                o.meta_claims = True; o.meta_adset = adset
            if ch == "email":
                o.klaviyo_claims = True
            repeat_today.append(o)

    # Meta's 7-day-click window also claims a slice of renewals and non-meta repeats (people saw a warm ad)
    for o in renewals_today:
        if rng.random() < 0.20:
            o.meta_claims = True; o.meta_adset = 1103
    for o in repeat_today:
        if not o.meta_claims and rng.random() < 0.12:
            o.meta_claims = True; o.meta_adset = int(rng.choice([1103, 1104], p=[0.85, 0.15]))
    # Klaviyo claims flows on renewals (reminder emails) and some new orders (welcome flow / abandoned cart)
    for o in renewals_today:
        if rng.random() < 0.41:
            o.klaviyo_claims = True; o.klaviyo_name = "Flow: Subscription Renewal Reminder"
    for o in repeat_today:
        if o.klaviyo_claims:
            o.klaviyo_name = "Campaign" if rng.random() < 0.6 else "Flow: Winback 45d"
    for o in new_today:
        if rng.random() < 0.17:
            o.klaviyo_claims = True; o.klaviyo_name = "Flow: Abandoned Cart" if rng.random() < 0.7 else "Flow: Welcome Series"

    daily.append(dict(d=d, spend=spend, prospecting_spend=prospecting_spend, retargeting_spend=retargeting_spend,
                      n_new_meta=n_new_meta, new=new_today, renewals=renewals_today, repeats=repeat_today))

print(f"customers: {len(customers):,}  orders: {len(orders):,}")

# ----------------------------------------------------------------------------
# Meta ads insights (what Ads Manager reports)
# ----------------------------------------------------------------------------
meta_rows = []
for day in daily:
    d = day["d"]
    claimed = [o for o in (day["new"] + day["renewals"] + day["repeats"]) if o.meta_claims]
    by_adset: dict[int, list[Order]] = {}
    for o in claimed:
        by_adset.setdefault(o.meta_adset, []).append(o)

    # fatigue multipliers for the Golden Hour ad
    fat = 0.0
    if d >= FATIGUE_FROM:
        fat = min(1.0, (d - FATIGUE_FROM).days / 50)

    for kind, kind_spend in (("prospecting", day["prospecting_spend"]), ("retargeting", day["retargeting_spend"])):
        ads = [a for a in ADS if a.kind == kind]
        shares = np.array([a.base_share for a in ads], dtype=float)
        if kind == "prospecting":
            # buyer keeps scaling the "winner": its share climbs 42% -> 68%
            gh = next(i for i, a in enumerate(ads) if a.fatigue)
            shares[gh] = 0.42 + 0.26 * t_frac(d)
            others = [i for i in range(len(ads)) if i != gh]
            rest = 1 - shares[gh]
            base_rest = sum(ads[i].base_share for i in others)
            for i in others:
                shares[i] = rest * ads[i].base_share / base_rest
        shares = shares * np.clip(rng.normal(1, 0.05, len(ads)), 0.8, 1.2)
        shares /= shares.sum()

        # distribute claimed purchases in this kind across ads in proportion to spend share within adset
        for adset_id in {a.adset_id for a in ads}:
            adset_ads = [i for i, a in enumerate(ads) if a.adset_id == adset_id]
            adset_orders = by_adset.get(adset_id, [])
            w = shares[adset_ads] / shares[adset_ads].sum()
            # fatigued ad converts worse per dollar
            if kind == "prospecting" and adset_id == 1101:
                gh_local = [k for k, i in enumerate(adset_ads) if ads[i].fatigue][0]
                w = w.copy(); w[gh_local] *= (1 - 0.45 * fat); w /= w.sum()
            assign = rng.multinomial(len(adset_orders), w) if adset_orders else np.zeros(len(adset_ads), dtype=int)
            # split order list accordingly
            idx = 0
            for k, i in enumerate(adset_ads):
                a = ads[i]
                sp = float(kind_spend * shares[i])
                mine = adset_orders[idx: idx + int(assign[k])]; idx += int(assign[k])
                purchases = len(mine)
                value = round(sum(o.total for o in mine), 2)
                cpm = a.base_cpm * (1 + 0.22 * t_frac(d)) * noise(0.06)
                impressions = int(sp / cpm * 1000)
                ctr = a.base_ctr * noise(0.07)
                freq = 1.9 + 0.4 * t_frac(d)
                if a.fatigue:
                    ctr *= (1 - 0.52 * fat)
                    freq = 2.0 + 0.5 * t_frac(d) + 2.4 * fat
                if kind == "retargeting":
                    freq = 3.4 + 1.1 * t_frac(d)
                clicks = int(impressions * ctr)
                link_clicks = int(clicks * 0.86)
                reach = int(impressions / freq)
                # PLANTED: double-fired purchase pixel from Jun 12 (dedupe catches a little)
                rep_purchases, rep_value = purchases, value
                if d >= PIXEL_DOUBLE_FIRE_FROM:
                    mult = 1.62 + float(rng.normal(0, 0.03))
                    rep_purchases = int(round(purchases * mult))
                    rep_value = round(value * mult, 2)
                meta_rows.append(dict(
                    date_start=d.isoformat(), account_id="act_2210094471", campaign_id=a.campaign_id,
                    campaign_name=a.campaign_name, adset_id=a.adset_id, adset_name=a.adset_name,
                    ad_id=a.ad_id, ad_name=a.name, objective="OUTCOME_SALES",
                    spend=round(sp, 2), impressions=impressions, reach=reach, frequency=round(freq, 2),
                    clicks=clicks, inline_link_clicks=link_clicks,
                    ctr=round(100 * clicks / impressions, 4) if impressions else 0,
                    cpc=round(sp / clicks, 4) if clicks else 0, cpm=round(1000 * sp / impressions, 4) if impressions else 0,
                    purchases=rep_purchases, purchase_value=rep_value,
                    purchase_roas=round(rep_value / sp, 4) if sp else 0,
                    landing_page_views=int(link_clicks * 0.78), add_to_cart=int(link_clicks * 0.11),
                    initiate_checkout=int(link_clicks * 0.05),
                ))

# ----------------------------------------------------------------------------
# Google Ads (brand only)
# ----------------------------------------------------------------------------
gads_rows = []
for day in daily:
    d = day["d"]
    brand_orders = [o for o in (day["new"] + day["repeats"]) if o.channel == "google_brand"]
    cost = 95 + 55 * t_frac(d) * dow_factor(d) * noise(0.1)
    clicks = int(cost / (1.65 * noise(0.1)))
    impressions = int(clicks / 0.31)
    gads_rows.append(dict(
        segments_date=d.isoformat(), customer_id="814-220-9931", campaign_id=20994410211,
        campaign_name="Brand | Exact | US", campaign_status="ENABLED", advertising_channel_type="SEARCH",
        metrics_cost_micros=int(cost * 1_000_000), metrics_impressions=impressions, metrics_clicks=clicks,
        metrics_conversions=round(len(brand_orders) * 0.94, 1),
        metrics_conversions_value=round(sum(o.total for o in brand_orders) * 0.94, 2),
        metrics_search_impression_share=round(float(np.clip(rng.normal(0.88, 0.03), 0.7, 0.98)), 4),
    ))

# ----------------------------------------------------------------------------
# GA4 sessions by source / medium / campaign (what GA4 attributes, last click)
# ----------------------------------------------------------------------------
ga4_rows = []
def ga_key(o: Order):
    if o.channel == "meta":
        src = "facebook" if "facebook" in o.referring_site else "instagram"
        return (src, "paid_social", o.utm_campaign or "(not set)")
    if o.channel == "google_brand":
        return ("google", "cpc", "brand_exact")
    if o.channel == "email" or (o.klaviyo_claims and o.kind != "renewal" and o.channel == "direct"):
        return ("klaviyo", "email", o.klaviyo_name or "(not set)")
    if o.channel == "organic":
        return ("google" if "google" in o.referring_site else "bing", "organic", "(not set)")
    if o.channel == "coupon_leak":
        if "retailmenot" in o.referring_site:
            return ("retailmenot.com", "referral", "(not set)")
        if "honey" in o.referring_site:
            return ("joinhoney.com", "referral", "(not set)")
        return ("(direct)", "(none)", "(not set)")
    if o.channel == "influencer":
        return ("instagram.com", "referral", "(not set)") if o.referring_site else ("(direct)", "(none)", "(not set)")
    return ("(direct)", "(none)", "(not set)")

for day in daily:
    d = day["d"]
    buckets: dict[tuple, dict] = {}
    all_orders = day["new"] + day["renewals"] + day["repeats"]
    for o in all_orders:
        if o.kind == "renewal" and not o.klaviyo_claims:
            k = ("(direct)", "(none)", "(not set)")
        else:
            k = ga_key(o)
        b = buckets.setdefault(k, dict(purchases=0, revenue=0.0))
        if rng.random() < 0.93:  # tag loss
            b["purchases"] += 1; b["revenue"] += o.total
    cvr = {"paid_social": 0.011, "cpc": 0.071, "email": 0.034, "organic": 0.026, "referral": 0.019, "(none)": 0.042}
    meta_clicks_today = sum(r["inline_link_clicks"] for r in meta_rows if r["date_start"] == d.isoformat())
    for k, b in buckets.items():
        src, med, camp = k
        rate = cvr.get(med, 0.03) * noise(0.12)
        sessions = int(b["purchases"] / rate) if b["purchases"] else int(rng.integers(20, 90))
        if med == "paid_social":
            sessions = max(sessions, int(meta_clicks_today * 0.78 * 0.5 * (0.6 if "broad" in camp else 0.4)))
        ga4_rows.append(dict(
            date=d.isoformat(), property_id="properties/412009913", session_source=src, session_medium=med,
            session_campaign=camp, sessions=sessions, engaged_sessions=int(sessions * float(np.clip(rng.normal(0.58, 0.05), 0.3, 0.8))),
            new_users=int(sessions * (0.71 if med in ("paid_social", "organic", "referral") else 0.33)),
            add_to_carts=int(b["purchases"] * 3.1 + sessions * 0.02), ecommerce_purchases=b["purchases"],
            purchase_revenue=round(b["revenue"], 2),
        ))

# ----------------------------------------------------------------------------
# Klaviyo attributed revenue
# ----------------------------------------------------------------------------
klaviyo_rows = []
flow_names = ["Flow: Welcome Series", "Flow: Abandoned Cart", "Flow: Winback 45d", "Flow: Subscription Renewal Reminder"]
for day in daily:
    d = day["d"]
    claimed = [o for o in (day["new"] + day["renewals"] + day["repeats"]) if o.klaviyo_claims]
    by_name: dict[str, list[Order]] = {}
    for o in claimed:
        name = o.klaviyo_name or "Campaign"
        if name == "Campaign":
            name = f"Campaign: {['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][d.weekday()]} send {d.isoformat()}"
        by_name.setdefault(name, []).append(o)
    for name in flow_names:
        by_name.setdefault(name, [])
    for name, os_ in by_name.items():
        is_flow = name.startswith("Flow")
        recipients = int(rng.integers(180, 420)) if is_flow else int(rng.integers(14000, 19500))
        if not is_flow and d.weekday() not in (1, 4):
            if not os_:
                continue
        opens = int(recipients * float(np.clip(rng.normal(0.41 if is_flow else 0.33, 0.04), 0.1, 0.8)))
        clicks = int(opens * float(np.clip(rng.normal(0.11 if is_flow else 0.06, 0.02), 0.01, 0.4)))
        # Klaviyo's 5-day attribution over-claims a bit on top of what we gave it
        over = 1.0 + (0.18 if is_flow else 0.25)
        klaviyo_rows.append(dict(
            date=d.isoformat(), message_type="flow" if is_flow else "campaign", message_name=name,
            recipients=recipients, opens=opens, clicks=clicks,
            attributed_orders=int(round(len(os_) * over)), attributed_revenue=round(sum(o.total for o in os_) * over, 2),
            unsubscribes=int(recipients * 0.0021) if not is_flow else int(recipients * 0.004),
        ))

# ----------------------------------------------------------------------------
# Founder's Monday spreadsheet (their math, their mistakes)
# ----------------------------------------------------------------------------
sheet_rows = []
week_start = START - timedelta(days=START.weekday())  # Monday
while week_start <= END:
    week_end = week_start + timedelta(days=6)
    m = [r for r in meta_rows if week_start.isoformat() <= r["date_start"] <= week_end.isoformat()]
    g = [r for r in gads_rows if week_start.isoformat() <= r["segments_date"] <= week_end.isoformat()]
    os_ = [o for o in orders if week_start <= o.created_at.date() <= week_end]
    meta_spend = round(sum(r["spend"] for r in m), 2)
    meta_purch = sum(r["purchases"] for r in m)
    meta_val = round(sum(r["purchase_value"] for r in m), 2)
    g_spend = round(sum(r["metrics_cost_micros"] for r in g) / 1e6, 2)
    shop_orders = len(os_)
    shop_rev = round(sum(o.total for o in os_), 2)
    # Their "CAC" = total paid spend / Meta-reported purchases. Wrong on both sides.
    cac = round((meta_spend + g_spend) / meta_purch, 2) if meta_purch else None
    note = ""
    if date(2026, 6, 8) <= week_start <= date(2026, 6, 14):
        note = "installed shopify meta channel"
    elif date(2026, 7, 13) <= week_start <= date(2026, 7, 19):
        note = "renamed campaigns per agency"
    elif date(2026, 8, 10) <= week_start <= date(2026, 8, 23):
        note = "FERN20 doing great?? orders up"
    sheet_rows.append(dict(
        week_of=week_start.isoformat(), meta_spend=meta_spend, google_spend=g_spend,
        meta_purchases_reported=meta_purch, meta_roas_reported=round(meta_val / meta_spend, 2) if meta_spend else None,
        shopify_orders=shop_orders, shopify_revenue=shop_rev, blended_cac_their_calc=cac, notes=note,
    ))
    week_start += timedelta(days=7)

# ----------------------------------------------------------------------------
# Write CSVs
# ----------------------------------------------------------------------------
def write(name: str, rows: list[dict]):
    if not rows:
        return
    p = OUT / f"{name}.csv"
    with p.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"  {p.name:36s} {len(rows):>8,} rows")

def iso(dt: datetime | None) -> str | None:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else None

cust_by_id = {c.id: c for c in customers}
shop_orders_rows, shop_lines_rows = [], []
_line_id = 9100000
for o in orders:
    first = cust_by_id.get(o.customer_id)
    landing = "/"
    if o.utm_source:
        landing = f"/?utm_source={o.utm_source}&utm_medium={o.utm_medium}" + (f"&utm_campaign={o.utm_campaign}" if o.utm_campaign else "")
        if o.channel == "meta":
            landing += f"&fbclid=IwAR{o.id % 99991:05d}x"
    elif o.channel == "coupon_leak":
        landing = "/products/the-trio-3-pack" if rng.random() < 0.5 else "/collections/all"
    ship = 0.0 if o.total >= 75 or o.kind == "renewal" else 7.95
    shop_orders_rows.append(dict(
        id=o.id, order_number=o.number, name=f"#{o.number}", created_at=iso(o.created_at), processed_at=iso(o.created_at),
        updated_at=iso(o.created_at + timedelta(hours=2)), customer_id=o.customer_id, email=f"customer{o.customer_id}@example.com",
        financial_status="paid", fulfillment_status="fulfilled" if o.created_at.date() < END - timedelta(days=3) else "unfulfilled",
        currency="USD", subtotal_price=o.subtotal, total_discounts=o.discounts, total_tax=round(o.total * 0.0825, 2),
        total_shipping=ship, total_price=round(o.total + o.total * 0.0825 + ship, 2),
        discount_code=o.discount_code, source_name=o.source_name, tags=o.tags,
        landing_site=landing, referring_site=o.referring_site, shipping_city=first.city if first else "",
        shipping_province_code=first.state if first else "", cancelled_at=None, test=False,
    ))
    for pid, sku, title, qty, price in o.lines:
        _line_id += 1
        pct = SUB_DISCOUNT if (o.source_name == "subscription_contract" or "Subscription First Order" in o.tags) else (0.20 if o.discount_code == "FERN20" else 0.0)
        shop_lines_rows.append(dict(id=_line_id, order_id=o.id, product_id=pid, variant_id=pid * 10 + 1, sku=sku, title=title,
                                    quantity=qty, price=price, total_discount=round(qty * price * pct, 2)))

shop_customers_rows = [dict(
    id=c.id, email=f"customer{c.id}@example.com", created_at=iso(c.created_at), updated_at=iso(c.last_order_at or c.created_at),
    orders_count=c.orders, total_spent=round(c.spent, 2), state="enabled", accepts_marketing=c.email_opt_in,
    default_address_city=c.city, default_address_province_code=c.state, default_address_country_code="US",
    tags="Active Subscriber" if c.subscriber else "", first_order_at=iso(c.first_order_at), last_order_at=iso(c.last_order_at),
) for c in customers if c.orders > 0]

shop_products_rows = [dict(id=pid, title=title, handle=title.lower().replace(" ", "-"), product_type="Aperitivo" if "Pack" not in title else "Bundle",
                           vendor="Halcyon Botanicals", status="active", created_at="2024-10-02 15:00:00", price=price, sku=sku)
                      for pid, sku, title, price in PRODUCTS]

print("writing:")
write("shopify_orders", shop_orders_rows)
write("shopify_order_line_items", shop_lines_rows)
write("shopify_customers", shop_customers_rows)
write("shopify_products", shop_products_rows)
write("meta_ads_insights", meta_rows)
write("google_ads_campaign_stats", gads_rows)
write("ga4_traffic_acquisition", ga4_rows)
write("klaviyo_message_performance", klaviyo_rows)
write("founder_monday_sheet", sheet_rows)

# ----------------------------------------------------------------------------
# Sanity report (truth vs reported)
# ----------------------------------------------------------------------------
print("\nmonthly truth vs Ads Manager:")
print(f"{'month':8s} {'meta_spend':>11s} {'new_meta':>9s} {'true_CAC':>9s} {'AM_purch':>9s} {'AM_ROAS':>8s} {'shop_orders':>11s} {'shop_rev':>10s}")
for m in range(4, 11):
    rows = [r for r in meta_rows if r["date_start"][5:7] == f"{m:02d}"]
    sp = sum(r["spend"] for r in rows); pv = sum(r["purchase_value"] for r in rows); pu = sum(r["purchases"] for r in rows)
    new_meta = sum(day["n_new_meta"] for day in daily if day["d"].month == m)
    os_ = [o for o in orders if o.created_at.month == m]
    print(f"2026-{m:02d}  {sp:11,.0f} {new_meta:9d} {sp/new_meta if new_meta else 0:9.2f} {pu:9d} {pv/sp if sp else 0:8.2f} {len(os_):11,d} {sum(o.total for o in os_):10,.0f}")
