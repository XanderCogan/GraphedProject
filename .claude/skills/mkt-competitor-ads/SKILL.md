---
name: mkt-competitor-ads
description: Monitor competitors' ads in the Meta, Google, LinkedIn, and TikTok ad libraries - scrape active ads, summarize positioning, offers, hooks, and formats, and track changes over time on a schedule. Use when the user asks what competitors are running, for an ad library scrape, competitor positioning, or competitive ad monitoring.
---

# Competitor ad monitoring

Read `.claude/skills/mkt-foundations/SKILL.md` first.

## Inputs
- A list of competitors, each with name, website domain, and Facebook page / LinkedIn company page if known.
- Platforms (default: Meta and Google, plus LinkedIn for B2B and TikTok for consumer brands).
- Country (default US).

## Steps
1. **Find the tools.** Run `graphed tools catalog --query "ad library"` (also try "meta ads library", "google ads transparency", "linkedin ads", "tiktok ads"). Check inputs and price with `catalog detail`. Any Apify ad-library actor also works as `apify:<owner~actor>`.
2. **Estimate cost** (competitors × platforms × price) and follow the guardrails.
3. **Scrape the active ads.** For each ad keep: platform, competitor, ad id, first-seen/start date, copy (primary text, headline), CTA, landing URL, format (image/video/carousel) and media URLs. Save to `outputs/competitors/<date>/raw.json`.
4. **Analyze per competitor:**
   - The main messages and positioning claims
   - Offers (trials, discounts, lead magnets)
   - Hook patterns
   - Formats used
   - Landing pages
   - **Longest-running ads**, since ads that stay live are probably working
5. **Compare across competitors.** Note the messages they all use, gaps nobody covers, and how the user's positioning differs.
6. **Track changes.** If a previous run exists, diff against it: new ads, stopped ads, new offers. Store the history in a Graphed Postgres table when a project exists.

## Output
`outputs/competitors/<date>/report.md` covering:
- A one-paragraph summary per competitor
- A table of their top ads with links
- What changed since last time
- 3–5 ideas for the user, as angles to test with `mkt-ad-creative`

## Schedule (offer after the first run)
Run weekly as a Graphed job (foundations section 6), and send the "what changed" section to the team or a dashboard (`mkt-dashboard`).
