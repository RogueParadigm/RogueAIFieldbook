# Recursive music loop banks

## Purpose

Build a long-running music bed from a short intro and several named, musically related segments. A sub-second waveform bridge may remove a click, but it cannot establish musical continuity. This workflow conditions every generation on a real 30-second audio prior.

## Default contract

- Generate one autonomous 120-second source.
- Export source seconds `0–30` as the intro.
- Use source seconds `30–60` as prior 0.
- Preserve prior 0 as the first 30 seconds of variant 1 and extend it by 90 seconds.
- Use variant 1 seconds `30–60` as prior 1.
- Repeat until ten 120-second variants exist.
- For every variant, preserve its last 30 seconds as an exit prior, extend it with a conclusive generation, then export only the 30 fresh seconds as that variant's ending.
- Measure every `variant end → variant start` pairing over a four-second window.
- At playback, sample among the three lowest-cost successors, exclude the two most recent variants, and use a stable seed.
- For finite playback, stop after the selected number of complete variants and play the ending conditioned from the current variant.

The recursive window advances musical material while the text prompt, tempo and instrumentation keep the family coherent. Each rendered segment records its input-prior hash, output hash, seed and next-prior hash.

## Shared implementation

- `rogue_ai_fieldbook.ace_step.AceStepV1Session.extend_right` maps the contract to ACE-Step's local `extend` task.
- `rogue_ai_fieldbook.continuation.LoopBankPlan` validates durations and the ACE-Step 240-second ceiling.
- `split_extended_generation` preserves the prior-prefixed 120-second result and extracts seconds `30–60` for the next step.
- `build_transition_costs` compares end/start loudness and coarse spectral signatures.
- `schedule_variants` produces a reproducible, varied route without immediate repeats.
- `program_duration_seconds` and `closest_loop_count` map a target duration to the nearest complete `intro → variants → ending` program.
- `smooth_join_target` removes the final PCM boundary step over 20 ms; the 30-second audio prior remains the musical-continuity mechanism.

With the default 30-second intro, 120-second variants, four-second inter-variant crossfade and 30-second ending, `N` variants last `30 + 120N + 30 - 4(N-1)` seconds. A ten-minute target therefore selects five variants and lasts 644 seconds. Exact arbitrary durations require additional exit cues generated from multiple positions inside every variant.

## Transition review contract

For ten variants, publish all 90 directed non-self pairs. A review audition concatenates the source’s final five seconds and the target’s first five seconds into an exact ten-second judgment window. Use only a roughly 12 ms edge fade to prevent start/stop clicks; do not apply the production crossfade because it can hide a poor musical match. Persist good/bad decisions by directed pair. Exclude bad edges from scheduling and rank explicitly approved edges before unreviewed edges.

`ranked_successors` centralizes the deterministic best-to-worst order used to publish these pairs. Fixed intro-to-first-loop and loop-to-conditioned-ending edges should also be reviewable, although only loop-to-loop rejections affect random scheduling.

## Limitations

Recursive conditioning guarantees lineage and strong stylistic continuity, not mathematical equality between arbitrary endpoints. The transition matrix therefore constrains random playback, and a multi-second equal-power crossfade remains a technical safety layer. The ending bank is linear in size—one outgoing ending per variant—because the last played variant is known. For sample-exact arbitrary loop-to-loop transitions, generate dedicated edge clips or use a common musical return anchor; that grows quadratically with the number of variants.

ACE-Step v1 accepts at most 240 seconds including the preserved context. The default 30 + 90 second operation stays well within that bound.
