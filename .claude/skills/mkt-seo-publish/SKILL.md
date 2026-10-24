---
name: mkt-seo-publish
description: Research, write, and publish an SEO blog post for a target keyword to the user's CMS, preferably via the Graphed SEO plugin. Use when the user asks to write a blog post/article for a keyword, publish content, or work through the SEO content queue.
---

# Write and publish an SEO article

Read `.claude/skills/mkt-foundations/SKILL.md` first.

## Use the plugin first
Graphed ships an SEO plugin built for exactly this:
- **Not installed yet:** run `graphed plugins show seo`, then `graphed plugins add seo --apply-manifest` inside the Graphed project. Follow the staged `.graphed/plugins/seo/AGENT.md` end to end, including connecting the CMS. The demo used Strapi; the CMS token goes in Graphed secrets.
- **Installed:** run the article flow through the plugin.
- The `/graphed:plugins:seo-agent` skill is the same flow.

Only use the manual steps below if the plugin can't be used, and tell the user if so.

## Manual flow
1. **Keyword:** take it from the user or the top of the `mkt-seo-keywords` queue. Confirm the search intent: comparison, how-to, or a list of alternatives.
2. **Research the current page 1.** Use a SERP tool (`graphed tools catalog --query "serp"`, DataForSEO) to get the top 10 results. Fetch the top 3–5. Note what they cover, their headings, length, what's missing, and the questions people ask.
3. **Outline:** title (with the keyword), meta description, H2/H3 structure covering everything competitors cover plus at least one thing they lack (real data, a clear verdict, a comparison table), FAQs, and internal links to relevant product pages.
4. **Write** in the brand's voice. Be accurate and specific, and don't invent statistics, customers or quotes. For "X vs Y" articles, be fair, include a comparison table, and give a clear "choose X if…, choose Y if…" verdict. Include a CTA for the user's product where it fits naturally.
5. **Publish:**
   - Use the plugin, or the CMS API with the token from Graphed secrets (via `graphed dev run`).
   - **Default to draft.** Publish live only if the user said so.
   - Set the slug, meta title/description and category.
6. **Return** the draft or live URL. Update the content queue status.

## Output
The URL, the title, the word count, and the keyword. Offer to request indexing and to add the URL to rank tracking via `mkt-seo-keywords` Mode B later.
