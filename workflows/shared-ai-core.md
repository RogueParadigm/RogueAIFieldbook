# Shared AI Workflow Core

## Purpose

`src/rogue_ai_fieldbook` contains small, model-independent algorithms that were previously copied between project scripts. It is the shared boundary between local model runtimes and consuming projects.

## Current consumers

- Open ImageGen uses the same provenance conventions conceptually; migration to the package can be done independently of its model runtime.
- `E:\Dev\Tools\AIAudio` imports the loop search and ACE-Step session for Pride Apocalypse.
- `E:\Dev\ElysMusicGeneration` imports the same package for themed chill candidates and `intro → loop` packs.

## Modules

### `rogue_ai_fieldbook.core`

- `stable_seed`: SHA-256-based process-independent seeds.
- `file_sha256`, `portable_path`, `write_metadata`: portable provenance sidecars.

### `rogue_ai_fieldbook.audio`

- tempo/bar duration conversion;
- waveform-relative seam metrics;
- crossfaded loop construction;
- grid search over start positions and crossfade lengths;
- intro-to-loop bridge construction;
- loudest-energy event cropping;
- RMS normalization with a peak ceiling.

### `rogue_ai_fieldbook.ace_step`

`AceStepV1Session` loads the currently validated ACE-Step v1 runtime once and forwards explicit seeds and inference parameters for multiple candidates. Torch and ACE-Step are imported lazily, so the core test suite does not require CUDA or model weights.

## Contract

The Fieldbook package owns algorithms and evidence-backed defaults. Model weights, caches and third-party repositories remain in their dedicated runtime. Consumer projects own prompts, naming, editorial decisions and output placement.

## Validation

```powershell
python -m unittest discover -s tests -v
```

Tests use synthetic signals and an injected fake ACE-Step pipeline. They validate duration, seam search, intro bridging, energy cropping, level ceilings, stable identity and adapter parameter forwarding without loading a model.

