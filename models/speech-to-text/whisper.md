# Whisper via whisper.cpp

## Verdict

**Tested** locally through ElysListen and retained in the Rogue Paradigm catalog.

## Identity

| Field | Value |
| --- | --- |
| Capability | Multilingual speech-to-text |
| Model project | [openai/whisper](https://github.com/openai/whisper) |
| Runtime | [ggerganov/whisper.cpp](https://github.com/ggerganov/whisper.cpp) |
| License | MIT for Whisper and whisper.cpp |
| Rogue Paradigm context | ElysListen for Unreal Engine |

## What we tested

- Local `whisper.cpp` inference on Windows through ElysListen
- Successful loading and initialization of the multilingual `ggml-medium.bin` checkpoint
- Packaged Unreal Engine runtime execution
- Model unloading and reloading during runtime tests

## Evidence

The local ElysListen packaged-demo logs dated 2026-08-31 record successful loading and initialization of `ggml-medium.bin`. The model weights are intentionally not stored in this repository.

## Still to document

- Test hardware and real-time factor
- Representative French and English audio set
- Word error rate or a smaller qualitative scorecard
- Noise, accents and overlapping-speaker failure cases
- Exact `whisper.cpp` revision
