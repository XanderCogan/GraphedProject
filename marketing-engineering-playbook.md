# Marketing Engineering Playbook

Source: "Marketing Engineering Crash Course with Claude Code" by Cody Schneider (YouTube, ~29 min)
https://www.youtube.com/watch?v=jOuxlampW9E

Purpose of this file: a structured, AI-readable summary of the tools, infrastructure and workflows shown in the video, written so it can later be turned into a Claude skill (or set of skills), agent instructions, or automations.

> Transcript notes: captions were auto-generated, so some names are garbled. "graph.com" / "Graph CLI" / "Grapht" almost certainly refer to **Graphed** (graphed.com) and its CLI. Other likely corrections are marked *(probably X)*.

---

## 1. Core idea

**Marketing engineering** = having a coding agent (Claude Code, Cursor, Codex, etc.) do the hands-on "middle work" of marketing that a person used to do manually: writing copy, making ad creative, publishing blog posts, building landing pages, keyword research, customer research, finding prospect emails and loading them into cold email tools, building newsletters, and monitoring competitors' ad libraries.

The agent becomes highly capable once it has (a) access to unified, trustworthy data and (b) the ability to take actions through APIs. The job of the marketing engineer is to remove the barriers between the agent and those two things.

---

## 2. Architecture: the read/write loop

```
 Data sources (Meta Ads, Google Ads, GA4, Search Console, CRM, Stripe, ...)
        │  data pipeline (syncs ~hourly)
        ▼
 Data warehouse (SQL)  ──READ──►  Coding agent (Claude Code)
        ▲                               │
        │                               │ WRITE via platform APIs
        └──── new results flow back ◄───┘ (upload ads, toggle ads, publish posts, ...)
```

**Rules**
1. **Read from the warehouse, write through APIs.** Do not have the agent pull analytics straight from platform APIs.
2. Why: hitting platform APIs hard causes rate limits and can violate terms of service (Meta can ban the ad account). Joining data from several sources inside the agent's context causes hallucinations and quickly fills the context window.
3. **Tie spend to revenue.** One source, like Meta Ads alone, gives a misleading picture. Join ad data through to sign-ups, CRM and payments so the agent decides based on what actually makes money.
4. Agents are very good at SQL, so a SQL warehouse is the natural interface.
5. Direct APIs might be fine for a tiny single-channel account, but break at scale.

---

## 3. Infrastructure checklist

| # | Component | What it's for | DIY option named in video | Graphed equivalent |
|---|-----------|---------------|---------------------------|--------------------|
| 1 | Data pipeline | Sync every marketing/sales/revenue source into one place | Airbyte (open source) | Built-in connectors (claimed 800+) |
| 2 | Data warehouse | Fast SQL over large unified data | ClickHouse (open source) | Built in |
| 3 | Cloud server | Always-on machine to run scripts and agents without your laptop | Netlify *(questionable for this)* | Built in |
| 4 | Media storage | Store generated images and videos | S3 bucket | Built in |
| 5 | Databases | Agent's working memory: TAM/lead lists, creative queues, and the exact JSON prompts sent to image/video models | Postgres (for example on Railway) | Created on demand |
| 6 | Recurring tasks | Run jobs on a schedule (minute/hour/day) | Cron on the server | Built in |
| 7 | Artifact hosting | Share dashboards, ad-review pages and similar at a URL | Vercel | Built in (private team URLs) |
| 8 | Auth + shareable links | Your team can open artifacts; the public can't | Custom login database | Built in |
| 9 | Git manager | Several people working on the same code | GitHub | Built in |
| 10 | API gateway | One access point for image, video, email, scraping and SEO APIs | Separate subscriptions (~40 APIs) | "Graphed tools": unified API, ~250 endpoints, pay per use |
| 11 | Secrets manager | Store API tokens safely, not in local files | Any secrets manager | Built in via the CLI |

---

## 4. Tools and services mentioned

**Agent harnesses:** Claude Code, Cursor, Codex, Hermes agent, plus a "Grog bot" *(name unclear)*.

**Data sources:** Facebook/Meta Ads, Google Ads, Google Analytics 4, Google Search Console, HubSpot, Attio *(transcribed "a Teo")*, Stripe, GoHighLevel, Instantly, Twilio, and possibly PostHog *(transcribed "Post Ads")*.

**Unified API endpoints (via Graphed tools):**
- Ad library scraping: TikTok, Google, Meta
- Email finding: "Get Leads" endpoint, plus waterfall enrichment through Lead Magic and Apollo
- Email verification: MillionVerifier
- People and phone lookup, funding signals, news search
- LinkedIn profile extraction and LinkedIn post engager extraction
- Keyword research: DataForSEO API
- Image generation: "ChatGPT Image 2.5", routed through Kie.ai *(transcribed "Kai AI")*
- Video generation: Seedance, HeyGen (AI avatars)
- Reddit research: xAI (Grok) API

**Other:** Strapi (CMS for the blog), Meta Marketing API, Claude Sonnet (writes articles), Superwhisper (voice dictation into Claude Code), Looker Studio and Power BI (the tools this approach replaces).

**Graphed plugins:** the "SEO plugin" (research, write and publish a blog post to your CMS).

---

## 5. Setup steps

### 5.1 Install the Graphed CLI
- It's an npm package. Give Claude Code the package URL and tell it to install it.
- Connect data sources in Graphed. They then sync to the warehouse about every hour.
- Pricing is pay as you go; the video says about $10 covers around 1,000 email lookups.

### 5.2 Meta (Facebook) Ads API token (one-time, ~10 min)
1. In Meta Business Settings, click **Add** to create a developer app (any name).
2. Choose these use cases: create/manage ads with the Marketing API; create/manage ads with Meta Ads Manager; connect the business portfolio to its account.
3. Go through the requirements screens, confirm, create the app, and add a privacy policy URL.
4. Create a **system user**, assign it the ad accounts/assets it should control, and generate its token. System-user tokens don't expire.
5. Store the token in the secrets manager, not in a local file. In Claude Code, ask it to add the token to your Graphed secrets, then ask it to list the secrets to confirm.

Secrets shown in the demo: Facebook Ads, Google Ads, Instantly, Strapi (CMS). Everything else is covered by the unified API.

---

## 6. Workflows (skill candidates)

Each workflow below is written as a playbook an agent could follow. The example requests are paraphrased. In the demo, every request started with "use the Graphed CLI".

### W1. Generate static ad creative
- **Input:** headline or message, size (for example 1080×1080), brand or style reference URL, optional constraints (fonts, colors, banned words for regulated industries).
- **Steps:** look at the brand site for design style → call the image-generation endpoint → save the image to media storage → record the prompt JSON in the creative database.
- **Scale:** generate many variations (for example 100 headlines and descriptions built from research pain points).
- **Output:** image files plus a record of the prompt used for each.

### W2. Upload and manage Meta ads
- **Input:** ad set URL or ID, the creative to upload.
- **Actions:** upload media into an ad set; turn specific ads on or off (by title); move ads between ad sets.
- **Example request:** "Upload the [name] ad into this ad set: [URL]" / "In that ad set, turn off the ad titled [X]."
- **Check:** refresh Ads Manager to confirm.

### W3. Voice-of-customer research from Reddit
- **Input:** product category or ideal customer (for example, people who want a data pipeline and warehouse their AI agent can query instead of using BI tools).
- **Steps:** search Reddit through the xAI API → pull relevant threads → extract **pain points, desired outcomes and objections** → group them into themes.
- **Output:** grouped research used for ad copy, hooks and scripts (W1, W8).

### W4. Cross-channel conversational analytics
- **Input:** a business question.
- **Example:** How many sign-ups came from Meta Ads, and what does the pixel show? How much GA4 traffic has Facebook as the referrer? Are branded searches in Search Console going up?
- **Steps:** write SQL against the warehouse and join across sources → answer in plain language.
- **Follow-up:** turn the result into a shareable dashboard (W5).

### W5. Build a shareable dashboard (artifact)
- **Input:** the data from W4.
- **Steps:** build a hosted dashboard → share a private team URL → keep improving it by request (change chart types, for example spend by month as a line chart; add a date-range picker).
- **Use:** team reporting, and ad-review or approval pages.

### W6. LinkedIn post engagers → cold email list
- **Input:** URL of a LinkedIn post whose audience matches your ideal customer.
- **Steps:**
  1. Pull everyone who reacted or commented (remove duplicates).
  2. Look up emails with the Get Leads endpoint.
  3. For people still missing emails, run a **waterfall enrichment**: try providers from cheapest up (Lead Magic, Apollo, ...).
  4. For anyone still missing, **guess emails** from common patterns (~32 variations) and check them with MillionVerifier. This is often cheaper than paid lookups.
  5. Push the verified list to the cold email tool (Instantly).
- **Benchmark:** usually about 50% are found at step 2. The demo post did much worse.

### W7. SEO keyword research
- **7a. "Versus" keywords:** use DataForSEO to find comparison keywords in your category (for example "[tool] vs [tool]" in the customer-data stack). Remove duplicate intent: "X vs Y" and "Y vs X" count as one. The demo went from 765 to fewer unique keywords.
- **7b. Page-two opportunities:** use Search Console data to find keywords where you rank in positions 11–20 with 100+ impressions over the last 90 days (398 in the demo). Rank the top 10 to target.
- **7c. Expand a winning angle:** take a promising keyword and find similar variations, then add them to the content queue.

### W8. Write and publish a blog post (SEO plugin)
- **One-time setup:** install the Graphed SEO plugin and connect it to your CMS (Strapi in the demo).
- **Steps:** look at what ranks on Google page 1 for the target keyword → write the article with Claude Sonnet → publish to the CMS → return the live URL.
- The plugin can be changed to fit your process.

### W9. UGC / AI-avatar ad scripts
- **Input:** research themes from W3.
- **Steps:** write about 10 short scripts for a UGC creator or AI avatar. Each opens with a casual, surprised hook (in the style of "this is kind of crazy" or "I wish I'd found this sooner"), then covers one pain point and its outcome.
- **Output:** scripts for a person to read, or to send to an AI avatar video tool (HeyGen).

### W10. Competitor ad monitoring (mentioned, not demoed)
- Scrape competitors' Meta, Google, LinkedIn and TikTok ad libraries on a schedule to see how they position themselves.

### Also listed as possible but not demoed
Landing pages, email newsletters (for example promoting a webinar), and graphic design in general.

---

## 7. How to operate

- **Run several jobs at once.** Start a long task, start another while it runs, and check back. The demo had about 5 running together.
- **Build it once, then schedule it.** After a workflow works interactively, deploy it to the cloud server as a scheduled job so it runs without you.
- **Keep the data fresh.** Hourly sync means agents and dashboards can act on near-real-time data, including making decisions on their own.
- **Keep a record of how creative was made.** Store the prompts and parameters behind each image or video so good results can be repeated.
- **Use your voice.** Dictating long requests (Superwhisper) speeds things up.
- **Interrupt freely.** You can redirect or stop the agent mid-task.

---

## 8. Turning this into AI automation (next steps)

Possible ways to package it:
- **One Claude skill per workflow** (W1–W10). Each would hold the steps above, required inputs, the tools/endpoints to call, and output format. A small "router" skill could pick the right one.
- **A shared "marketing-engineering-foundations" skill** with the architecture rules (section 2), infrastructure (section 3) and secrets handling (section 5). The workflow skills would build on it.
- **Scheduled jobs** for recurring work: competitor ad scraping, page-two keyword reports, weekly spend-to-revenue dashboards.
- **Decide: Graphed vs DIY.** Using Graphed means the skills call its CLI. Building it yourself means the skills call Airbyte, ClickHouse and the individual APIs directly, which is cheaper at scale but much more setup.

Things to confirm before building:
- The exact Graphed CLI package name, commands and endpoint names (the video only shows natural-language requests).
- Which data sources and ad platforms you actually use.
- Your CMS and cold email tool.
- Budget limits per run (enrichment and generation are pay per use).
