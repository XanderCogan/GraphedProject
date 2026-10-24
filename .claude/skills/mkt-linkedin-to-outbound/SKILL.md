---
name: mkt-linkedin-to-outbound
description: Turn the people who reacted to or commented on a LinkedIn post into a verified email list - extract engagers, find emails, waterfall-enrich the misses, guess-and-verify the rest, then hand off to a cold email tool. Use when the user gives a LinkedIn post URL and wants leads, emails, prospects, or an outbound list.
---

# LinkedIn post engagers → verified email list

Read `.claude/skills/mkt-foundations/SKILL.md` first. Run `graphed plugins search "outbound"` first. If an outbound plugin covers this, use it.

## Inputs
- A LinkedIn post URL. It should be a post whose engagers match the target customer.
- Optional: an ideal-customer filter (titles, company size or industry to keep), a max spend, and the destination (Instantly campaign, CSV).

## Steps
1. **Extract the engagers.** Run `apify:apimaestro~linkedin-post-comments-replies-engagements-scraper-no-cookies`. Check the input shape with `catalog detail` first. Collect reactors and commenters, then **remove duplicates by profile URL**. The same person often both reacts and comments. Save to `outputs/outbound/<slug>/engagers.json`.
2. **Filter to the ideal customer** (if a filter was given) using headline/title and company. Remove the post author, your own team and obvious non-buyers. Report how many people are kept.
3. **Find emails (first pass).** Run `graphed tools catalog --query "email find"` (or "leads"). Use the main email-finding tool, passing name plus company domain or profile URL. A good post usually gets about half. Estimate the cost first.
4. **Waterfall enrichment for the misses.** List the email-finder providers in the catalog (for example Lead Magic, Apollo) **from cheapest to most expensive**. Run the remaining people through each in turn, stopping per person on the first hit. Report hits and cost per stage.
5. **Guess and verify the rest.** For people with a known company domain but still no email:
   - Generate the common patterns: first, last, first.last, firstlast, f.last, flast, first_last, first-last, last.first, firstl, and so on. That's up to about 32 per person.
   - Check them with `million-verifier:bulk`: upload a CSV with `graphed storage upload`, pass its URL, and save the report with `--out`. Use `million-verifier:validate` for a handful.
   - Keep only `ok`/valid. Treat catch-all domains as risky: keep them in a separate column and don't mix them into the main list.
6. **Verify everything.** Run all found emails through MillionVerifier too, unless the provider already verified them.
7. **Build the final list:** `outputs/outbound/<slug>/leads.csv` with these columns:
   - first_name, last_name, title, company, domain, linkedin_url
   - email, email_source (which stage found it), verification_status
   - engagement (reacted or commented, plus the comment text), post_url

## Hand-off
To load into Instantly or another cold email tool, use the matching plugin or the tool's API with the token from Graphed secrets. **Confirm with the user before adding leads to any campaign, and never start sending yourself.** Suggest a first line that refers to the post they engaged with.

## Output
Report:
- Funnel counts: engagers → after dedupe → after filter → found by stage → verified
- Total credits spent
- The CSV path
