# Five static ideas for Halcyon prospecting

Each one goes after something no current prospecting ad says. Headline, sub-line, CTA as rendered. Generated at 3:4, cropped to 1080x1350.

1. **Zero sugar vs a glass of wine.** Same Ritual. Zero Sugar. / A non-alcoholic aperitif with adaptogens, not sugar. / CTA: Shop Halcyon
2. **Subscription to a cold audience.** Never Run Out. 15% Off, Every Month. / Subscribe once. A bottle arrives before the last one is gone. Pause anytime. / CTA: Subscribe
3. **Host gift, the 3-pack.** Bring This Instead of Wine. / The 3-pack, $99. For the host who is not drinking tonight, or who is. / CTA: Send One
4. **Price per glass vs a bar.** $2.10 a Glass. / One bottle pours eighteen. The bar charges fourteen for one. / CTA: Shop Halcyon
5. **Tomorrow morning, without a medical claim.** Tonight Ends at 10. Tomorrow Starts at 6. / Adaptogens to help you unwind. Nothing to sleep off. / CTA: Shop Halcyon

Not made: a reviews ad (Review Carousel already owns proof for warm traffic) and a second occasion ad (three exist).

## Review (2026-10-26)

Model `kie:gpt-image-2-text-to-image` at 2K, 3:4, about 3.5 credits each, six renders for five ads.

- All text rendered as written. No made-up handles or URLs. Wordmark consistent across the five.
- Ad 2's first render put "22% ALC./VOL." on the label of a non-alcoholic product and gave it illustrated label art. Regenerated with the label text pinned in every prompt ("HALCYON / NON-ALCOHOLIC APERITIF / 0% ALC. VOL. 750 ML"). The `.req.json` files carry that line now.
- Every render put the CTA pill flush to the bottom edge, so a center crop from 3:4 to 4:5 clipped it. Final crops take the measured empty margin from each end and stretch the remainder 1.5 to 3.3 percent horizontally to reach 1080x1350, which is below what the eye notices. The skill's `generate.sh` crops with `sips`, which does not exist on Windows; the crop here is Pillow.
- Known gap: the bottle shape and cap differ between ads (screw cap, cork, wine-style capsule). A real brand would fix this with a product photo as the reference through the image-to-image model. Halcyon has no product photo.
- Delivered: `clients/static-ads/ads/<n>-<name>.png`, project storage `static-ads/halcyon-ads/<n>-<name>.png`, rows in the project's `skill_asset` table, and `~/Downloads/halcyon-ads/`.
