"""
Load the generated CSVs into a Supabase Postgres database, schema `halcyon`.

Usage:
    python data/load_supabase.py            # reads SUPABASE_DB_URL from .env or the environment
    python data/load_supabase.py --drop     # drop and recreate the schema first

Graphed's Postgres connector then syncs these tables into the warehouse.

Uses psycopg when it can load; falls back to pg8000 (pure Python) on machines
where the psycopg binary is blocked. Both go through COPY, so the load is fast
either way. Use the Supabase *session pooler* URI: the direct host is IPv6-only.
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
from pathlib import Path

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
    "meta_ads_insights_weekly": """
        week_start date, week_end date, account_id text, campaign_id bigint, campaign_name text, adset_id bigint,
        adset_name text, ad_id bigint, ad_name text, spend numeric(12,2), impressions bigint, reach bigint,
        frequency numeric(6,2), clicks bigint, inline_link_clicks bigint, ctr numeric(8,4), purchases integer,
        purchase_value numeric(12,2), purchase_roas numeric(10,4),
        primary key (week_start, ad_id)
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
        week_of date primary key, meta_spend numeric(12,2), google_spend numeric(12,2), influencer_spend numeric(12,2),
        meta_purchases_reported integer, meta_roas_reported numeric(8,2), shopify_orders integer,
        shopify_revenue numeric(12,2), shopify_new_customers integer, blended_cac_their_calc numeric(10,2),
        meta_cac_new_their_calc numeric(10,2), notes text
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


class Db:
    """Minimal driver shim: run(sql), copy_csv(sql, fileobj), one(sql) -> first value."""

    def __init__(self, url: str) -> None:
        self.kind = "psycopg"
        try:
            import psycopg  # type: ignore

            self.conn = psycopg.connect(url, autocommit=False)
            self.cur = self.conn.cursor()
        except ImportError:
            self.kind = "pg8000"
            import re

            import scramp  # type: ignore

            if not hasattr(scramp, "make_channel_binding"):  # scramp 1.5 + pg8000 1.31 on Windows
                scramp.make_channel_binding = lambda name, sock: None  # SCRAM without channel binding
            import pg8000.native  # type: ignore

            m = re.match(r"postgres(?:ql)?://([^:]+):(.*)@([^/:]+)(?::(\d+))?/([^?]*)", url)
            if not m:
                sys.exit("SUPABASE_DB_URL is not a postgresql://user:password@host:port/db URI")
            user, pw, host, port, db = m.groups()
            self.conn = pg8000.native.Connection(
                user=user, password=pw, host=host, port=int(port or 5432), database=db or "postgres",
                ssl_context=True, timeout=30,
            )
            self.conn.run("begin")
            print(f"  (psycopg unavailable; using pg8000 via {host})")

    def run(self, sql: str) -> None:
        if self.kind == "psycopg":
            self.cur.execute(sql)
        else:
            self.conn.run(sql)

    def one(self, sql: str):
        if self.kind == "psycopg":
            self.cur.execute(sql)
            return self.cur.fetchone()[0]
        return self.conn.run(sql)[0][0]

    def copy_csv(self, sql: str, fh) -> None:
        if self.kind == "psycopg":
            with self.cur.copy(sql) as cp:
                while chunk := fh.read(1 << 20):
                    cp.write(chunk)
        else:
            self.conn.run(sql, stream=fh)

    def commit(self) -> None:
        if self.kind == "psycopg":
            self.conn.commit()
        else:
            self.conn.run("commit")

    def close(self) -> None:
        self.conn.close()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--drop", action="store_true", help="drop and recreate the schema")
    args = ap.parse_args()

    db = Db(read_env())
    try:
        if args.drop:
            db.run(f"drop schema if exists {SCHEMA} cascade")
        db.run(f"create schema if not exists {SCHEMA}")
        for table, ddl in TABLES.items():
            db.run(f"drop table if exists {SCHEMA}.{table}")
            db.run(f"create table {SCHEMA}.{table} ({ddl})")
            path = OUT / f"{table}.csv"
            with path.open("r", encoding="utf-8", newline="") as fh:
                header = next(csv.reader(fh))
                fh.seek(0)
                cols = ", ".join(header)
                db.copy_csv(f"copy {SCHEMA}.{table} ({cols}) from stdin with (format csv, header true, null '')", fh)
            n = db.one(f"select count(*) from {SCHEMA}.{table}")
            print(f"  {table:32s} {n:>8,} rows")
        # Read-only role for the warehouse connector, if the operator wants one
        db.run(f"grant usage on schema {SCHEMA} to postgres")
        db.commit()
    finally:
        db.close()
    print("done")


if __name__ == "__main__":
    main()
