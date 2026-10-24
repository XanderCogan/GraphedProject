# Kickoff call script

Thirty minutes. The goal is not to explain Graphed. The goal is to leave with every credential, every number the founder already believes, and a clear statement of the one problem they'd pay to have solved. Everything else can be async.

## Before the call (10 minutes)

- Open their store. Buy nothing, but go to checkout. Note what fires: Meta pixel, GA4, Klaviyo, TikTok, anything else. Browser devtools, Network tab, filter `facebook.com/tr` and `google-analytics.com/g/collect`.
- Check the Meta Ad Library for their page. Count active ads. Note the oldest active creative.
- Look at their last 3 emails if you can subscribe. Note cadence and whether flows exist.
- Read the discovery notes from sales. Write down the number they quoted as the problem (CAC, ROAS, revenue). That number is almost always computed wrong, and finding out how is the first week's work.

## Minute 0 to 5: frame it

"I'm the person who makes this work. By end of next week you'll have your data in one place and a dashboard you can open on Monday instead of the spreadsheet. Today I need three things from you: how you measure the business now, what's connected to what, and access. I'll do most of the talking at the end, not the beginning."

## Minute 5 to 15: how they measure today

Ask these in order. Write down the exact answer, including the wrong ones.

1. "Walk me through your Monday. What do you open, in what order, and what number do you look at first?"
2. "When you say CAC, what's the numerator and what's the denominator?" (Listen for: total spend or Meta only; all orders or new customers only; Shopify orders or Meta-reported purchases.)
3. "What does your media buyer send you, and how often? Can you forward me the last one?"
4. "What number would make you say this is working? And what number right now makes you say it isn't?"
5. "Has anything changed in the last six months? New pixel, new app, new agency, campaign restructure, new discount codes, a rebrand, a Shopify theme change?" (Every yes is a candidate root cause. Write the month next to it.)
6. "Do you have a subscription product? What share of orders is renewals? Does your media buyer count those as conversions?"
7. "Any discount codes in the wild? Influencer codes? When did you last check where they're being used?"

## Minute 15 to 22: what is connected to what

Draw it on paper while they talk.

- Shopify: plan tier, apps installed that touch tracking (Meta sales channel, Google & YouTube channel, Klaviyo, Recharge, any "pixel manager").
- Meta: who owns the Business Manager? Who has admin? Is there a Conversions API set up, and by whom?
- Google: Ads account, GA4 property, Search Console. Same login or different?
- Email: Klaviyo or other. Is attribution set to 5-day click, 5-day open, or something else?
- Anything else sending revenue: Amazon, wholesale, retail, TikTok Shop.
- The spreadsheet. Ask for view access to the actual sheet. Not a screenshot.

## Minute 22 to 27: access

Send the access checklist (02) while on the call and watch them open it. Don't leave the call until at least Shopify and Meta are in motion, because those two take longest to approve and they gate everything.

Say: "I'll never need your passwords. For every platform there's a way to add me or Graphed as a collaborator. The checklist has the exact clicks."

## Minute 27 to 30: set expectations and close

- "In the first three days I'm going to find things that are wrong with your numbers before I find anything wrong with your marketing. That's normal. I'll show you what I find and how I checked it."
- "Day 5 you get the dashboard and a one-page note. Day 10 the first agent is running against a scope we agree on together, read-only first."
- Confirm one Slack channel or email thread for everything. One.
- End on time. Thank them once. Hang up.

## After the call (15 minutes)

- Write up the answers to questions 1 to 7 in the deployment log.
- Turn every "something changed" answer into a dated hypothesis: "Meta sales channel installed ~June. Check Meta purchases vs Shopify orders before and after."
- Send a recap with the access checklist and the three things you still need. Keep it under ten lines.

## Questions to ask yourself, not them

- Is the number they're worried about even real?
- What's the cheapest finding that would make them trust us? Usually it's one chart where two sources disagree and we explain why.
- What's the agent they actually need first? It's rarely the one sales promised.
