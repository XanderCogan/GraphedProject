"""
Synthetic data generator for Halcyon Botanicals (fictional Shopify DTC brand). v3.

Simulates the brand from launch (2024-10-02) to 2026-10-23 so Shopify has full history and
customers' orders_count / total_spent reconcile to the orders table. Ad platform, GA4 and
Klaviyo exports cover the connector backfill window (2026-04-01 onward), which is what
Graphed's connectors land on first sync.

Timestamps are UTC (connectors normalize). The store runs on America/Chicago.

Deterministic (seeded). Run:  python data/generator/generate.py

Five problems are planted on purpose. See customer/brief.md for the answer key.
See data/realism-audit.md for what v3 fixed versus v2.
"""
from __future__ import annotations

import csv
import math
import string
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import numpy as np

SEED = 20261024
rng = np.random.default_rng(SEED)

LAUNCH = date(2024, 10, 2)
END = date(2026, 10, 23)
WINDOW_START = date(2026, 4, 1)          # connector backfill window for ad platforms / GA4 / Klaviyo
DAYS = [(LAUNCH + timedelta(days=i)) for i in range((END - LAUNCH).days + 1)]
NDAYS = len(DAYS)
WIN_N = (END - WINDOW_START).days + 1

OUT = Path(__file__).resolve().parents[1] / "out"
OUT.mkdir(parents=True, exist_ok=True)

# Planted-issue dates
PIXEL_DOUBLE_FIRE_FROM = date(2026, 6, 12)   # Shopify Meta channel installed, old pixel left on
UTM_RENAME_FROM = date(2026, 7, 15)          # media buyer renamed campaigns, switched UTMs to {{campaign.name}}
CODE_LEAK_FROM = date(2026, 8, 10)           # FERN20 hits coupon sites
FATIGUE_FROM = date(2026, 7, 20)             # Golden Hour UGC starts fatiguing (7-day frequency crosses 4 late Aug)

# ----------------------------------------------------------------------------
# Time helpers
# ----------------------------------------------------------------------------
def dst_bounds(year: int) -> tuple[date, date]:
    mar = date(year, 3, 1); mar += timedelta(days=(6 - mar.weekday()) % 7 + 7)   # 2nd Sunday March
    nov = date(year, 11, 1); nov += timedelta(days=(6 - nov.weekday()) % 7)      # 1st Sunday Nov
    return mar, nov

def utc_offset_hours(d: date) -> int:
    a, b = dst_bounds(d.year)
    return 5 if a <= d < b else 6

def local_to_utc(dt: datetime) -> datetime:
    return dt + timedelta(hours=utc_offset_hours(dt.date()))

def win_frac(d: date) -> float:
    """0 at WINDOW_START, 1 at END, clipped."""
    return float(np.clip((d - WINDOW_START).days / max(WIN_N - 1, 1), 0, 1))

def pre_frac(d: date) -> float:
    """0 at launch, 1 at WINDOW_START."""
    return float(np.clip((d - LAUNCH).days / (WINDOW_START - LAUNCH).days, 0, 1))

def noise(sd: float = 0.08, lo: float = 0.5, hi: float = 1.6) -> float:
    return float(np.clip(rng.normal(1.0, sd), lo, hi))

def dow_demand(d: date) -> float:
    # Sunday/Monday strongest for DTC beverage, Fri/Sat softer
    return {0: 1.07, 1: 1.02, 2: 0.99, 3: 0.98, 4: 0.92, 5: 0.90, 6: 1.12}[d.weekday()]

# ----------------------------------------------------------------------------
# Promo calendar and seasonality
# ----------------------------------------------------------------------------
@dataclass
class Promo:
    start: date
    end: date
    code: str
    pct: float
    lift: float          # multiplier on new-customer demand and repeat hazard
    meta_budget: float   # multiplier on Meta budget
    name: str

PROMOS = [
    Promo(date(2024, 11, 29), date(2024, 12, 2), "BLACKFRIDAY25", 0.25, 2.4, 1.8, "Black Friday: 25% off everything"),
    Promo(date(2025, 1, 2), date(2025, 1, 31), "DRYJAN15", 0.15, 1.30, 1.25, "Dry January: 15% off"),
    Promo(date(2025, 5, 23), date(2025, 5, 26), "SUMMER15", 0.15, 1.45, 1.2, "Memorial Day weekend: 15% off"),
    Promo(date(2025, 7, 1), date(2025, 7, 5), "FIREWORKS15", 0.15, 1.35, 1.15, "4th of July: 15% off"),
    Promo(date(2025, 8, 29), date(2025, 9, 1), "LABORDAY15", 0.15, 1.35, 1.15, "Labor Day: 15% off"),
    Promo(date(2025, 11, 28), date(2025, 12, 1), "BFCM25", 0.25, 2.8, 2.0, "Black Friday: 25% off everything"),
    Promo(date(2026, 1, 2), date(2026, 1, 31), "DRYJAN15", 0.15, 1.35, 1.25, "Dry January: 15% off"),
    Promo(date(2026, 5, 22), date(2026, 5, 25), "SUMMER15", 0.15, 1.45, 1.2, "Memorial Day weekend: 15% off"),
    Promo(date(2026, 7, 1), date(2026, 7, 5), "FIREWORKS15", 0.15, 1.35, 1.15, "4th of July: 15% off"),
    Promo(date(2026, 9, 4), date(2026, 9, 7), "LABORDAY15", 0.15, 1.35, 1.15, "Labor Day: 15% off"),
]

def promo_for(d: date) -> Promo | None:
    for p in PROMOS:
        if p.start <= d <= p.end:
            return p
    return None

def season_demand(d: date) -> float:
    m = d.month
    base = {1: 1.0, 2: 0.90, 3: 0.92, 4: 0.98, 5: 1.04, 6: 1.08, 7: 1.08, 8: 1.05, 9: 0.98, 10: 0.98, 11: 1.0, 12: 1.12}[m]
    if m == 12 and d.day >= 21:
        base *= 0.78                      # post-shipping-cutoff lull
    return base

def season_cpm(d: date) -> float:
    m = d.month
    return {1: 0.85, 2: 0.92, 3: 0.97, 4: 1.0, 5: 1.0, 6: 0.96, 7: 0.95, 8: 0.97, 9: 1.03, 10: 1.08, 11: 1.35, 12: 1.30}[m]

# ----------------------------------------------------------------------------
# Catalog
# ----------------------------------------------------------------------------
PRODUCTS = [
    # id, sku, title, price, mix weight (hero SKU dominates)
    (8101, "HB-ROSE-750", "Rosemary Fig Aperitivo 750ml", 42.00, 0.48),
    (8102, "HB-CITR-750", "Bitter Citrus Aperitivo 750ml", 38.00, 0.30),
    (8103, "HB-SMOK-750", "Smoked Pear Aperitivo 750ml", 40.00, 0.22),
    (8104, "HB-TRIO-3PK", "The Trio 3-Pack", 99.00, 0.0),
]
SKU_W = np.array([p[4] for p in PRODUCTS[:3]]); SKU_W = SKU_W / SKU_W.sum()
SUB_DISCOUNT = 0.15

# ----------------------------------------------------------------------------
# Geography: metro-population weighted, mild home-market bump for Texas
# ----------------------------------------------------------------------------
CITIES = [
    ("New York", "NY", 8.3), ("Brooklyn", "NY", 2.6), ("Queens", "NY", 2.3), ("Los Angeles", "CA", 3.9), ("Chicago", "IL", 2.7),
    ("Houston", "TX", 2.3), ("Phoenix", "AZ", 1.6), ("Philadelphia", "PA", 1.6), ("San Antonio", "TX", 1.4), ("San Diego", "CA", 1.4),
    ("Dallas", "TX", 1.3), ("Austin", "TX", 1.0), ("San Jose", "CA", 1.0), ("Fort Worth", "TX", 0.9), ("Jacksonville", "FL", 0.95),
    ("Columbus", "OH", 0.9), ("Charlotte", "NC", 0.9), ("Indianapolis", "IN", 0.88), ("San Francisco", "CA", 0.87), ("Seattle", "WA", 0.75),
    ("Denver", "CO", 0.72), ("Washington", "DC", 0.7), ("Nashville", "TN", 0.69), ("Oklahoma City", "OK", 0.68), ("El Paso", "TX", 0.68),
    ("Boston", "MA", 0.65), ("Portland", "OR", 0.65), ("Las Vegas", "NV", 0.64), ("Detroit", "MI", 0.64), ("Memphis", "TN", 0.63),
    ("Louisville", "KY", 0.62), ("Baltimore", "MD", 0.58), ("Milwaukee", "WI", 0.57), ("Albuquerque", "NM", 0.56), ("Tucson", "AZ", 0.54),
    ("Fresno", "CA", 0.54), ("Sacramento", "CA", 0.52), ("Kansas City", "MO", 0.51), ("Mesa", "AZ", 0.5), ("Atlanta", "GA", 0.5),
    ("Omaha", "NE", 0.49), ("Colorado Springs", "CO", 0.48), ("Raleigh", "NC", 0.47), ("Miami", "FL", 0.44), ("Long Beach", "CA", 0.46),
    ("Virginia Beach", "VA", 0.45), ("Oakland", "CA", 0.44), ("Minneapolis", "MN", 0.43), ("Tulsa", "OK", 0.41), ("Tampa", "FL", 0.4),
    ("Arlington", "TX", 0.4), ("New Orleans", "LA", 0.38), ("Wichita", "KS", 0.39), ("Cleveland", "OH", 0.37), ("Bakersfield", "CA", 0.4),
    ("Aurora", "CO", 0.39), ("Anaheim", "CA", 0.35), ("Honolulu", "HI", 0.35), ("Santa Ana", "CA", 0.31), ("Riverside", "CA", 0.32),
    ("Corpus Christi", "TX", 0.32), ("Lexington", "KY", 0.32), ("Henderson", "NV", 0.32), ("Stockton", "CA", 0.32), ("Saint Paul", "MN", 0.31),
    ("Cincinnati", "OH", 0.31), ("St. Louis", "MO", 0.3), ("Pittsburgh", "PA", 0.3), ("Greensboro", "NC", 0.3), ("Lincoln", "NE", 0.29),
    ("Anchorage", "AK", 0.29), ("Plano", "TX", 0.29), ("Orlando", "FL", 0.31), ("Irvine", "CA", 0.31), ("Newark", "NJ", 0.31),
    ("Durham", "NC", 0.29), ("Chula Vista", "CA", 0.28), ("Toledo", "OH", 0.27), ("Fort Wayne", "IN", 0.27), ("St. Petersburg", "FL", 0.26),
    ("Laredo", "TX", 0.26), ("Jersey City", "NJ", 0.29), ("Chandler", "AZ", 0.28), ("Madison", "WI", 0.27), ("Lubbock", "TX", 0.26),
    ("Scottsdale", "AZ", 0.24), ("Reno", "NV", 0.26), ("Buffalo", "NY", 0.28), ("Gilbert", "AZ", 0.27), ("Glendale", "AZ", 0.25),
    ("North Las Vegas", "NV", 0.26), ("Winston-Salem", "NC", 0.25), ("Chesapeake", "VA", 0.25), ("Norfolk", "VA", 0.24), ("Fremont", "CA", 0.23),
    ("Garland", "TX", 0.24), ("Irving", "TX", 0.26), ("Hialeah", "FL", 0.22), ("Richmond", "VA", 0.23), ("Boise", "ID", 0.24),
    ("Spokane", "WA", 0.23), ("Baton Rouge", "LA", 0.22), ("Tacoma", "WA", 0.22), ("San Bernardino", "CA", 0.22), ("Modesto", "CA", 0.22),
    ("Fontana", "CA", 0.21), ("Des Moines", "IA", 0.21), ("Moreno Valley", "CA", 0.21), ("Santa Clarita", "CA", 0.23), ("Fayetteville", "NC", 0.21),
    ("Birmingham", "AL", 0.2), ("Oxnard", "CA", 0.2), ("Rochester", "NY", 0.21), ("Port St. Lucie", "FL", 0.2), ("Grand Rapids", "MI", 0.2),
    ("Huntsville", "AL", 0.21), ("Salt Lake City", "UT", 0.2), ("Frisco", "TX", 0.2), ("Yonkers", "NY", 0.21), ("Amarillo", "TX", 0.2),
    ("Glendale", "CA", 0.2), ("Huntington Beach", "CA", 0.2), ("McKinney", "TX", 0.2), ("Montgomery", "AL", 0.2), ("Augusta", "GA", 0.2),
    ("Aurora", "IL", 0.18), ("Akron", "OH", 0.19), ("Little Rock", "AR", 0.2), ("Tempe", "AZ", 0.18), ("Columbus", "GA", 0.2),
    ("Overland Park", "KS", 0.2), ("Grand Prairie", "TX", 0.2), ("Tallahassee", "FL", 0.2), ("Cape Coral", "FL", 0.19), ("Mobile", "AL", 0.19),
    ("Knoxville", "TN", 0.19), ("Shreveport", "LA", 0.18), ("Worcester", "MA", 0.2), ("Ontario", "CA", 0.18), ("Vancouver", "WA", 0.19),
    ("Sioux Falls", "SD", 0.19), ("Chattanooga", "TN", 0.18), ("Brownsville", "TX", 0.19), ("Fort Lauderdale", "FL", 0.18), ("Providence", "RI", 0.19),
    ("Newport News", "VA", 0.18), ("Rancho Cucamonga", "CA", 0.17), ("Santa Rosa", "CA", 0.17), ("Peoria", "AZ", 0.18), ("Oceanside", "CA", 0.17),
    ("Elk Grove", "CA", 0.17), ("Salem", "OR", 0.17), ("Pembroke Pines", "FL", 0.17), ("Eugene", "OR", 0.17), ("Garden Grove", "CA", 0.17),
    ("Cary", "NC", 0.17), ("Fort Collins", "CO", 0.17), ("Corona", "CA", 0.17), ("Springfield", "MO", 0.17), ("Jackson", "MS", 0.16),
    ("Alexandria", "VA", 0.16), ("Hayward", "CA", 0.16), ("Clarksville", "TN", 0.16), ("Lakewood", "CO", 0.16), ("Lancaster", "CA", 0.17),
    ("Salinas", "CA", 0.16), ("Palmdale", "CA", 0.17), ("Hollywood", "FL", 0.15), ("Springfield", "MA", 0.16), ("Macon", "GA", 0.16),
    ("Kansas City", "KS", 0.16), ("Sunnyvale", "CA", 0.16), ("Pomona", "CA", 0.15), ("Killeen", "TX", 0.16), ("Escondido", "CA", 0.15),
    ("Pasadena", "TX", 0.15), ("Naperville", "IL", 0.15), ("Bellevue", "WA", 0.15), ("Joliet", "IL", 0.15), ("Murfreesboro", "TN", 0.16),
    ("Midland", "TX", 0.14), ("Rockford", "IL", 0.15), ("Paterson", "NJ", 0.16), ("Savannah", "GA", 0.15), ("Bridgeport", "CT", 0.15),
    ("Torrance", "CA", 0.15), ("McAllen", "TX", 0.14), ("Syracuse", "NY", 0.15), ("Surprise", "AZ", 0.14), ("Denton", "TX", 0.15),
    ("Roseville", "CA", 0.15), ("Thornton", "CO", 0.14), ("Miramar", "FL", 0.14), ("Pasadena", "CA", 0.14), ("Mesquite", "TX", 0.14),
    ("Olathe", "KS", 0.14), ("Santa Clara", "CA", 0.13), ("Victorville", "CA", 0.14), ("Waco", "TX", 0.14), ("Carrollton", "TX", 0.13),
    ("Charleston", "SC", 0.15), ("Warren", "MI", 0.14), ("Hampton", "VA", 0.14), ("Gainesville", "FL", 0.14), ("Visalia", "CA", 0.14),
    ("Coral Springs", "FL", 0.13), ("Columbia", "SC", 0.14), ("Cedar Rapids", "IA", 0.14), ("Sterling Heights", "MI", 0.13), ("New Haven", "CT", 0.14),
    ("Stamford", "CT", 0.14), ("Concord", "CA", 0.13), ("Kent", "WA", 0.13), ("Santa Barbara", "CA", 0.1), ("Boulder", "CO", 0.11),
    ("Ann Arbor", "MI", 0.12), ("Burlington", "VT", 0.05), ("Portland", "ME", 0.07), ("Asheville", "NC", 0.1), ("Bozeman", "MT", 0.06),
    ("Missoula", "MT", 0.07), ("Manchester", "NH", 0.11), ("Wilmington", "DE", 0.07), ("Dover", "DE", 0.04), ("Juneau", "AK", 0.03),
    ("Bend", "OR", 0.1), ("Santa Fe", "NM", 0.09), ("Cheyenne", "WY", 0.06), ("Fargo", "ND", 0.12), ("Billings", "MT", 0.11),
]
# Online brand: geography follows population and ad delivery, not the HQ. Premium non-alcoholic skews
# coastal/urban a little. Texas gets no special bump beyond its population.
_cw = np.array([w * (1.15 if st in ("CA", "NY", "WA", "OR", "CO", "MA", "DC") else 1.0) for _, st, w in CITIES]); _cw /= _cw.sum()

# Combined state + average local sales tax rate (approximate). No sales tax: OR, MT, NH, DE, AK (local only).
STATE_TAX = {
    "AL": 9.25, "AK": 1.8, "AZ": 8.4, "AR": 9.45, "CA": 8.8, "CO": 7.8, "CT": 6.35, "DE": 0.0, "DC": 6.0, "FL": 7.0, "GA": 7.4, "HI": 4.45,
    "ID": 6.0, "IL": 8.85, "IN": 7.0, "IA": 6.95, "KS": 8.7, "KY": 6.0, "LA": 9.55, "ME": 5.5, "MD": 6.0, "MA": 6.25, "MI": 6.0, "MN": 8.0,
    "MS": 7.05, "MO": 8.3, "MT": 0.0, "NE": 6.95, "NV": 8.25, "NH": 0.0, "NJ": 6.6, "NM": 7.6, "NY": 8.52, "NC": 7.0, "ND": 7.0, "OH": 7.2,
    "OK": 9.0, "OR": 0.0, "PA": 6.3, "RI": 7.0, "SC": 7.5, "SD": 6.4, "TN": 9.55, "TX": 8.2, "UT": 7.2, "VT": 6.3, "VA": 5.75, "WA": 9.4,
    "WV": 6.5, "WI": 5.45, "WY": 5.4,
}
_city_tax_jitter = {i: float(np.clip(rng.normal(0, 0.45), -0.9, 0.9)) for i in range(len(CITIES))}

def tax_rate(city_idx: int) -> float:
    st = CITIES[city_idx][1]
    base = STATE_TAX[st]
    if base == 0.0:
        return 0.0
    return max(4.0, base + _city_tax_jitter[city_idx]) / 100

# ----------------------------------------------------------------------------
# Meta account structure. Campaign/adset names are the CURRENT names (Meta reports current names
# for all history). Ads have a lifecycle: the buyer launches new creative every few weeks and
# pauses losers.
# ----------------------------------------------------------------------------
@dataclass
class Ad:
    ad_id: int
    name: str
    adset_id: int
    start: date
    end: date | None
    base_share: float      # delivery weight within ad set
    base_ctr: float
    base_cpm: float
    quality: float = 1.0   # conversion weight per dollar relative to ad set
    fatigue: bool = False

ADSETS = {
    1101: ("Broad 25-54 US", 1001, "[P] Prospecting | Broad", "prospecting_broad_v1", "prospecting"),
    1102: ("Interests - Sober Curious", 1002, "[P] Prospecting | Interests", "prospecting_interests_v1", "prospecting"),
    1103: ("Warm - Purchasers 180d + Site 30d", 1003, "[R] Retargeting | Warm", "retargeting_warm_v1", "retargeting"),
    1104: ("Cart Abandoners 7d", 1004, "[R] Retargeting | Cart", "retargeting_cart_v1", "retargeting"),
}

ADS = [
    # Broad prospecting
    Ad(1201, "Golden Hour UGC 0:22", 1101, date(2025, 11, 4), None, 0.42, 0.0160, 14.5, 1.15, fatigue=True),
    Ad(1202, "Founder Story Static", 1101, date(2025, 6, 10), date(2026, 8, 4), 0.20, 0.0105, 13.8, 0.95),
    Ad(1203, "Ingredient Flatlay Carousel", 1101, date(2026, 1, 13), None, 0.13, 0.0092, 15.2, 0.85),
    Ad(1209, "Dinner Party Lifestyle Static", 1101, date(2026, 4, 14), date(2026, 5, 5), 0.12, 0.0081, 15.9, 0.55),
    Ad(1210, "Hangover-Free Hook UGC 0:15", 1101, date(2026, 5, 12), None, 0.16, 0.0138, 14.9, 1.0),
    Ad(1211, "Pour Shot Reel", 1101, date(2026, 6, 2), date(2026, 6, 23), 0.10, 0.0119, 15.4, 0.6),
    Ad(1212, "Founder Story v2 Static", 1101, date(2026, 7, 7), None, 0.14, 0.0112, 14.1, 0.9),
    Ad(1213, "Summer Spritz Carousel", 1101, date(2026, 8, 18), date(2026, 9, 8), 0.11, 0.0098, 15.6, 0.65),
    Ad(1214, "Fall Fig Reel", 1101, date(2026, 9, 15), None, 0.15, 0.0141, 15.0, 1.05),
    # Interests prospecting
    Ad(1204, "Sober Curious Testimonial", 1102, date(2025, 9, 16), None, 0.45, 0.0121, 19.9, 1.0),
    Ad(1205, "Mocktail Recipe Reel", 1102, date(2026, 2, 3), None, 0.30, 0.0134, 18.7, 1.05),
    Ad(1216, "Adaptogen Explainer Static", 1102, date(2026, 4, 28), date(2026, 5, 26), 0.18, 0.0088, 20.6, 0.6),
    Ad(1215, "Zero Proof Dinner Party UGC", 1102, date(2026, 6, 30), None, 0.28, 0.0129, 19.2, 0.95),
    # Warm retargeting
    Ad(1206, "Review Carousel 4.8 stars", 1103, date(2025, 5, 20), None, 0.50, 0.0210, 24.0, 1.0),
    Ad(1207, "Subscribe & Save 15%", 1103, date(2025, 8, 12), None, 0.30, 0.0185, 23.1, 1.1),
    Ad(1217, "Trio Bundle Offer", 1103, date(2026, 6, 16), None, 0.25, 0.0172, 23.8, 0.9),
    # Cart retargeting
    Ad(1208, "Cart Reminder DPA", 1104, date(2025, 3, 4), None, 1.0, 0.0290, 27.5, 1.0),
]
AD_BY_ID = {a.ad_id: a for a in ADS}

def live_ads(adset_id: int, d: date) -> list[Ad]:
    return [a for a in ADS if a.adset_id == adset_id and a.start <= d and (a.end is None or d < a.end)]

def utm_campaign_for(adset_id: int, d: date) -> str:
    name, _, current, old, _ = ADSETS[adset_id]
    return current if d >= UTM_RENAME_FROM else old       # after rename: {{campaign.name}} dynamic param

# ----------------------------------------------------------------------------
# Macro series
# ----------------------------------------------------------------------------
def meta_budget_target(d: date) -> float:
    """Daily budget the buyer is aiming at. ~$200/day at launch -> ~$930/day Apr 2026 -> ~$1,630/day Oct 2026."""
    if d < WINDOW_START:
        return 200 * (930 / 200) ** pre_frac(d)
    return 930 + 700 * win_frac(d)

# Buyer revises the daily budget on Mondays (step changes), holds sometimes, pushes on promos.
_budget_by_day: dict[date, float] = {}
_cur = None
for _d in DAYS:
    if _cur is None or _d.weekday() == 0:
        target = meta_budget_target(_d)
        if _cur is None or rng.random() < 0.72:
            _cur = target * float(np.clip(rng.normal(1.0, 0.06), 0.85, 1.2))
    p = promo_for(_d)
    _budget_by_day[_d] = _cur * (p.meta_budget if p else 1.0)

def meta_spend_for(d: date) -> float:
    pacing = {0: 1.0, 1: 1.0, 2: 0.99, 3: 0.99, 4: 0.97, 5: 0.98, 6: 1.04}[d.weekday()]
    return _budget_by_day[d] * pacing * float(np.clip(rng.normal(1.0, 0.05), 0.8, 1.25))

def true_new_cac_meta(d: date) -> float:
    """Real cost of a NEW customer from Meta (total Meta spend / new Meta customers)."""
    if d < WINDOW_START:
        cac = 30 + 6 * pre_frac(d)
    else:
        f = win_frac(d)
        cac = 36 + 24 * (f ** 1.15)
        if d >= FATIGUE_FROM:
            cac *= 1.0 + 0.10 * min(1.0, (d - FATIGUE_FROM).days / 45)
    p = promo_for(d)
    cac *= (0.82 if p and p.lift >= 2 else (0.9 if p else 1.0))
    cac *= {1: 0.82, 2: 1.08, 3: 1.06, 11: 0.95, 12: 0.97}.get(d.month, 1.0)
    return cac

def brand_scale(d: date) -> float:
    """Non-paid demand scales with how big the brand is (awareness ~ cumulative spend)."""
    return meta_budget_target(d) / 930

# ----------------------------------------------------------------------------
# Customers
# ----------------------------------------------------------------------------
@dataclass
class Customer:
    id: int
    created_at: datetime          # UTC, set from first order
    source: str                   # meta | google_brand | organic | email | influencer | coupon_leak
    city_idx: int
    subscriber: bool = False
    sub_next: date | None = None
    sub_cycles: int = 0
    orders: int = 0
    spent: float = 0.0
    first_order_at: datetime | None = None
    last_order_at: datetime | None = None
    last_day: int = -999
    first_day: int = -999
    email_opt_in: bool = True
    state: str = "disabled"

customers: list[Customer] = []
_next_cid = 70000

def new_customer(created_utc: datetime, source: str) -> Customer:
    global _next_cid
    _next_cid += 1
    ci = int(rng.choice(len(CITIES), p=_cw))
    st = str(rng.choice(["disabled", "enabled", "invited"], p=[0.66, 0.31, 0.03]))
    c = Customer(id=_next_cid, created_at=created_utc, source=source, city_idx=ci,
                 email_opt_in=bool(rng.random() < 0.82), state=st)
    customers.append(c)
    return c

# ----------------------------------------------------------------------------
# Orders
# ----------------------------------------------------------------------------
@dataclass
class Order:
    id: int
    created_at: datetime          # UTC
    customer_id: int
    kind: str                     # first | repeat | renewal
    channel: str                  # meta | google_brand | organic | email | influencer | coupon_leak | direct
    utm_campaign: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_content: str | None
    referring_site: str
    source_name: str              # web | subscription_contract
    tags: str
    discount_code: str | None
    discount_pct: float
    city_idx: int
    lines: list[tuple[int, str, str, int, float]] = field(default_factory=list)
    subtotal: float = 0.0
    discounts: float = 0.0
    total: float = 0.0
    tax: float = 0.0
    shipping: float = 0.0
    total_price: float = 0.0
    meta_claims: bool = False
    meta_adset: int | None = None
    klaviyo_claims: bool = False
    klaviyo_name: str | None = None
    financial_status: str = "paid"
    fulfillment_status: str | None = "fulfilled"
    cancelled_at: datetime | None = None
    updated_at: datetime | None = None
    number: int = 0

orders: list[Order] = []
_oid = 0

def local_checkout_time(d: date, kind: str) -> datetime:
    if kind == "renewal":
        # Recharge batch-charges early morning store time
        minutes = int(np.clip(rng.normal(300, 35), 215, 420))     # ~05:00 local
        return datetime.combine(d, datetime.min.time()) + timedelta(minutes=minutes)
    # web checkout: bimodal-ish, lunch and evening, wrapped
    hour = rng.normal(13.5, 3.2) if rng.random() < 0.55 else rng.normal(20.0, 1.9)
    hour = hour % 24
    return datetime.combine(d, datetime.min.time()) + timedelta(hours=float(hour), minutes=int(rng.integers(0, 60)), seconds=int(rng.integers(0, 60)))

def pick_lines(kind: str, sub: bool, promo: bool, leak: bool) -> list[tuple[int, str, str, int, float]]:
    lines = []
    if sub:
        pid, sku, title, price, _ = PRODUCTS[int(rng.choice(3, p=SKU_W))]
        qty = int(rng.choice([1, 2], p=[0.68, 0.32]))
        return [(pid, sku, title, qty, price)]
    trio_p = 0.36
    if promo:
        trio_p = 0.48
    if leak:
        trio_p = 0.22
    if rng.random() < trio_p:
        pid, sku, title, price, _ = PRODUCTS[3]
        lines.append((pid, sku, title, 1 if rng.random() < 0.92 else 2, price))
        if rng.random() < 0.08:
            pid, sku, title, price, _ = PRODUCTS[int(rng.choice(3, p=SKU_W))]
            lines.append((pid, sku, title, 1, price))
        return lines
    n = int(rng.choice([1, 2, 3], p=[0.62, 0.28, 0.10]))
    idx = rng.choice(3, size=n, replace=False, p=SKU_W)
    for i in idx:
        pid, sku, title, price, _ = PRODUCTS[int(i)]
        q = int(rng.choice([1, 2, 3], p=[0.74, 0.21, 0.05]))
        if promo:
            q = int(rng.choice([1, 2, 3], p=[0.55, 0.32, 0.13]))
        lines.append((pid, sku, title, q, price))
    return lines

def fbclid() -> str:
    alphabet = string.ascii_letters + string.digits + "-_"
    return "IwAR" + "".join(rng.choice(list(alphabet), size=57))

def utm_for(channel: str, d: date, adset: int | None) -> tuple[str | None, str | None, str | None, str | None, str]:
    if channel == "meta":
        camp = utm_campaign_for(adset, d)
        ad = None
        if d >= UTM_RENAME_FROM:
            la = live_ads(adset, d)
            ad = str(rng.choice([a.ad_id for a in la])) if la else None
        ref = "https://l.facebook.com/" if rng.random() < 0.52 else "https://l.instagram.com/"
        return camp, "facebook", "paid_social", ad, ref
    if channel == "google_brand":
        return "brand_exact", "google", "cpc", None, "https://www.google.com/"
    if channel == "email":
        return None, "klaviyo", "email", None, ""
    if channel == "organic":
        r = rng.random()
        return None, None, None, None, "https://www.google.com/" if r < 0.82 else ("https://www.bing.com/" if r < 0.93 else "https://duckduckgo.com/")
    if channel == "influencer":
        return None, None, None, None, "https://www.instagram.com/" if rng.random() < 0.55 else ""
    if channel == "coupon_leak":
        r = rng.random()
        ref = ("https://www.retailmenot.com/" if r < 0.32 else "https://www.couponfollow.com/" if r < 0.50
               else "https://www.dealspotr.com/" if r < 0.58 else "https://slickdeals.net/" if r < 0.64 else "")
        return None, None, None, None, ref
    return None, None, None, None, ""

def make_order(d: date, cust: Customer, kind: str, channel: str, adset: int | None = None,
               code: str | None = None, discount_pct: float = 0.0) -> Order:
    global _oid
    _oid += 1
    local = local_checkout_time(d, kind)
    created = local_to_utc(local)
    sub = kind == "renewal" or (kind == "first" and cust.subscriber)
    promo = promo_for(d)
    lines = pick_lines(kind, sub, promo is not None and code == (promo.code if promo else None), channel == "coupon_leak")
    subtotal = round(sum(q * p for _, _, _, q, p in lines), 2)
    discounts = 0.0
    if sub:
        discounts = round(subtotal * SUB_DISCOUNT, 2); code = None; discount_pct = SUB_DISCOUNT
    elif code:
        discounts = round(subtotal * discount_pct, 2)
    total = round(subtotal - discounts, 2)
    utm_c, utm_s, utm_m, utm_ct, ref = utm_for(channel, d, adset)
    if kind == "renewal":
        utm_c, utm_s, utm_m, utm_ct, ref = None, None, None, None, ""
    tags = []
    if sub and kind == "first":
        tags.append("Subscription First Order")
    if kind == "renewal":
        tags.append("Subscription Recurring Order")
    ship = 0.0 if (total >= 75 or kind == "renewal") else (7.95 if d < date(2026, 2, 1) else 8.95)
    tax = round(total * tax_rate(cust.city_idx), 2)
    o = Order(id=_oid, created_at=created, customer_id=cust.id, kind=kind, channel=channel,
              utm_campaign=utm_c, utm_source=utm_s, utm_medium=utm_m, utm_content=utm_ct, referring_site=ref,
              source_name="subscription_contract" if kind == "renewal" else "web",
              tags=", ".join(tags), discount_code=code, discount_pct=discount_pct, city_idx=cust.city_idx,
              lines=lines, subtotal=subtotal, discounts=discounts, total=total, tax=tax, shipping=ship,
              total_price=round(total + tax + ship, 2))
    cust.orders += 1
    cust.spent = round(cust.spent + o.total_price, 2)
    cust.last_order_at = created
    cust.last_day = (d - LAUNCH).days
    if cust.first_order_at is None:
        cust.first_order_at = created
        cust.first_day = cust.last_day
        cust.created_at = created - timedelta(seconds=int(rng.integers(5, 240)))   # Shopify creates the customer at checkout
    orders.append(o)
    return o

# ----------------------------------------------------------------------------
# Simulation
# ----------------------------------------------------------------------------
daily: list[dict] = []
_cum_meta_spend: list[float] = []

for di, d in enumerate(DAYS):
    promo = promo_for(d)
    lift = promo.lift if promo else 1.0
    season = season_demand(d)
    scale = brand_scale(d)
    spend = meta_spend_for(d)
    _cum_meta_spend.append(spend)
    prospecting_spend = spend * (0.80 - 0.04 * win_frac(d))
    retargeting_spend = spend - prospecting_spend

    # New customers (truth)
    n_new_meta = int(rng.poisson(spend / true_new_cac_meta(d) * season))
    n_new_brand = int(rng.poisson(3.2 * scale * season * lift * dow_demand(d)))
    n_new_organic = int(rng.poisson(4.4 * scale * (1 + 0.12 * win_frac(d)) * season * lift * dow_demand(d)))
    n_new_email = int(rng.poisson(1.1 * scale * lift))
    seeding_drop = d.day in (3, 4, 5, 17, 18, 19)
    n_new_infl = int(rng.poisson((2.4 if seeding_drop else 0.9) * (0.4 + 0.6 * scale)))
    n_new_leak = 0
    if d >= CODE_LEAK_FROM:
        ramp = min(1.0, (d - CODE_LEAK_FROM).days / 12)
        n_new_leak = int(rng.poisson(12 * ramp * dow_demand(d)))

    new_today: list[Order] = []

    def first_order_code(channel: str) -> tuple[str | None, float]:
        if promo and rng.random() < (0.72 if channel != "meta" else 0.55):
            return promo.code, promo.pct
        welcome_p = 0.30 if channel in ("organic", "google_brand", "email") else (0.10 if channel == "meta" else 0.0)
        if rng.random() < welcome_p:
            return "WELCOME10", 0.10
        return None, 0.0

    def add_new(n: int, channel: str, adset_pool=None):
        for _ in range(n):
            c = new_customer(datetime.min, channel)
            take = 0.19 if channel in ("meta", "organic", "google_brand", "email") else (0.10 if channel == "influencer" else 0.03)
            if promo and promo.lift >= 2:
                take *= 0.6     # sale buyers subscribe less
            if rng.random() < take:
                c.subscriber = True
                c.sub_next = d + timedelta(days=30)
            adset = int(rng.choice(adset_pool, p=[0.7, 0.3])) if adset_pool is not None else None
            code, pct = first_order_code(channel)
            if c.subscriber:
                code, pct = None, 0.0
            o = make_order(d, c, "first", channel, adset=adset, code=code, discount_pct=pct)
            if channel == "meta":
                o.meta_claims = True; o.meta_adset = adset
            new_today.append(o)

    add_new(n_new_meta, "meta", adset_pool=[1101, 1102])
    add_new(n_new_brand, "google_brand")
    add_new(n_new_organic, "organic")
    add_new(n_new_email, "email")
    for _ in range(n_new_infl):
        c = new_customer(datetime.min, "influencer")
        if rng.random() < 0.12:
            c.subscriber = True; c.sub_next = d + timedelta(days=30)
        use_code = rng.random() < 0.65 and not c.subscriber
        o = make_order(d, c, "first", "influencer", code="FERN20" if use_code else None, discount_pct=0.20 if use_code else 0.0)
        new_today.append(o)
    for _ in range(n_new_leak):
        c = new_customer(datetime.min, "coupon_leak")
        if rng.random() < 0.03:
            c.subscriber = True; c.sub_next = d + timedelta(days=30)
        o = make_order(d, c, "first", "coupon_leak", code=None if c.subscriber else "FERN20", discount_pct=0.0 if c.subscriber else 0.20)
        new_today.append(o)

    # Meta's view-through / 7-day-click window also claims some new customers other channels earned
    for o in new_today:
        if o.channel in ("organic", "google_brand", "email", "influencer") and rng.random() < 0.15:
            o.meta_claims = True; o.meta_adset = int(rng.choice([1101, 1102], p=[0.7, 0.3]))
        elif o.channel == "coupon_leak" and rng.random() < 0.10:
            o.meta_claims = True; o.meta_adset = 1101

    # Subscription renewals due today
    renewals_today: list[Order] = []
    due_in_3 = 0
    for c in customers:
        if not c.subscriber or c.sub_next is None:
            continue
        if c.sub_next == d + timedelta(days=3):
            due_in_3 += 1
        if c.sub_next <= d:
            churn = {0: 0.14, 1: 0.10, 2: 0.08}.get(c.sub_cycles, 0.065)
            if c.sub_cycles >= 6:
                churn = 0.045
            if c.source == "coupon_leak":
                churn = 0.35
            if rng.random() < churn:
                c.subscriber = False; c.sub_next = None
                continue
            o = make_order(d, c, "renewal", "direct")
            c.sub_cycles += 1
            c.sub_next = d + timedelta(days=int(rng.choice([29, 30, 30, 31, 32], p=[0.1, 0.4, 0.2, 0.2, 0.1])))
            renewals_today.append(o)

    # One-time repeat orders: recency-decaying hazard, promo and send-day lifts
    repeat_today: list[Order] = []
    n_cust = len(customers)
    if n_cust:
        last = np.fromiter((c.last_day for c in customers), dtype=np.int64, count=n_cust)
        is_sub = np.fromiter((c.subscriber for c in customers), dtype=bool, count=n_cust)
        delta = di - last
        eligible = delta >= 14
        h = (0.0049 * np.exp(-delta / 80.0) + 0.00024) * season * dow_demand(d)
        h = h * np.where(is_sub, 0.35, 1.0)
        if promo:
            h = h * (1.0 + 0.9 * (promo.lift - 1.0))
        elif d.weekday() in (1, 4):          # campaign send days
            h = h * 1.25
        h = np.where(eligible, h, 0.0)
        hits = np.nonzero(rng.random(n_cust) < h)[0]
        for i in hits:
            c = customers[int(i)]
            r = rng.random()
            if promo:
                ch = "email" if r < 0.55 else ("meta" if r < 0.70 else ("google_brand" if r < 0.80 else ("organic" if rng.random() < 0.5 else "direct")))
            else:
                ch = "email" if r < 0.34 else ("meta" if r < 0.52 else ("google_brand" if r < 0.64 else ("organic" if rng.random() < 0.5 else "direct")))
            adset = int(rng.choice([1103, 1104], p=[0.78, 0.22])) if ch == "meta" else None
            code, pct = (promo.code, promo.pct) if (promo and rng.random() < 0.75) else (None, 0.0)
            o = make_order(d, c, "repeat", ch, adset=adset, code=code, discount_pct=pct)
            if ch == "meta":
                o.meta_claims = True; o.meta_adset = adset
            if ch == "email":
                o.klaviyo_claims = True
            repeat_today.append(o)

    # Meta's attribution window claims a slice of renewals and non-Meta repeats (warm ads were seen)
    for o in renewals_today:
        if rng.random() < 0.20:
            o.meta_claims = True; o.meta_adset = 1103
    for o in repeat_today:
        if not o.meta_claims and rng.random() < 0.12:
            o.meta_claims = True; o.meta_adset = int(rng.choice([1103, 1104], p=[0.85, 0.15]))
    # Klaviyo claims flows on renewals (reminder emails) and some new orders (welcome / abandoned cart)
    for o in renewals_today:
        if rng.random() < 0.41:
            o.klaviyo_claims = True; o.klaviyo_name = "Flow: Subscription Renewal Reminder"
    send_day = promo is not None or d.weekday() in (1, 4)
    for o in repeat_today:
        if o.klaviyo_claims:
            o.klaviyo_name = "Campaign" if (send_day and rng.random() < 0.72) else "Flow: Winback 45d"
    for o in new_today:
        if rng.random() < 0.17:
            if rng.random() < 0.7:
                o.klaviyo_claims = True; o.klaviyo_name = "Flow: Abandoned Cart"
                if o.discount_code is None and o.kind == "first" and "Subscription" not in o.tags and rng.random() < 0.55:
                    o.discount_code = "SAVE10"; o.discount_pct = 0.10
                    o.discounts = round(o.subtotal * 0.10, 2); o.total = round(o.subtotal - o.discounts, 2)
                    o.tax = round(o.total * tax_rate(o.city_idx), 2)
                    o.shipping = 0.0 if o.total >= 75 else o.shipping
                    o.total_price = round(o.total + o.tax + o.shipping, 2)
            else:
                o.klaviyo_claims = True; o.klaviyo_name = "Flow: Welcome Series"

    daily.append(dict(d=d, spend=spend, prospecting_spend=prospecting_spend, retargeting_spend=retargeting_spend,
                      n_new_meta=n_new_meta, new=new_today, renewals=renewals_today, repeats=repeat_today,
                      due_in_3=due_in_3, promo=promo))

# Refunds, cancellations, fulfillment lag (post-process; platforms still count these orders)
for o in orders:
    r = rng.random()
    if r < 0.005:
        o.financial_status = "voided" if rng.random() < 0.4 else "refunded"
        o.fulfillment_status = None
        o.cancelled_at = o.created_at + timedelta(hours=float(rng.uniform(0.2, 30)))
        o.updated_at = o.cancelled_at
        continue
    if r < 0.017:
        o.financial_status = "refunded"
    elif r < 0.024:
        o.financial_status = "partially_refunded"
    lag_days = float(rng.choice([0.3, 1.1, 1.6, 2.2, 3.4, 5.0], p=[0.12, 0.38, 0.25, 0.15, 0.07, 0.03]))
    fulfilled_at = o.created_at + timedelta(days=lag_days)
    end_utc = datetime.combine(END, datetime.min.time()) + timedelta(hours=23)
    if fulfilled_at > end_utc:
        o.fulfillment_status = None if (end_utc - o.created_at).days < 1 else ("partial" if rng.random() < 0.15 else None)
        o.updated_at = o.created_at + timedelta(minutes=int(rng.integers(1, 40)))
    else:
        o.updated_at = fulfilled_at
        if o.financial_status in ("refunded", "partially_refunded"):
            o.updated_at = fulfilled_at + timedelta(days=float(rng.uniform(2, 20)))

# Order ids / numbers: strictly increasing in time, like Shopify
orders.sort(key=lambda o: o.created_at)
_base_id = 5_600_000_000
_num = 1000
for o in orders:
    _base_id += int(rng.integers(1, 4)) * 1000 + int(rng.integers(0, 1000))
    _num += 1
    o.id = _base_id; o.number = _num

# Reconcile customers (orders_count, total_spent, timestamps) from actual orders
by_cust: dict[int, list[Order]] = defaultdict(list)
for o in orders:
    by_cust[o.customer_id].append(o)
for c in customers:
    os_ = by_cust.get(c.id, [])
    c.orders = len(os_)
    # Shopify total_spent is net of refunds; orders_count still counts cancelled orders
    c.spent = round(sum(o.total_price * (0.0 if o.financial_status in ("refunded", "voided") else (0.6 if o.financial_status == "partially_refunded" else 1.0))
                        for o in os_), 2)
    if os_:
        c.first_order_at = os_[0].created_at
        c.last_order_at = os_[-1].created_at

print(f"customers: {len(customers):,}  orders: {len(orders):,}")

# ----------------------------------------------------------------------------
# Meta Ads insights (what Ads Manager reports), daily + weekly, window only
# ----------------------------------------------------------------------------
meta_rows: list[dict] = []
_weekly_acc: dict[tuple[date, int], dict] = {}

def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())

for day in daily:
    d = day["d"]
    if d < WINDOW_START:
        continue
    t = win_frac(d)
    fat = min(1.0, (d - FATIGUE_FROM).days / 50) if d >= FATIGUE_FROM else 0.0
    claimed = [o for o in (day["new"] + day["renewals"] + day["repeats"]) if o.meta_claims]
    by_adset: dict[int, list[Order]] = defaultdict(list)
    for o in claimed:
        by_adset[o.meta_adset].append(o)

    for adset_id, (adset_name, camp_id, camp_name, _old, kind) in ADSETS.items():
        ads = live_ads(adset_id, d)
        if not ads:
            continue
        if kind == "prospecting":
            adset_spend = day["prospecting_spend"] * (0.70 if adset_id == 1101 else 0.30)
        else:
            adset_spend = day["retargeting_spend"] * (0.88 if adset_id == 1103 else 0.12)
        # delivery weights: Meta concentrates on the historic winner; buyer keeps feeding it
        w = np.array([a.base_share for a in ads], dtype=float)
        for i, a in enumerate(ads):
            if a.fatigue:
                w[i] = 0.50 + 0.30 * t
            age = (d - a.start).days
            if age < 7:
                w[i] *= 0.45 + 0.08 * age          # learning phase ramps delivery
        w = w * rng.lognormal(0.0, 0.30, len(ads))
        w = w / w.sum()
        # conversion weight per dollar
        q = np.array([a.quality for a in ads], dtype=float) * w
        for i, a in enumerate(ads):
            if a.fatigue:
                q[i] *= (1 - 0.45 * fat)
            if (d - a.start).days < 7:
                q[i] *= 0.6
        q = q / q.sum() if q.sum() > 0 else w
        adset_orders = by_adset.get(adset_id, [])
        assign = rng.multinomial(len(adset_orders), q) if adset_orders else np.zeros(len(ads), dtype=int)
        idx = 0
        for i, a in enumerate(ads):
            sp = float(adset_spend * w[i])
            mine = adset_orders[idx: idx + int(assign[i])]; idx += int(assign[i])
            purchases = len(mine)
            value = round(sum(o.total for o in mine), 2)
            age = (d - a.start).days
            cpm = a.base_cpm * (1 + 0.22 * t) * season_cpm(d) * noise(0.12) * (1.25 if age < 5 else 1.0)
            impressions = int(sp / cpm * 1000)
            ctr = a.base_ctr * noise(0.12)
            if a.fatigue:
                ctr *= (1 - 0.52 * fat)
            if kind == "prospecting":
                dfreq = 1.08 + 0.18 * t + (0.65 * fat if a.fatigue else 0.0)
            else:
                dfreq = 1.45 + 0.55 * t
            dfreq *= noise(0.04)
            clicks = int(impressions * ctr)
            link_clicks = int(clicks * float(np.clip(rng.normal(0.86, 0.03), 0.7, 0.95)))
            reach = int(impressions / dfreq)
            lpv = int(link_clicks * float(np.clip(rng.normal(0.78, 0.04), 0.6, 0.9)))
            ic = int(round(purchases * float(rng.uniform(1.4, 2.0)) + rng.poisson(0.6)))
            atc = int(round(ic * float(rng.uniform(1.7, 2.5)) + rng.poisson(1.0)))
            ic = max(ic, purchases); atc = max(atc, ic)
            # PLANTED: double-fired purchase pixel from Jun 12. The Shopify channel sends every standard event.
            rep_purch, rep_val, rep_atc, rep_ic = purchases, value, atc, ic
            if d >= PIXEL_DOUBLE_FIRE_FROM:
                mult = 1.62 + float(rng.normal(0, 0.03))
                rep_purch = int(round(purchases * mult)); rep_val = round(value * mult, 2)
                rep_atc = int(round(atc * mult)); rep_ic = int(round(ic * mult))
            row = dict(
                date_start=d.isoformat(), account_id="act_2210094471", campaign_id=camp_id, campaign_name=camp_name,
                adset_id=adset_id, adset_name=adset_name, ad_id=a.ad_id, ad_name=a.name, objective="OUTCOME_SALES",
                spend=round(sp, 2), impressions=impressions, reach=reach, frequency=round(dfreq, 2),
                clicks=clicks, inline_link_clicks=link_clicks,
                ctr=round(100 * clicks / impressions, 4) if impressions else 0,
                cpc=round(sp / clicks, 4) if clicks else 0, cpm=round(1000 * sp / impressions, 4) if impressions else 0,
                purchases=rep_purch, purchase_value=rep_val, purchase_roas=round(rep_val / sp, 4) if sp else 0,
                landing_page_views=lpv, add_to_cart=rep_atc, initiate_checkout=rep_ic,
            )
            meta_rows.append(row)
            # weekly accumulation with a proper 7-day frequency (reach is not additive across days)
            if kind == "prospecting":
                wfreq = (2.0 + 0.5 * t + 2.5 * fat) if a.fatigue else (1.9 + 0.4 * t)
            else:
                wfreq = 3.4 + 1.1 * t
            k = (week_start(d), a.ad_id)
            acc = _weekly_acc.setdefault(k, dict(spend=0.0, impressions=0, clicks=0, link=0, purchases=0, value=0.0, wfreq=[], a=a, n=0))
            acc["spend"] += sp; acc["impressions"] += impressions; acc["clicks"] += clicks; acc["link"] += link_clicks
            acc["purchases"] += rep_purch; acc["value"] += rep_val; acc["wfreq"].append(wfreq); acc["n"] += 1

meta_weekly_rows: list[dict] = []
for (ws, ad_id), acc in sorted(_weekly_acc.items()):
    a = acc["a"]; adset_name, camp_id, camp_name, _o, _k = ADSETS[a.adset_id]
    wf = float(np.mean(acc["wfreq"])) * (acc["n"] / 7) ** 0.5 * noise(0.04)   # partial weeks have lower frequency
    wf = max(1.05, wf)
    reach = int(acc["impressions"] / wf)
    meta_weekly_rows.append(dict(
        week_start=ws.isoformat(), week_end=(ws + timedelta(days=6)).isoformat(), account_id="act_2210094471",
        campaign_id=camp_id, campaign_name=camp_name, adset_id=a.adset_id, adset_name=adset_name, ad_id=ad_id, ad_name=a.name,
        spend=round(acc["spend"], 2), impressions=acc["impressions"], reach=reach, frequency=round(wf, 2),
        clicks=acc["clicks"], inline_link_clicks=acc["link"],
        ctr=round(100 * acc["clicks"] / acc["impressions"], 4) if acc["impressions"] else 0,
        purchases=acc["purchases"], purchase_value=round(acc["value"], 2),
        purchase_roas=round(acc["value"] / acc["spend"], 4) if acc["spend"] else 0,
    ))

# ----------------------------------------------------------------------------
# Google Ads (brand only). Brand search demand follows awareness (trailing Meta spend) and season.
# ----------------------------------------------------------------------------
gads_rows: list[dict] = []
for di, day in enumerate(daily):
    d = day["d"]
    if d < WINDOW_START:
        continue
    trailing = sum(_cum_meta_spend[max(0, di - 30): di]) / 30
    awareness = trailing / 920
    promo = day["promo"]
    brand_orders = [o for o in (day["new"] + day["repeats"]) if o.channel == "google_brand"]
    impressions = int(rng.poisson(190 * awareness * season_demand(d) * dow_demand(d) * (1.5 if promo else 1.0)))
    ctr = float(np.clip(rng.normal(0.31, 0.03), 0.2, 0.42))
    clicks = int(rng.binomial(impressions, ctr)) if impressions else 0
    cpc = float(np.clip(rng.normal(1.62, 0.12), 1.1, 2.3)) * (1 + 0.10 * win_frac(d))
    cost = round(clicks * cpc, 2)
    conv = round(len(brand_orders) * float(np.clip(rng.normal(0.94, 0.06), 0.7, 1.1)) + float(rng.poisson(0.4)), 1)
    gads_rows.append(dict(
        segments_date=d.isoformat(), customer_id="814-220-9931", campaign_id=20994410211,
        campaign_name="Brand | Exact | US", campaign_status="ENABLED", advertising_channel_type="SEARCH",
        metrics_cost_micros=int(cost * 1_000_000), metrics_impressions=impressions, metrics_clicks=clicks,
        metrics_conversions=conv,
        metrics_conversions_value=round(sum(o.total for o in brand_orders) * float(np.clip(rng.normal(0.94, 0.06), 0.7, 1.1)), 2),
        metrics_search_impression_share=round(float(np.clip(rng.normal(0.88 - (0.06 if promo else 0), 0.03), 0.6, 0.98)), 4),
    ))

# ----------------------------------------------------------------------------
# Klaviyo: list grows with opt-ins, shrinks with unsubscribes. Campaigns Tue/Fri + promo days.
# Flow recipients come from their actual triggers.
# ----------------------------------------------------------------------------
CAMPAIGN_SUBJECTS = [
    "Weekend spritz, no hangover", "Three ways to pour Rosemary Fig", "Why we use no sugar (and what we use instead)",
    "Smoked Pear is back in stock", "The 5pm ritual, reimagined", "Meet the adaptogens in your glass", "Host a zero-proof dinner party",
    "What customers say after 30 days", "Trio 3-Pack: one of each", "Behind the label: our founder's story",
    "New recipe: the Halcyon Negroni", "Sober curious? Start here", "A bottle for every mood", "Free shipping on orders over $75",
    "Your questions, answered", "Golden hour, bottled", "How to taste an aperitivo", "Gift a bottle, get a thank-you",
    "Subscribe and save 15%", "From Austin with love", "The citrus one, explained", "Pairing guide: aperitivo and small plates",
    "Last call for this week's drop", "Restock alert", "A note from the founder",
]

klaviyo_rows: list[dict] = []
list_size = 0.0
_subj_i = 0
klaviyo_clicks_by_day: dict[date, int] = {}
for di, day in enumerate(daily):
    d = day["d"]
    promo = day["promo"]
    new_today = day["new"]
    # opt-ins: new customers who accept marketing + popup signups proportional to site traffic
    optins = int(rng.binomial(len(new_today), 0.82)) + int(rng.poisson(9 * brand_scale(d) * (1.6 if promo else 1.0)))
    list_size += optins
    if d < WINDOW_START:
        # still run unsubscribes on send days so the list is realistic by the window
        if promo or d.weekday() in (1, 4):
            list_size -= list_size * 0.0021
        continue

    claimed = [o for o in (new_today + day["renewals"] + day["repeats"]) if o.klaviyo_claims]
    by_name: dict[str, list[Order]] = defaultdict(list)
    for o in claimed:
        by_name[o.klaviyo_name or "Campaign"].append(o)
    for name in ("Flow: Welcome Series", "Flow: Abandoned Cart", "Flow: Winback 45d", "Flow: Subscription Renewal Reminder"):
        by_name.setdefault(name, [])
    day_clicks = 0

    # Flows: recipients from triggers
    purchases_today = len(new_today) + len(day["repeats"])
    atc_est = int(purchases_today * float(rng.uniform(3.2, 4.4)))
    flow_recipients = {
        "Flow: Welcome Series": max(1, int(optins * float(np.clip(rng.normal(0.95, 0.05), 0.8, 1.0)))),
        "Flow: Abandoned Cart": max(1, int((atc_est - purchases_today) * float(np.clip(rng.normal(0.36, 0.05), 0.2, 0.5)))),
        "Flow: Subscription Renewal Reminder": max(1, day["due_in_3"] + int(rng.poisson(1.5))),
        "Flow: Winback 45d": max(1, sum(1 for c in customers if c.last_day == di - 45 and not c.subscriber and c.email_opt_in)),
    }
    flow_rates = {
        "Flow: Welcome Series": (0.52, 0.12), "Flow: Abandoned Cart": (0.44, 0.14),
        "Flow: Subscription Renewal Reminder": (0.58, 0.06), "Flow: Winback 45d": (0.33, 0.05),
    }
    for name, recipients in flow_recipients.items():
        os_ = by_name[name]
        o_rate, c_rate = flow_rates[name]
        opens = int(rng.binomial(recipients, float(np.clip(rng.normal(o_rate, 0.04), 0.1, 0.8))))
        clicks = int(rng.binomial(opens, float(np.clip(rng.normal(c_rate, 0.02), 0.01, 0.5)))) if opens else 0
        day_clicks += clicks
        over = 1.18
        klaviyo_rows.append(dict(
            date=d.isoformat(), message_type="flow", message_name=name, recipients=recipients, opens=opens, clicks=clicks,
            attributed_orders=int(round(len(os_) * over)), attributed_revenue=round(sum(o.total for o in os_) * over, 2),
            unsubscribes=int(rng.binomial(recipients, 0.004)),
        ))

    # Campaigns
    send_day = promo is not None or d.weekday() in (1, 4)
    if send_day:
        if promo:
            dayn = (d - promo.start).days
            name = promo.name if dayn == 0 else (f"{promo.name} - ends tonight" if d == promo.end else f"{promo.name} - still on")
            name = f"{name} ({d.isoformat()})"
        else:
            name = f"{CAMPAIGN_SUBJECTS[_subj_i % len(CAMPAIGN_SUBJECTS)]} ({d.isoformat()})"; _subj_i += 1
        recipients = int(list_size * float(np.clip(rng.normal(0.965, 0.008), 0.93, 0.99)))
        opens = int(rng.binomial(recipients, float(np.clip(rng.normal(0.33 if not promo else 0.38, 0.03), 0.1, 0.7))))
        clicks = int(rng.binomial(opens, float(np.clip(rng.normal(0.055 if not promo else 0.085, 0.012), 0.01, 0.3))))
        day_clicks += clicks
        os_ = by_name.get("Campaign", [])
        unsubs = int(rng.binomial(recipients, 0.0021 if not promo else 0.0032))
        list_size -= unsubs
        # Klaviyo's 5-day open-or-click attribution also claims orders from openers who bought via any channel
        nxt = daily[di + 1] if di + 1 < len(daily) else None
        pool_repeats = len(day["repeats"]) + (len(nxt["repeats"]) if nxt else 0)
        pool_new = len(new_today) + (len(nxt["new"]) if nxt else 0)
        extra = int(rng.binomial(pool_repeats, 0.24)) + int(rng.binomial(pool_new, 0.03))
        extra_rev = sum(float(np.clip(rng.normal(74, 22), 33, 200)) for _ in range(extra))
        klaviyo_rows.append(dict(
            date=d.isoformat(), message_type="campaign", message_name=name, recipients=recipients, opens=opens, clicks=clicks,
            attributed_orders=len(os_) + extra, attributed_revenue=round(sum(o.total for o in os_) + extra_rev, 2),
            unsubscribes=unsubs,
        ))
    else:
        # email-channel orders on non-send days get attributed to flows by Klaviyo; already bucketed as winback
        pass
    klaviyo_clicks_by_day[d] = day_clicks

# ----------------------------------------------------------------------------
# GA4 sessions by source / medium / campaign (last click). Sessions come from traffic, purchases from
# orders GA4 actually saw. Subscription renewals are server-side charges and never reach GA4.
# ----------------------------------------------------------------------------
ga4_rows: list[dict] = []
_meta_link_by_day_camp: dict[tuple[date, int], int] = defaultdict(int)
for r in meta_rows:
    _meta_link_by_day_camp[(date.fromisoformat(r["date_start"]), r["adset_id"])] += r["inline_link_clicks"]

def ga_key(o: Order) -> tuple[str, str, str]:
    if o.channel == "meta":
        src = "facebook" if "facebook" in o.referring_site else "instagram"
        return (src, "paid_social", o.utm_campaign or "(not set)")
    if o.channel == "google_brand":
        return ("google", "cpc", "brand_exact")
    if o.channel == "email" or (o.klaviyo_claims and o.kind != "renewal" and o.channel == "direct"):
        return ("klaviyo", "email", o.klaviyo_name or "(not set)")
    if o.channel == "organic":
        src = "google" if "google" in o.referring_site else ("bing" if "bing" in o.referring_site else "duckduckgo")
        return (src, "organic", "(not set)")
    if o.channel == "coupon_leak":
        for host in ("retailmenot.com", "couponfollow.com", "dealspotr.com", "slickdeals.net"):
            if host.split(".")[0] in o.referring_site:
                return (host, "referral", "(not set)")
        return ("(direct)", "(none)", "(not set)")
    if o.channel == "influencer":
        return ("instagram.com", "referral", "(not set)") if o.referring_site else ("(direct)", "(none)", "(not set)")
    return ("(direct)", "(none)", "(not set)")

ENGAGED = {"paid_social": 0.42, "cpc": 0.66, "email": 0.64, "organic": 0.61, "(none)": 0.58, "referral": 0.50}
NEWUSER = {"paid_social": 0.80, "cpc": 0.44, "email": 0.14, "organic": 0.62, "(none)": 0.36, "referral": 0.72}
ATC_RATE = {"paid_social": 0.028, "cpc": 0.14, "email": 0.075, "organic": 0.055, "(none)": 0.065, "referral": 0.05}

for di, day in enumerate(daily):
    d = day["d"]
    if d < WINDOW_START:
        continue
    promo = day["promo"]
    scale = brand_scale(d) * season_demand(d) * dow_demand(d) * (1.0 + 0.5 * ((promo.lift - 1) if promo else 0))
    buckets: dict[tuple, dict] = {}
    def bucket(k):
        return buckets.setdefault(k, dict(sessions=0, purchases=0, revenue=0.0))
    # purchases GA4 saw (renewals excluded; paid clicks sometimes lose attribution to direct on iOS)
    for o in day["new"] + day["repeats"]:
        if rng.random() > 0.93:
            continue
        k = ga_key(o)
        if k[1] == "paid_social" and rng.random() < 0.15:
            k = ("(direct)", "(none)", "(not set)")
        b = bucket(k); b["purchases"] += 1; b["revenue"] += o.total
    # sessions from traffic sources
    for adset_id in ADSETS:
        link = _meta_link_by_day_camp.get((d, adset_id), 0)
        camp = utm_campaign_for(adset_id, d)
        sess = int(link * float(np.clip(rng.normal(0.84, 0.05), 0.6, 0.98)))
        fb = int(sess * float(np.clip(rng.normal(0.52, 0.04), 0.4, 0.65)))
        bucket(("facebook", "paid_social", camp))["sessions"] += fb
        bucket(("instagram", "paid_social", camp))["sessions"] += sess - fb
    g = next((r for r in gads_rows if r["segments_date"] == d.isoformat()), None)
    if g:
        bucket(("google", "cpc", "brand_exact"))["sessions"] += int(g["metrics_clicks"] * float(np.clip(rng.normal(0.9, 0.04), 0.7, 1.0)))
    kc = klaviyo_clicks_by_day.get(d, 0)
    email_sess = int(kc * float(np.clip(rng.normal(0.92, 0.04), 0.7, 1.0)))
    # split email sessions across the klaviyo campaign names that exist in buckets today, else generic
    email_keys = [k for k in buckets if k[1] == "email"] or [("klaviyo", "email", "(not set)")]
    for k in email_keys:
        bucket(k)["sessions"] += email_sess // len(email_keys)
    org = int(rng.poisson(330 * scale))
    bucket(("google", "organic", "(not set)"))["sessions"] += int(org * 0.86)
    bucket(("bing", "organic", "(not set)"))["sessions"] += int(org * 0.09)
    bucket(("duckduckgo", "organic", "(not set)"))["sessions"] += org - int(org * 0.86) - int(org * 0.09)
    bucket(("(direct)", "(none)", "(not set)"))["sessions"] += int(rng.poisson(620 * scale))
    bucket(("instagram.com", "referral", "(not set)"))["sessions"] += int(rng.poisson(45 * scale * (2.2 if d.day in (3, 4, 5, 17, 18, 19) else 1.0)))
    if d >= CODE_LEAK_FROM:
        ramp = min(1.0, (d - CODE_LEAK_FROM).days / 12)
        for host, base in (("retailmenot.com", 95), ("couponfollow.com", 55), ("dealspotr.com", 28), ("slickdeals.net", 22)):
            bucket((host, "referral", "(not set)"))["sessions"] += int(rng.poisson(base * ramp))
    for k, b in buckets.items():
        src, med, camp = k
        sessions = max(b["sessions"], b["purchases"] * int(rng.integers(3, 9)))
        if sessions == 0:
            continue
        eng = float(np.clip(rng.normal(ENGAGED.get(med, 0.55), 0.05), 0.2, 0.9))
        nu = float(np.clip(rng.normal(NEWUSER.get(med, 0.5), 0.05), 0.05, 0.95))
        atc = int(sessions * float(np.clip(rng.normal(ATC_RATE.get(med, 0.05), 0.012), 0.005, 0.3)))
        atc = max(atc, int(b["purchases"] * float(rng.uniform(1.6, 2.6))))
        ga4_rows.append(dict(
            date=d.isoformat(), property_id="properties/412009913", session_source=src, session_medium=med,
            session_campaign=camp, sessions=sessions, engaged_sessions=int(sessions * eng), new_users=int(sessions * nu),
            add_to_carts=atc, ecommerce_purchases=b["purchases"], purchase_revenue=round(b["revenue"], 2),
        ))

# ----------------------------------------------------------------------------
# Founder's Monday spreadsheet (their math, their mistakes). Started when the Meta budget got serious.
# ----------------------------------------------------------------------------
sheet_rows: list[dict] = []
ws = WINDOW_START - timedelta(days=WINDOW_START.weekday())
_meta_by_day: dict[str, list[dict]] = defaultdict(list)
for r in meta_rows:
    _meta_by_day[r["date_start"]].append(r)
_g_by_day = {r["segments_date"]: r for r in gads_rows}
_first_at = {c.id: c.first_order_at for c in customers}
while ws <= END:
    we = ws + timedelta(days=6)
    m = [r for dd in (ws + timedelta(days=i) for i in range(7)) for r in _meta_by_day.get(dd.isoformat(), [])]
    g = [_g_by_day[dd.isoformat()] for dd in (ws + timedelta(days=i) for i in range(7)) if dd.isoformat() in _g_by_day]
    # founder reads Shopify in store time, so bucket by local date
    os_ = [o for o in orders if ws <= (o.created_at - timedelta(hours=utc_offset_hours(o.created_at.date()))).date() <= we]
    meta_spend = round(sum(r["spend"] for r in m), 2)
    meta_purch = sum(r["purchases"] for r in m)
    meta_val = round(sum(r["purchase_value"] for r in m), 2)
    g_spend = round(sum(r["metrics_cost_micros"] for r in g) / 1e6, 2)
    shop_orders = len(os_)
    shop_rev = round(sum(o.total_price for o in os_), 2)       # gross, refunds not netted
    new_cust = sum(1 for o in os_ if _first_at.get(o.customer_id) == o.created_at)
    cac = round((meta_spend + g_spend) / meta_purch, 2) if meta_purch else None
    new_cac = round(meta_spend / new_cust, 2) if new_cust else None
    infl = round(meta_spend * 0.167 * float(np.clip(rng.normal(1.0, 0.18), 0.5, 1.6)), 2) if ws.day <= 7 or rng.random() < 0.5 else 0.0
    note = ""
    if date(2026, 6, 8) <= ws <= date(2026, 6, 14):
        note = "installed shopify meta channel"
    elif date(2026, 7, 13) <= ws <= date(2026, 7, 19):
        note = "renamed campaigns per agency"
    elif date(2026, 8, 10) <= ws <= date(2026, 8, 23):
        note = "FERN20 doing great?? orders up"
    elif date(2026, 5, 18) <= ws <= date(2026, 5, 24):
        note = "memorial day sale"
    elif date(2026, 8, 31) <= ws <= date(2026, 9, 6):
        note = "labor day sale"
    sheet_rows.append(dict(
        week_of=ws.isoformat(), meta_spend=meta_spend, google_spend=g_spend, influencer_spend=infl,
        meta_purchases_reported=meta_purch, meta_roas_reported=round(meta_val / meta_spend, 2) if meta_spend else None,
        shopify_orders=shop_orders, shopify_revenue=shop_rev, shopify_new_customers=new_cust,
        blended_cac_their_calc=cac, meta_cac_new_their_calc=new_cac, notes=note,
    ))
    ws += timedelta(days=7)

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
_line_id = 9_100_000_000
for o in orders:
    c = cust_by_id[o.customer_id]
    landing = "/"
    if o.utm_source:
        landing = f"/?utm_source={o.utm_source}&utm_medium={o.utm_medium}"
        if o.utm_campaign:
            landing += f"&utm_campaign={quote(o.utm_campaign, safe='')}"
        if o.utm_content:
            landing += f"&utm_content={o.utm_content}"
        if o.channel == "meta":
            landing += f"&fbclid={fbclid()}"
    elif o.channel == "coupon_leak":
        landing = "/products/the-trio-3-pack" if rng.random() < 0.5 else ("/collections/all" if rng.random() < 0.6 else "/discount/FERN20")
    elif o.channel == "organic" and rng.random() < 0.4:
        landing = rng.choice(["/products/rosemary-fig-aperitivo-750ml", "/products/bitter-citrus-aperitivo-750ml",
                              "/products/smoked-pear-aperitivo-750ml", "/pages/our-story", "/collections/all"])
    city, st, _ = CITIES[o.city_idx]
    shop_orders_rows.append(dict(
        id=o.id, order_number=o.number, name=f"#{o.number}", created_at=iso(o.created_at),
        processed_at=iso(o.created_at + timedelta(seconds=int(rng.integers(1, 6)))), updated_at=iso(o.updated_at),
        customer_id=o.customer_id, email=f"customer{o.customer_id}@example.com",
        financial_status=o.financial_status, fulfillment_status=o.fulfillment_status,
        currency="USD", subtotal_price=o.subtotal, total_discounts=o.discounts, total_tax=o.tax,
        total_shipping=o.shipping, total_price=o.total_price,
        discount_code=o.discount_code, source_name=o.source_name, tags=o.tags,
        landing_site=landing, referring_site=o.referring_site, shipping_city=city, shipping_province_code=st,
        cancelled_at=iso(o.cancelled_at), test=False,
    ))
    for pid, sku, title, qty, price in o.lines:
        _line_id += int(rng.integers(1, 3))
        shop_lines_rows.append(dict(id=_line_id, order_id=o.id, product_id=pid, variant_id=pid * 10 + 1, sku=sku, title=title,
                                    quantity=qty, price=price, total_discount=round(qty * price * o.discount_pct, 2)))

shop_customers_rows = []
for c in customers:
    if c.orders == 0:
        continue
    city, st, _ = CITIES[c.city_idx]
    tags = []
    if c.subscriber:
        tags.append("Active Subscriber")
    elif c.sub_cycles > 0:
        tags.append("Churned Subscriber")
    if c.spent >= 500:
        tags.append("VIP")
    shop_customers_rows.append(dict(
        id=c.id, email=f"customer{c.id}@example.com", created_at=iso(c.created_at),
        updated_at=iso(max(c.last_order_at, c.created_at) + timedelta(days=float(rng.uniform(0.5, 3)))),
        orders_count=c.orders, total_spent=round(c.spent, 2), state=c.state, accepts_marketing=c.email_opt_in,
        default_address_city=city, default_address_province_code=st, default_address_country_code="US",
        tags=", ".join(tags), first_order_at=iso(c.first_order_at), last_order_at=iso(c.last_order_at),
    ))

shop_products_rows = [dict(id=pid, title=title, handle=title.lower().replace(" ", "-"), product_type="Aperitivo" if "Pack" not in title else "Bundle",
                           vendor="Halcyon Botanicals", status="active", created_at="2024-09-18 15:00:00", price=price, sku=sku)
                      for pid, sku, title, price, _ in PRODUCTS]

print("writing:")
write("shopify_orders", shop_orders_rows)
write("shopify_order_line_items", shop_lines_rows)
write("shopify_customers", shop_customers_rows)
write("shopify_products", shop_products_rows)
write("meta_ads_insights", meta_rows)
write("meta_ads_insights_weekly", meta_weekly_rows)
write("google_ads_campaign_stats", gads_rows)
write("ga4_traffic_acquisition", ga4_rows)
write("klaviyo_message_performance", klaviyo_rows)
write("founder_monday_sheet", sheet_rows)

# ----------------------------------------------------------------------------
# Sanity report (truth vs reported), window months
# ----------------------------------------------------------------------------
print("\nmonthly truth vs Ads Manager (window):")
print(f"{'month':8s} {'meta_spend':>11s} {'new_meta':>9s} {'true_CAC':>9s} {'AM_purch':>9s} {'AM_ROAS':>8s} {'shop_orders':>11s} {'shop_rev':>10s}")
for m in range(4, 11):
    rows = [r for r in meta_rows if r["date_start"][5:7] == f"{m:02d}"]
    sp = sum(r["spend"] for r in rows); pv = sum(r["purchase_value"] for r in rows); pu = sum(r["purchases"] for r in rows)
    new_meta = sum(day["n_new_meta"] for day in daily if day["d"].month == m and day["d"].year == 2026)
    os_ = [o for o in orders if o.created_at.year == 2026 and o.created_at.month == m]
    print(f"2026-{m:02d}  {sp:11,.0f} {new_meta:9d} {sp/new_meta if new_meta else 0:9.2f} {pu:9d} {pv/sp if sp else 0:8.2f} {len(os_):11,d} {sum(o.total_price for o in os_):10,.0f}")
