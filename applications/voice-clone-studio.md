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
| Original voice creation | Qwen3-TTS 1.7B VoiceDesign | Successful original French tavern-keeper voice at 24 kHz |
| Voice cloning | Qwen3-TTS 1.7B Base | Successfully reused the designed voice for a new French quest line |
| Preset voice generation | Qwen3-TTS 0.6B and 1.7B CustomVoice | Successful French 24 kHz outputs; 1.7B style instruction validated |
| Sound generation | MMAudio Medium 44 kHz | Successful text-to-audio 44.1 kHz output |

Both tests used an NVIDIA GeForce RTX 3060 12 GB with Python 3.12 and PyTorch 2.9.1/CUDA 12.8.

## Notes

- The VoiceDesign test created an original voice from a written description without a preset speaker. It produced 5.44 seconds of French speech at 24 kHz.
- The earlier CustomVoice tests used the built-in Qwen `Ryan` speaker. They validate preset-voice generation only and do not represent custom voice creation.
- The 1.7B test accepted an explicit energetic, brisk French delivery instruction and produced a 5.76-second result versus 6.24 seconds for the uninstructed 0.6B baseline.
- Qwen Base 1.7B full in-context cloning was validated using the generated VoiceDesign WAV and its exact transcript. The new line, `J'ai une quête pour vous, voyageur !`, produced 2.72 seconds of 24 kHz audio.
- The same Base workflow can use a user-provided recording when its transcript and the right to clone that voice are available.
- The sound test exercised Voice Clone Studio's own `FoleyManager`, including automatic MMAudio weight loading and output generation.
- MMAudio video-to-audio remains untested in this record.
- The first runs download several gigabytes of model and feature weights.
- SoX was not available in `PATH`, but it was not required for either successful generation path.

See the [Qwen3-TTS](../models/text-to-speech/qwen3-tts.md) and [MMAudio](../models/sound-generation/mmaudio.md) field notes for the exact results and licensing distinctions.
