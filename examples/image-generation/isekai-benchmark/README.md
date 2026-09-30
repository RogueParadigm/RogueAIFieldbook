# Isekai production-workflow benchmark

This benchmark asks a local, open-source image model to perform the three jobs
that matter in the Isekai production pipeline: create a coherent new scene from
separate visual authorities, revise an environment while protecting finished
characters, and repair one small semantic region without moving the rest of the
panel.

The private source references are not copied into this repository. Their SHA-256
hashes and portable role names are recorded in each output sidecar. All edits in
this directory were written by Open ImageGen; the Isekai source tree remained
read-only.

## Evaluation matrix

| Test | Model and settings | Result | Verdict |
| --- | --- | --- | --- |
| New bakery scene from identity + style references | FLUX.2 [klein] 4B, 944×1680, 4 steps, seed `260905` | Coherent new panel; recognisable face, glasses, ponytail, outfit, bag, palette, and bakery setting | **Fail for final use:** three hands, the action became tasting a utensil rather than bread, the face narrowed, and pseudo-text appeared on the price tag |
| New bakery scene from identity + style references | SenseNova-U1.5-8B-MoT Q8, 896×1600, 50 steps, seed `260905` | Coherent heroine, bakery, bread-tasting action, price-card interaction, lighting, palette, and style | **Strong pass with one defect:** exactly two arms and two hands with clear roles; one impossible floating spatula remained; 197.544s inference |
| Successive floating-object correction | SenseNova-U1.5-8B-MoT Q8, 896×1600, 50 steps, seed `260914` | Removed the floating spatula and reconstructed the wall/window while retaining the heroine, two hands, action, framing, and scene | **Accepted semantic correction:** 191.411s inference; subtle full-frame redraw means a mask is still required for pixel invariance |
| Style consolidation from accepted scene | BArtstyle REv3 + Counterfeit V3, 576×1024, denoise `0.22`/`0.32`, LoRA `0.60`, seeds `260917`/`260918` | Preserved two hands, action, outfit, bag, lighting, and composition while imposing cleaner flat-color rendering | **Useful finishing pass:** 6.095s/6.130s inference; low strength retains identity better, but the full frame is regenerated |
| Bakery scene from scratch | BArtstyle REv3 + Counterfeit V3, 576×1024, LoRA `0.65`, 30 steps, seeds `260919`/`260920` | Strong anime flat-color style with no extra limbs in either sample | **Style pass, scene-fidelity fail:** one seed turned the card into a booklet; the other omitted it, and both simplified the bakery/action |
| Simplify A9 background while protecting heroine | FLUX.2 [klein] 4B, 1664×944, 4 steps, seed `260906`, `preserve-white` mask | The environmental rendering changed while the protected character/contact region was restored from the source | **Strong workflow pass:** 100% exact protected pixels; 99.999302% of unprotected pixels changed |
| Restore missing A1 window, broad mask | FLUX.2 [klein] 4B, 512×1024, 4 steps, seed `260907` | Added an oversized door/window with a comparatively smooth transition | **Fail:** incorrect geometry despite strong outside-region preservation |
| Restore missing A1 window, tight mask | FLUX.2 [klein] 4B, 512×1024, 4 steps, seed `260908` | Added a recognisable window inside the requested region | **Partial:** 100% of pixels outside the hard mask are exact, but the patch has a visible rectangular colour seam |
| Restore missing A1 window, tight mask | Qwen-Image-Edit-2511, 512×1024, 20 steps, seed `260909` | Added a credible vertical window with dark frame, crossbar, sill, and perspective | **Partial:** better geometry than full-frame FLUX but oversized and visibly rectangular with a hard mask; 12px feather makes the seam much less visible |
| Successive scale correction | FLUX.2 [klein] 4B, 512×1024, seed `260910` | Replaced the accepted Qwen window with a larger four-pane design | **Rejected:** the requested 45% width reduction was not achieved |
| Successive scale correction | Qwen-Image-Edit-2511, 512×1024, 20 steps, seed `260911` | Turned the window into a projecting bay-window form | **Rejected:** 1067.893s inference and a more severe geometry defect |
| Focused missing-window correction | FLUX.2 [klein] 4B, automatic 272×362 source crop rendered at 576×768, seed `260912` | Produced a small vertical window with plausible scale, frame, divider, sill, perspective, and wall integration | **Best local result:** 32.831s inference; 3px feather is visually clean with 99.797145% exact protected pixels; hard recomposition preserves 100% |

Pixel measurements use the source-sized deterministic composite, not the
model-sized raw redraw. A hard mask makes exact preservation measurable; a
feathered mask intentionally blends boundary pixels and therefore cannot be
100% identical outside the original binary region.

## Artifacts

- [`local-flux2-casual-bakery.png`](local-flux2-casual-bakery.png) — new scene
  from two reference authorities.
- [`local-sensenova-u1.5-casual-bakery.png`](local-sensenova-u1.5-casual-bakery.png)
  — stronger two-reference scene with correct hand count and one floating-object defect.
- [`local-sensenova-u1.5-casual-bakery-v2.png`](local-sensenova-u1.5-casual-bakery-v2.png)
  — accepted successive correction with the floating object removed.
- [`local-bartstyle-rev3-bakery-low.png`](local-bartstyle-rev3-bakery-low.png)
  and [`local-bartstyle-rev3-bakery-medium.png`](local-bartstyle-rev3-bakery-medium.png)
  — fast style-consolidation passes over the accepted SenseNova composition.
- [`local-bartstyle-rev3-bakery-t2i-seed-260919.png`](local-bartstyle-rev3-bakery-t2i-seed-260919.png)
  and [`local-bartstyle-rev3-bakery-t2i-seed-260920.png`](local-bartstyle-rev3-bakery-t2i-seed-260920.png)
  — from-scratch controls showing strong style but weak narrative constraint following.
- [`local-flux2-A9-protected-background-edit.png`](local-flux2-A9-protected-background-edit.png)
  — large environmental revision with character protection.
- [`local-flux2-A1-window-restoration.png`](local-flux2-A1-window-restoration.png)
  — broad-mask window attempt.
- [`local-flux2-A1-window-restoration-v2.png`](local-flux2-A1-window-restoration-v2.png)
  — tight-mask window attempt.
- [`local-qwen-A1-window-restoration.png`](local-qwen-A1-window-restoration.png)
  — Qwen hard-mask result; outside-mask pixels are 100% exact.
- [`local-qwen-A1-window-restoration.raw-edit.png`](local-qwen-A1-window-restoration.raw-edit.png)
  — Qwen's full model output before deterministic recomposition.
- [`local-qwen-A1-window-restoration-feathered.png`](local-qwen-A1-window-restoration-feathered.png)
  — the same raw edit recomposed with a 12-pixel feather, without inference.
- [`local-successive-A1-pass2-window-scale.png`](local-successive-A1-pass2-window-scale.png)
  and [`local-successive-A1-qwen-pass2-window-scale.png`](local-successive-A1-qwen-pass2-window-scale.png)
  — rejected full-frame successive corrections.
- [`local-focused-auto-A1-flux-window-feather3.png`](local-focused-auto-A1-flux-window-feather3.png)
  — accepted focused correction and current best local result.
- [`local-focused-auto-A1-flux-window-hard.png`](local-focused-auto-A1-flux-window-hard.png)
  — the same focused raw edit with 100% exact hard-mask protection.
- `A1-window-edit-mask*.png` — reproducible edit masks. White is editable.

Each output has a sibling JSON provenance record containing the exact prompt,
seed, checkpoint revision, input hashes, timings, and hardware/runtime details.

## What changed in the skill

This benchmark directly produced six interface changes:

1. `compose` separates new-scene synthesis from modification of an edit target.
2. Repeatable `--image-role` arguments make identity, style, geometry, layout,
   and lighting authority explicit and ordered.
3. `--mask-mode preserve-white` accepts protection masks as used by the Isekai
   recomposition workflow; `edit-white` remains the default for edit masks.
4. Masked edits retain a `.raw-edit` image by default, and `composite-mask` can
   retune mask polarity or feathering without paying for another inference.
5. Sidecars record editable-region change and protected-region exactness.
6. `--focus-mask` automatically renders a padded local crop at useful pixel
   density and restores it into the full source; `composite-mask --region` can
   retune its raw crop without another inference.

## Conclusion

FLUX.2 [klein] 4B remains credible for interactive multi-reference ideation and
large masked revisions, but its three-hand bakery result fails the final human
anatomy gate. SenseNova-U1.5 Q8 is the better local quality route for this kind
of identity-and-style scene: it generated exactly two functional hands and
followed the intended bread action, then removed its own floating-object defect
in one successive edit. The tradeoff is roughly three minutes per 896×1600 pass
and a 21.2 GB checkpoint.

BArtstyle REv3 is a useful second-stage specialist rather than a better scene
model. At low img2img strength it retained the already-solved two-hand bakery
composition and pushed it toward clean, high-contrast flat-color rendering in
about six seconds. From scratch it delivered the target rendering language but
failed the price-card and environment constraints. The production route is
therefore composition and correction first, style consolidation second, with a
fresh anatomy/identity gate after every generative pass.

Full-frame successive passes are still not universally reliable semantic
micro-repairs: both the FLUX and Qwen window scale-correction candidates were
worse than their parent. For a tiny spatial target, the decisive improvement
came from pixel density. Focused FLUX produced the best local window in 32.831
seconds, versus 1214.428 seconds for the first Qwen attempt and 1067.893 seconds
for the rejected second Qwen pass.

Exact locality is solved by compositing; boundary harmony and object geometry
still depend on the generated patch. Successive correction therefore means a
gated candidate lineage with crop-focused inference when the target is small,
not blindly feeding every output into another full-frame redraw.
