---
name: mkt-ad-creative
description: Generate static ad images (single or many variations) with Graphed image tools, on-brand, with every prompt logged. Use when the user asks to make an ad, ad creative, static, banner, social image, or creative variations at scale.
---

# Static ad creative

Read `.claude/skills/mkt-foundations/SKILL.md` first. It covers setup, cost guardrails and logging.

## Inputs (ask only for what's missing)
- **Message:** headline and any supporting text. For variations, take them from a list, from `mkt-voc-research` output, or have the agent write them.
- **Format:** size or aspect ratio. Default 1080×1080 (1:1). Others: 1080×1350 (4:5 feed), 1080×1920 (9:16 stories/reels).
- **Brand reference:** a website URL or brand guide. Look at it for colors, fonts, tone and visual style before writing prompts.
- **Constraints:** required or banned words, regulated-industry rules, logo use, how many variations.

## Steps
1. **Learn the style.** Fetch the brand URL and summarize it as a short style spec: palette hex values, typography feel, layout, imagery style and mood. Reuse this spec for every variation so the ads look like a set.
2. **Pick the model.** Default is `kie:gpt-image-2-text-to-image`, which handles text in images well. For editing a reference image or product shot, use `kie:gpt-image-2-image-to-image`. Alternatives are `kie:nano-banana-pro` and `kie:nano-banana-2`. Run `graphed tools catalog detail <id>` to get the exact input fields (prompt, size/aspect, image urls) and the price.
3. **Write the prompts.** Each prompt includes: the exact headline text in quotes, the layout, the style spec, the aspect ratio, and "no extra text" to stop invented copy. Keep on-image text short (7 words or fewer is ideal).
4. **Estimate cost** (number of variations × price per image) and follow the foundations guardrails.
5. **Generate:** `graphed tools run <model> --wait --out outputs/ad-creative/<slug>-<n>.json --body-file <input.json>`. The result has the image URL(s). Download each image into `outputs/ad-creative/`.
6. **Check every image yourself.** Look at it: Is the headline spelled correctly? Is the text cut off? Are banned words absent? Does it match the brand? Regenerate any failures once with a corrected prompt, and log the retry.
7. **Store and log.** Run `graphed storage upload` for each final image under `creative/<campaign>/<slug>.png` when a project exists. Add a log entry with: model, input JSON, `trn_` id, storage key, headline and the angle or pain point it targets.

## Output
- A list of the final images (local paths and storage keys) with each headline.
- The total credits spent.
- An offer to upload them with `mkt-meta-ads-manage`, or to build a review page with `mkt-dashboard` so the team can approve them first.

## Scale pattern (100+ variations)
Build a matrix: angles (pain points and outcomes from `mkt-voc-research`) × headline styles × 1–2 layouts. Generate a small batch of 5–10 first and get the user's approval on the look. Then run the rest from a script under `graphed dev run`, using the SDK `client.tools.run` and one idempotency key per variation.
