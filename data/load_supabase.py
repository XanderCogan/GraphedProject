"""
Load the generated CSVs into a Supabase Postgres database, schema `halcyon`.

Usage:
    python data/load_supabase.py            # reads SUPABASE_DB_URL from .env or the environment
    python data/load_supabase.py --drop     # drop and recreate the schema first

Graphed's Postgres connector then syncs these tables into the warehouse.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "out"
SCHEMA = "halcyon"

TABLES: dict[str, str] = {
    "shopify_orders": """
        id bigint primary key, order_number integer, name text, created_at timestamp, processed_at timestamp,
        updated_at timestamp, customer_id bigint, email text, financial_status text, fulfillment_status text,
        currency text, subtotal_price numeric(10,2), total_discounts numeric(10,2), total_tax numeric(10,2),
        total_shipping numeric(10,2), total_price numeric(10,2), discount_code text, source_name text, tags text,
        landing_site text, referring_site text, shipping_city text, shipping_province_code text,
        cancelled_at timestamp, test boolean
    """,
    "shopify_order_line_items": """
        id bigint primary key, order_id bigint, product_id bigint, variant_id bigint, sku text, title text,
        quantity integer, price numeric(10,2), total_discount numeric(10,2)
    """,
    "shopify_customers": """
        id bigint primary key, email text, created_at timestamp, updated_at timestamp, orders_count integer,
        total_spent numeric(12,2), state text, accepts_marketing boolean, default_address_city text,
        default_address_province_code text, default_address_country_code text, tags text,
        first_order_at timestamp, last_order_at timestamp
    """,
    "shopify_products": """
        id bigint primary key, title text, handle text, product_type text, vendor text, status text,
        created_at timestamp, price numeric(10,2), sku text
    """,
    "meta_ads_insights": """
        date_start date, account_id text, campaign_id bigint, campaign_name text, adset_id bigint, adset_name text,
        ad_id bigint, ad_name text, objective text, spend numeric(12,2), impressions bigint, reach bigint,
        frequency numeric(6,2), clicks bigint, inline_link_clicks bigint, ctr numeric(8,4), cpc numeric(10,4),
        cpm numeric(10,4), purchases integer, purchase_value numeric(12,2), purchase_roas numeric(10,4),
        landing_page_views bigint, add_to_cart bigint, initiate_checkout bigint,
        primary key (date_start, ad_id)
    """,
    "google_ads_campaign_stats": """
        segments_date date, customer_id text, campaign_id bigint, campaign_name text, campaign_status text,
        advertising_channel_type text, metrics_cost_micros bigint, metrics_impressions bigint, metrics_clicks bigint,
        metrics_conversions numeric(10,1), metrics_conversions_value numeric(12,2),
        metrics_search_impression_share numeric(6,4),
        primary key (segments_date, campaign_id)
    """,
    "ga4_traffic_acquisition": """
        date date, property_id text, session_source text, session_medium text, session_campaign text,
        sessions bigint, engaged_sessions bigint, new_users bigint, add_to_carts bigint, ecommerce_purchases bigint,
        purchase_revenue numeric(12,2),
        primary key (date, session_source, session_medium, session_campaign)
    """,
    "klaviyo_message_performance": """
        date date, message_type text, message_name text, recipients bigint, opens bigint, clicks bigint,
        attributed_orders integer, attributed_revenue numeric(12,2), unsubscribes integer,
        primary key (date, message_name)
    """,
    "founder_monday_sheet": """
        week_of date primary key, meta_spend numeric(12,2), google_spend numeric(12,2), meta_purchases_reported integer,
        meta_roas_reported numeric(8,2), shopify_orders integer, shopify_revenue numeric(12,2),
        blended_cac_their_calc numeric(10,2), notes text
    """,
}


def read_env() -> str:
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("SUPABASE_DB_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not url:
        sys.exit("SUPABASE_DB_URL not set. Copy .env.example to .env and fill it in.")
    return url


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true", help="drop and recreate the schema")
    args = ap.parse_args()

    url = read_env()
    with psycopg.connect(url, autocommit=False) as conn:
        with conn.cursor() as cur:
            if args.drop:
                cur.execute(f"drop schema if exists {SCHEMA} cascade")
            cur.execute(f"create schema if not exists {SCHEMA}")
            for table, ddl in TABLES.items():
                cur.execute(f"drop table if exists {SCHEMA}.{table}")
                cur.execute(f"create table {SCHEMA}.{table} ({ddl})")
                path = OUT / f"{table}.csv"
                with path.open("r", encoding="utf-8", newline="") as fh:
                    header = next(csv.reader(fh))
                    fh.seek(0)
                    cols = ", ".join(header)
                    with cur.copy(f"copy {SCHEMA}.{table} ({cols}) from stdin with (format csv, header true, null '')") as cp:
                        while chunk := fh.read(1 << 20):
                            cp.write(chunk)
                cur.execute(f"select count(*) from {SCHEMA}.{table}")
                n = cur.fetchone()[0]
                print(f"  {table:32s} {n:>8,} rows")
            # Read-only role for the warehouse connector, if the operator wants one
            cur.execute(f"grant usage on schema {SCHEMA} to postgres")
        conn.commit()
    print("done")


if __name__ == "__main__":
    main()
