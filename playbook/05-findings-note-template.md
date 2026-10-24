# What we found: [Customer]

Sent to: founder. Copied to: media buyer. One page. Every number comes from a query in the deployment log.

## The number you asked about

You said: [their number, their definition].
We measured: [true number, our definition]. [One sentence on the gap.]

## Why they're different

[Three to five findings. One line each. Date, what happened, what it did to the number.]

1. **[Date]: [event].** [Effect on the metric.] [How we know, one clause.]
2. ...

## What to do this week

| Fix | Who | Effort | What it changes |
|-----|-----|--------|-----------------|
| | | | |

## What's now running

- Dashboard: [link]. Open it Monday instead of the spreadsheet. It updates hourly.
- Agent: [name], scoped to [scope], mode: [read-only / acting]. First recommendation: [one line].

## What we need from you

- [One or two items, each with a deadline.]

---

## Filled in for Halcyon Botanicals

### The number you asked about

You said CAC on Meta went from $36 to over $60 and your media buyer says Ads Manager ROAS of 3.5 to 4 means it's fine.
We measured a true new-customer CAC from Meta of about $36 in April and about $60 in September, so your instinct was right. Ads Manager ROAS is not fine. It's inflated by two separate problems and the real figure on new customers is close to 1.

### Why they're different

1. **June 12: Shopify's Meta sales channel was installed while the old manual pixel stayed live.** Meta-reported purchases jumped about 60% overnight with no change in Shopify orders. Every ROAS and CPA in Ads Manager since then is overstated by roughly that much. We know because Meta purchases divided by Shopify orders was flat near 0.40 for ten weeks and stepped to 0.58 in one day.
2. **The Warm retargeting ad set counts subscription renewals as conversions.** It reports a CPA near $6 because renewals that were going to happen anyway land in its 7-day window. Those are not new customers.
3. **July 15: campaigns were renamed.** GA4 and your spreadsheet show the old names ending and new ones starting, so campaign-level trends broke in half. The dashboard merges them.
4. **August 10: FERN20 leaked to coupon sites.** Redemptions went from about 25 a month to over 400, with RetailMeNot and Honey as referrers. Those orders show as "direct" in Shopify, which is why organic looked like it was growing.
5. **Golden Hour UGC fatigued in August.** Frequency went from 2.0 to 4.9 and CTR halved. Its reported CPA still looked good because of finding 1, so spend on it kept rising. It now takes two thirds of prospecting budget.

### What to do this week

| Fix | Who | Effort | What it changes |
|-----|-----|--------|-----------------|
| Remove the manual pixel, keep the sales channel, turn on event deduplication | Media buyer | 1 hour | Ads Manager numbers become real again |
| Exclude active subscribers from Warm retargeting | Media buyer | 30 min | Retargeting CPA becomes honest, saves about $3k a month |
| Deactivate FERN20, issue per-influencer codes | Marketing manager | 30 min | Stops ~$6k a month in unintended discounts |
| Cap Golden Hour at 35% of prospecting spend, launch two new hooks | Media buyer | 2 hours | Stops paying rising CPMs to the same people |
| Replace the Monday spreadsheet with the dashboard | Founder | 0 | Same numbers every time, no manual math |

### What's now running

- Dashboard: private link. Panels follow the five findings in order.
- Facebook Ads agent, scoped to the two prospecting campaigns, read-only. It flags any ad above frequency 3.5 with CTR down 40% from launch, and recommends budget shifts daily.

### What we need from you

- Confirmation the media buyer has removed the manual pixel, by Wednesday, so we can verify the ratio drops back.
- A yes on letting the agent pause fatigued ads on its own from week two.
