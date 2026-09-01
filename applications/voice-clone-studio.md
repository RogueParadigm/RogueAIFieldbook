# Voice Clone Studio

## Verdict

**Tested** on Windows on 2026-09-01 for both voice generation and sound generation.

## Identity

| Field | Value |
| --- | --- |
| Upstream | [FranckyB/Voice-Clone-Studio](https://github.com/FranckyB/Voice-Clone-Studio) |
| Tested revision | `fe0b40458c5adcd03bff9df5ae668d9138e369a2` |
| Application license | Apache-2.0 |
| Interface | Modular Gradio application |

## Validated stack

| Capability | Engine | Result |
| --- | --- | --- |
| Voice generation | Qwen3-TTS 0.6B CustomVoice | Successful French 24 kHz output |
| Sound generation | MMAudio Medium 44 kHz | Successful text-to-audio 44.1 kHz output |

Both tests used an NVIDIA GeForce RTX 3060 12 GB with Python 3.12 and PyTorch 2.9.1/CUDA 12.8.

## Notes

- The voice test used the built-in Qwen `Ryan` speaker. It validates voice generation through the application, not zero-shot cloning from a user-provided recording.
- The sound test exercised Voice Clone Studio's own `FoleyManager`, including automatic MMAudio weight loading and output generation.
- MMAudio video-to-audio remains untested in this record.
- The first runs download several gigabytes of model and feature weights.
- SoX was not available in `PATH`, but it was not required for either successful generation path.

See the [Qwen3-TTS](../models/text-to-speech/qwen3-tts.md) and [MMAudio](../models/sound-generation/mmaudio.md) field notes for the exact results and licensing distinctions.
