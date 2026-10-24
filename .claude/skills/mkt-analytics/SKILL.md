---
name: mkt-analytics
description: Answer marketing and revenue questions by writing SQL against the Graphed warehouse, joining ad platforms, GA4, Search Console, CRM, and payments. Use when the user asks how a channel is performing, sign-ups/revenue by source, spend vs results, branded search trends, attribution, or any "what is happening in my data" question.
---

# Cross-channel analytics

Read `.claude/skills/mkt-foundations/SKILL.md` first. **Use the warehouse only.** Never pull reporting data from ad-platform APIs.

## Steps
1. **Restate the question** as specific metrics with a time range. Default: last 30 days compared with the previous 30. Examples: sign-ups attributed to Meta Ads; pixel-reported conversions and landing-page views; GA4 sessions where the source is Facebook; branded vs non-branded Search Console clicks/impressions by week.
2. **Find the data.** Run `graphed --format json sources list` to get each source's `schema_name`, then `graphed warehouse schema <schema_name>` for the relevant ones. Note the column names, date columns, ID/UTM fields and units. For example, spend may be stored in micros or cents.
3. **Write the SQL.** Run one query per sub-question first, and check that the row counts look reasonable. Then join across sources on date, campaign/UTM, or email/customer id. Rules:
   - Filter dates explicitly and state the timezone.
   - Don't count conversions twice across platforms. Each platform claims its own credit, so report platform-reported figures and CRM/Stripe ground truth side by side.
   - **Branded search:** define the brand terms with the user (brand name, misspellings, product names) and classify queries with `ILIKE` patterns. Show the weekly trend.
4. **Run:** `graphed --format json warehouse query -- '<SQL>'`. If a query is slow or huge, aggregate in SQL rather than pulling raw rows.
5. **Sanity-check.** Compare totals against what the user expects or the platform UI where possible. Flag gaps, such as a missing source or a sync lag of about 1 hour.

## Output
- Lead with the direct answer (numbers plus the direction of change).
- Then a small table, then the assumptions (attribution, date range, brand-term list).
- Save the SQL in `outputs/analytics/<slug>.sql` so it can be re-run.
- Offer `mkt-dashboard` to turn it into a live, shareable view, or a scheduled weekly report (foundations section 6).

## Useful standing questions
- Did we make money last week? Spend by channel compared with new revenue from Stripe/CRM, and blended CAC.
- Which campaigns or ads drive real sign-ups, not just platform-reported ones?
- Is branded search growing week over week?
- Which landing pages convert best by source?
