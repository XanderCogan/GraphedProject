import { Kysely, sql } from "kysely";

// Meta ads agent: one row per run, one row per recommendation. Nothing here
// is written to Meta; `applied` is for the media buyer to tick off by hand.
export async function up(db: Kysely<unknown>): Promise<void> {
  await db.schema
    .createTable("meta_ads_runs")
    .addColumn("id", "text", (col) => col.primaryKey())
    .addColumn("client_key", "text", (col) => col.notNull())
    .addColumn("started_at", "timestamptz", (col) => col.notNull().defaultTo(sql`now()`))
    .addColumn("finished_at", "timestamptz")
    .addColumn("status", "text", (col) => col.notNull())
    .addColumn("dry_run", "boolean", (col) => col.notNull())
    .addColumn("scope", "jsonb", (col) => col.notNull())
    .addColumn("summary", "jsonb")
    .addColumn("brief", "text")
    .addColumn("model", "text")
    .addColumn("llm_used", "boolean", (col) => col.notNull().defaultTo(false))
    .addColumn("error", "text")
    .execute();

  await db.schema
    .createIndex("meta_ads_runs_client_started_idx")
    .on("meta_ads_runs")
    .columns(["client_key", "started_at"])
    .execute();

  await db.schema
    .createTable("meta_ads_recommendations")
    .addColumn("id", "uuid", (col) => col.primaryKey().defaultTo(sql`gen_random_uuid()`))
    .addColumn("run_id", "text", (col) => col.notNull())
    .addColumn("client_key", "text", (col) => col.notNull())
    .addColumn("rank", "integer", (col) => col.notNull())
    .addColumn("kind", "text", (col) => col.notNull())
    .addColumn("severity", "text", (col) => col.notNull())
    .addColumn("action", "text", (col) => col.notNull())
    .addColumn("action_label", "text", (col) => col.notNull())
    .addColumn("ad_id", "text", (col) => col.notNull())
    .addColumn("ad_name", "text", (col) => col.notNull())
    .addColumn("adset_name", "text", (col) => col.notNull())
    .addColumn("campaign_name", "text", (col) => col.notNull())
    .addColumn("week", "text", (col) => col.notNull())
    .addColumn("rationale", "text", (col) => col.notNull())
    .addColumn("evidence", "jsonb", (col) => col.notNull())
    .addColumn("applied", "boolean", (col) => col.notNull().defaultTo(false))
    .addColumn("created_at", "timestamptz", (col) => col.notNull().defaultTo(sql`now()`))
    .execute();

  await db.schema
    .createIndex("meta_ads_recommendations_run_idx")
    .on("meta_ads_recommendations")
    .column("run_id")
    .execute();
}

export async function down(db: Kysely<unknown>): Promise<void> {
  await db.schema.dropTable("meta_ads_recommendations").execute();
  await db.schema.dropTable("meta_ads_runs").execute();
}
