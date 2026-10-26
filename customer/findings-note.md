# What we found: Halcyon Botanicals

Sent to: founder. Copied to: media buyer. One page. Every number comes from the warehouse, and the query behind each one is on the Monday board, which names its table under every panel.

## The number you asked about

You said: your spreadsheet's cost per new customer moved from about $26 in April to about $29 now, while Meta spend went up 43% (from $29.5k to $42.3k a month). Your media buyer says Ads Manager ROAS of 3.5 to 4 means it's fine.

We measured: Meta spend divided by the customers Meta actually brought in. $36 in April. $65 in September. Up 80%. Meta delivered 825 new customers in April and 649 in September on 43% more money. Your spreadsheet divides the same spend by every new customer in Shopify, including the ones who came in organically and, since August, the ones who found a leaked coupon code. That denominator kept growing while Meta's share of it shrank, which is why your number barely moved. Your instinct was right. Ads Manager is not fine either: its ROAS of 3.4 over the last four weeks is 1.39 when you count only first orders.

## Why they're different

1. **June 12: Shopify's Meta sales channel went live while the old manual pixel stayed on.** Meta-reported purchases per Shopify order sat at 0.44 for ten weeks and stepped to 0.61 overnight, with no change in orders. Every ROAS and CPA in Ads Manager since then is overstated by about 40%. Ads Manager ROAS went from 3.0 to 4.3 that month, which is the moment your media buyer started saying it was fine.
2. **The Warm retargeting ad set counts subscription renewals as conversions.** It serves past purchasers, so renewals that were going to happen anyway land in its attribution window. It reports a cost per purchase of $11 on about $9.5k a month. Almost none of those are new customers.
3. **July 15: campaigns were renamed and the UTM template changed.** GA4 and Shopify landing sites show the old names ending and the new names starting the same day, so every campaign trend broke in two. Meta's own reports show only the new names, which hid it. The board joins the halves.
4. **August 10: FERN20 leaked to coupon sites.** Redemptions went from about 26 a month to about 410, with RetailMeNot and CouponFollow as referrers. September alone gave away $7.2k in discounts. Those orders average $8 less, they land as "direct" in Shopify, and they are 22% of your new customers since the leak. They are in your spreadsheet's denominator as if Meta brought them in.
5. **Golden Hour UGC fatigued in late August and kept getting budget.** Its 7-day frequency went from 2.1 in the spring to 4.8 now and its click-through rate is 47% of what it was at launch. Because of finding 1 its reported cost per purchase still looked fine, so the budget followed it. It is 38% of prospecting spend this week. The agent flagged it in its first run.

## What to do this week

| Fix | Who | Effort | What it changes |
|-----|-----|--------|-----------------|
| Remove the manual pixel, keep the sales channel, turn on event deduplication | Media buyer | 1 hour | Ads Manager purchases drop about 30% and become real |
| Exclude active subscribers from the Warm retargeting audience | Media buyer | 30 min | Stops most of the $9.5k a month spent re-showing ads to people who already subscribe |
| Deactivate FERN20, issue one code per influencer | Marketing manager | 30 min | Stops about $7k a month in unintended discounts and cleans the new-customer count |
| Cap Golden Hour UGC at 25% of the Broad ad set and move the difference to Hangover-Free Hook and Fall Fig Reel, which hold their launch CTR | Media buyer | 2 hours | Stops paying rising CPMs to show one ad to the same people five times a week |
| Open the Monday board instead of the spreadsheet | Founder | 0 | Same numbers every week, no manual math, and the CAC you see is the one that moves the bank balance |

## What's now running

- Dashboard: the Monday board, private behind your Graphed login. Six panels in the order of the findings above, every number naming its source table. It reads the warehouse, which syncs from Shopify, Meta, GA4 and Klaviyo.
- Agent: the Meta ads agent, scoped to the two prospecting campaigns only, recommend-only. Every morning at 8 it reads the week's numbers, flags any ad over 7-day frequency 3.5 with CTR under 60% of its launch level, or with cost per purchase 1.5x its recent median, and writes the media buyer a ranked note at `/meta-ads`. Its first recommendation: rotate new creative into Golden Hour UGC 0:22, frequency 4.84, CTR at 47% of launch, fatigued for eight weeks.

## What we need from you

- Confirmation from the media buyer that the manual pixel is off, by Wednesday, so we can watch the purchase ratio fall back to 0.44 and know the fix took.
- A decision on whether the agent may cap a fatigued ad's budget on its own from week two. Until then it only writes the note.
