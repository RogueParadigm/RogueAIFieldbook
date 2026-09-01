# Chatterbox Voice Conversion

## Verdict

**Tested** in Voice Clone Studio on Windows on 2026-09-01.

## Identity

| Field | Value |
| --- | --- |
| Upstream | [resemble-ai/chatterbox](https://github.com/resemble-ai/chatterbox) |
| Capability | Speech-to-speech voice conversion |
| License | MIT |
| Tested with | Voice Clone Studio |

## Test context

- Voice Clone Studio revision: `fe0b40458c5adcd03bff9df5ae668d9138e369a2`
- Platform: Windows
- GPU: NVIDIA GeForce RTX 3060 12 GB
- Python: 3.12
- PyTorch: 2.9.1 with CUDA 12.8
- Source: a user-provided 2.56-second spoken performance, transcoded to mono 24 kHz PCM for the test
- Target reference: the original French tavern-keeper voice generated during the Qwen3-TTS VoiceDesign evaluation

## Observed result

Voice Clone Studio completed the conversion successfully after loading the Chatterbox voice-conversion weights. The resulting WAV was mono 24 kHz and exactly 2.56 seconds long. It retained the timing and performance of the source recording while applying the target voice identity.

This was a voice-to-voice conversion, not transcription followed by text-to-speech. The source recording and converted audio are personal evaluation artifacts: both remain in the ignored local evaluation directory and are not included in this repository.

## Boundaries

- This test covers one short French performance and one designed target voice.
- Long-form stability, cross-language conversion, and batch processing remain untested.
- The first run downloads the model weights.
