---
name: mkt-meta-ads-manage
description: Upload image/video ads into a Meta (Facebook/Instagram) ad set, turn ads on or off, and move or duplicate ads between ad sets via the Meta Marketing API, with the token held in Graphed secrets. Use when the user asks to upload, launch, pause, enable, disable, or move Facebook/Meta ads.
---

# Manage Meta ads

Read `.claude/skills/mkt-foundations/SKILL.md` first. This skill **writes** to a live ad account, so follow the confirmation rules below.

## Prerequisites
- Graphed secrets `META_ACCESS_TOKEN` (system-user token) and `META_AD_ACCOUNT_ID` (`act_…`). Check with `graphed secrets list`. If they're missing, walk the user through the Meta token steps in foundations section 5.
- First run `graphed plugins search "meta ads"`. If a Meta/Facebook Ads plugin exists, use it instead of the raw-API approach below.
- For reporting (spend, results), use `mkt-analytics` on the warehouse. Don't query performance from the API.

## How calls are made
The token only exists inside Graphed runtimes, so make API calls from a small Node script run with `graphed dev run -- node scripts/meta.mjs <action> ...`. The script reads `process.env.META_ACCESS_TOKEN`. Use the current Graph API version from Meta's docs (`https://graph.facebook.com/vXX.X/`). Never print the token.

## Actions

### Upload a new ad into an existing ad set
1. Get the ad set id. If the user pastes an Ads Manager URL, the ad set id is the `selected_adset_ids` value (or ask). Read the ad set (`GET /{adset_id}?fields=name,campaign_id,status,promoted_object`) and one existing ad's creative (`GET /{adset_id}/ads?fields=name,creative{object_story_spec,asset_feed_spec}`). Copy the page id, Instagram account, link URL and CTA from it unless the user specifies others.
2. Upload the media:
   - Image: `POST /act_{id}/adimages` with the file. You get back an `image_hash`.
   - Video: `POST /act_{id}/advideos`. You get back a `video_id`, which needs a thumbnail.
3. Create the creative: `POST /act_{id}/adcreatives` with `object_story_spec` (page_id, link_data: message, link, name/headline, image_hash, call_to_action).
4. Create the ad: `POST /act_{id}/ads` with `adset_id`, `creative`, and a name.
   - **Status:** default to `PAUSED`, and tell the user it's paused.
   - Use `ACTIVE` only if the user explicitly asked for it to go live.
5. Log the ad id, creative id, media source and status.

### Turn ads on or off
1. List the ads in the ad set (`GET /{adset_id}/ads?fields=id,name,effective_status`) and match by the name or title the user gave.
2. If more than one ad matches, or none does, show the candidates and ask.
3. Confirm with the user, then `POST /{ad_id}` with `status=PAUSED` or `ACTIVE`.
4. Read the ad back to verify it changed.

### Move an ad to another ad set
Meta ads can't be re-parented. Copy it with `POST /{ad_id}/copies` with `adset_id=<target>` (or recreate it from the same creative), then pause the original. Confirm the plan before doing this.

## Confirmation rules
- Before activating, pausing or copying any ad, show the user the ad names and target ad set in one line and wait for a yes. One approval covers that exact batch only.
- Never change budgets, bids, targeting or campaign settings unless explicitly asked, and confirm the numbers first.

## Output
Report each ad touched (name, id, new status) and ask the user to check in Ads Manager.
