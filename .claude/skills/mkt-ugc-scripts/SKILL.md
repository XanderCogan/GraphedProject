---
name: mkt-ugc-scripts
description: Write short UGC-style / AI-avatar video ad scripts from voice-of-customer pain points and outcomes, and optionally render them as talking-head videos with Graphed (ugc.avatar, HeyGen, Seedance). Use when the user asks for UGC scripts, video ad scripts, hooks, AI avatar ads, or talking-head ads.
---

# UGC / AI-avatar ad scripts

Read `.claude/skills/mkt-foundations/SKILL.md` first. The best input is a `mkt-voc-research` report. If there isn't one, offer to run it, or work from pain points the user provides.

## Inputs
- Pain points and outcomes (from the research report).
- Product, offer and CTA.
- Number of scripts (default 10) and length (default 20–35 seconds, about 60–90 spoken words).
- Hook style. The demo used casual, surprised, first-person openers. Write fresh hooks in that spirit rather than reusing the same line.

## Script structure (one pain point per script)
1. **Hook (0–3s):** a casual, surprised first-person opener.
2. **Pain (3–10s):** a specific, relatable moment using the buyer's own words from the research. Example: losing hours every Monday to spreadsheets just to find out whether the ads made money.
3. **Turn (10–20s):** what they found and what it does, in plain language.
4. **Outcome (20–30s):** the concrete result, matched to a desired outcome from the research.
5. **CTA (last 3–5s).**

Write it the way people talk: contractions, short sentences, no jargon or marketing-speak. Add simple stage directions in [brackets] (for example "[holds up phone]").

## Output
`outputs/ugc/<slug>/scripts.md`. For each script, include: the theme or pain point it targets, the hook, the full script, the word count and estimated seconds, and an on-screen caption. Rank the scripts by expected strength, and say why the top 3 lead.

## Optional: render
- Run `graphed tools catalog detail graphed:ugc.avatar`. This produces a vertical UGC talking-head ad from a script plus brand. Alternatives: `heygen:videos.avatar_iii`, or `kie:bytedance/seedance-2-5` for b-roll.
- Estimate cost per video. **Render 1–2 first for approval** before doing the batch.
- Log the inputs and `trn_` ids, store the finished videos with `graphed storage upload`, and offer `mkt-meta-ads-manage` to upload them, paused.
