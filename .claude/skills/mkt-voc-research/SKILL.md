---
name: mkt-voc-research
description: Voice-of-customer research - mine Reddit (and optionally other forums/reviews) for the pain points, desired outcomes, and objections of a target buyer, clustered into themes for ad copy, hooks, and content. Use when the user asks for customer research, pain points, Reddit research, messaging angles, or input for ads/scripts.
---

# Voice-of-customer research

Read `.claude/skills/mkt-foundations/SKILL.md` first.

## Inputs
- **Who and what:** the buyer and the job they're trying to get done. Example: "teams that want a data pipeline and warehouse their AI coding agent can query, instead of BI tools like Looker Studio or Power BI."
- Optional: subreddits to focus on, competitor names, time window (default: last 2 years), and how many threads (default ~50).

## Steps
1. **Plan the searches.** Write 5–10 search queries covering problem language ("how do I…", "frustrated with…", "alternative to <competitor>"), competitor names and category terms. Pick likely subreddits.
2. **Find a source tool.** Run `graphed tools catalog --query "reddit"`. Prefer a cataloged Reddit search/scrape tool. Otherwise use an Apify Reddit scraper actor (`apify:<owner~actor>`, checked with `catalog detail`). The video used xAI/Grok search, so if the catalog has an xAI search tool, it works too. Estimate cost before running.
3. **Collect.** Gather the posts and top comments. Keep the URL, subreddit, date, score and text. Save the raw data to `outputs/voc/<slug>/raw.json`.
4. **Extract.** For each thread, pull out:
   - **Pain points:** what's broken or annoying, in the user's own words.
   - **Desired outcomes:** what success looks like to them.
   - **Objections:** reasons they hesitate or would not buy.
   - **Current alternatives:** tools and workarounds they mention.
   Keep short supporting quotes with their source URL. For large volumes, do the extraction in a script that calls an LLM through the SDK's OpenRouter proxy.
5. **Group into themes.** Merge the extracted points into 5–12 themes. For each theme give: a label, a one-line summary, how often it came up, 2–3 representative quotes with links, and the outcome it ties to.
6. **Turn into marketing angles.** For each theme, suggest an ad angle, 3 headline ideas and 1 hook line.

## Output
Write `outputs/voc/<slug>/report.md` containing:
- Themes ranked by how often they came up
- Quotes with links
- Angles
- A short "words they use" vocabulary list

Then give a 5-line summary in chat. Offer next steps: `mkt-ad-creative` (variations by angle) or `mkt-ugc-scripts`.

## Quality bar
Use the buyers' real wording. Don't invent quotes. Ignore vendor self-promotion threads. Flag themes that rest on fewer than 3 threads as weak signals.
