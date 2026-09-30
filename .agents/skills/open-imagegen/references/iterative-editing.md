# Iterative editing

Use this workflow when a first edit is directionally useful but fails one or
more production criteria. Successive correction helps only when every pass has
one target and an explicit accept/reject gate.

## Pass order

Resolve dependencies before appearance:

1. semantic presence and placement;
2. geometry, scale, pose, or identity;
3. material, palette, style, and lighting;
4. boundary blending and deterministic recomposition.

Do not ask one pass to solve several levels. A geometry pass should not also
restyle the scene. A blending pass should not redesign the object.

## Candidate lineage

- Start each pass from the latest **accepted composite**, never a rejected
  candidate or an unmasked raw redraw.
- Give the edit target first, followed by narrowly scoped reference authorities.
- Name outputs by pass and target, for example `panel-p02-window-scale.png`.
- Keep the `.raw-edit` and JSON sidecar. The input hashes preserve lineage.
- Reuse `composite-mask` to tune polarity or feathering before paying for
  another inference.

## Acceptance gate

Inspect both the raw edit and the composite. Accept a pass only if all three are
true:

1. The single stated target is materially closer to the requested result.
2. Protected invariants remain intact. For a hard mask, use the sidecar's
   `mask_metrics.protected_exact_pct`; production preservation should be 100%.
3. The pass introduces no defect more expensive than the one it fixes.

If any check fails, retain the artifact as evidence but do not use it as the
next parent. Rebase on the last accepted composite and change one variable:
prompt, mask, reference authority, seed, or model.

## Routing and stopping

- Use FLUX.2 [klein] 4B for fast exploration and broad environmental/style
  revisions. If a masked target is small, retry with `--focus-mask` before
  changing models.
- Escalate difficult local geometry or identity to Qwen-Image-Edit-2511 only
  after focused FLUX fails; one 20-step draft takes about 20 minutes on the
  validated RTX 3060.
- Prefer a compositing-only feather pass for a correct object with a visible
  edge. Feathering relaxes exactness in a small boundary band, so record the
  new mask metrics.
- After three consecutive rejected passes on the same target, stop iterating.
  Change the crop/mask strategy, provide a stronger geometry reference, or use
  deterministic asset compositing instead of accumulating redraws.

## Isekai finding

On the A1 missing-window test, the first Qwen pass solved semantic presence and
basic geometry. A subsequent FLUX request to shrink it changed the design; a
second Qwen pass created a projecting bay window. Both were rejected. A fresh
FLUX pass focused on a padded 272×362 source crop produced the best local window
in 32.831 seconds. This is why “successive” means gated lineage plus adequate
target pixel density, not blindly feeding every output forward.
