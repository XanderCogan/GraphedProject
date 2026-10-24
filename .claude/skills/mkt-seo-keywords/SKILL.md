---
name: mkt-seo-keywords
description: SEO keyword research - find "X vs Y" comparison keywords in a category (DataForSEO), find page-two ranking opportunities from Google Search Console in the warehouse, expand a winning keyword into variations, and rank what to write next. Use when the user asks for keyword research, versus/comparison keywords, quick-win SEO, page-two keywords, or a content queue.
---

# SEO keyword research

Read `.claude/skills/mkt-foundations/SKILL.md` first. Search Console data comes from the warehouse, and keyword volume and ideas come from DataForSEO through Graphed Tools (`graphed tools catalog --query "dataforseo"` or `"keywords"`).

## Mode A: "versus" keywords for a category
1. Get the list of tools or brands from the user, or put one together. Example: CDP and warehouse stack tools like Hightouch, Census, ClickHouse, Snowflake, Segment.
2. Use the DataForSEO keyword ideas/suggestions tool with seeds like `<tool> vs`, `<tool> alternative`, `<tool> competitor`. Collect keyword, search volume, keyword difficulty, CPC.
3. **Remove duplicate intent.** "A vs B" and "B vs A" (and "A versus B", "A or B") count as one topic. Normalize by sorting the two names and keep the version with the most volume. Drop keywords where one side isn't relevant to the user's product.
4. Save `outputs/seo/vs-keywords.csv` and report before → after counts.

## Mode B: page-two opportunities (quick wins)
1. Find the Search Console schema with `graphed sources list`, then `graphed warehouse schema <gsc_schema>`.
2. Query for keywords with average position 11–20 and 100+ impressions over the last 90 days. Group by query, with clicks, impressions, CTR, average position and the top ranking page.
3. Rank by opportunity, for example impressions × (21 − position), boosted when the query matches the product's buying intent. Show the top 10, with the page that currently ranks and a suggested action: refresh that page, add a section, or write a new dedicated article.
4. Save `outputs/seo/page-two.csv`.

## Mode C: expand a winning angle
Given one promising keyword (for example "Google Ads vs Facebook Ads for <industry>"), use DataForSEO related/suggestion tools to find all the variations (other industries, modifiers). Remove duplicate intent as in Mode A and add the results to the queue.

## Content queue
Keep `outputs/seo/queue.csv` with these columns: keyword, intent, volume, difficulty, source (vs / page-two / expansion), target URL (new or existing), status, priority. Use a Graphed Postgres table instead if a project exists. Offer `mkt-seo-publish` for the top item.

## Cost
DataForSEO calls are pay-per-request. Batch seed keywords into as few calls as the tool allows, and estimate before running.
