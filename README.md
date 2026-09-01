# Rogue AI Fieldbook

An opinionated field guide to open-source AI models and workflows actually tested by Rogue Paradigm.

This is not a directory of every model available. An entry belongs here only after it has been used in a real Rogue Paradigm project or a reproducible evaluation. Each field note records what was tested, where it was used, and what is still unknown.

## Catalog

| Category | Model | Used with | Field note |
| --- | --- | --- | --- |
| Text to speech | Qwen3-TTS | VoiceBox | [Read the note](models/text-to-speech/qwen3-tts.md) |
| Speech to text | Whisper via whisper.cpp | ElysListen | [Read the note](models/speech-to-text/whisper.md) |
| Music generation | ACE-Step 1.5 | ProdIA-MAX | [Read the note](models/music-generation/ace-step-1.5.md) |
| Sound generation | MMAudio | Voice Clone Studio | [Read the note](models/sound-generation/mmaudio.md) |
| Voice conversion | Chatterbox Voice Conversion | Voice Clone Studio | [Read the note](models/voice-conversion/chatterbox-vc.md) |

The machine-readable source of truth is [`catalog.json`](catalog.json).

## Repository layout

```text
models/          Tested model field notes, grouped by capability
applications/    Tested host applications and their validated model stacks
workflows/       Reproducible workflows such as ComfyUI graphs
templates/       Templates for new models and workflows
catalog.json     Machine-readable catalog index
scripts/         Lightweight repository validation
```

## Admission rule

A model or workflow must have:

1. been run successfully by Rogue Paradigm;
2. a named test context or consuming project;
3. an upstream source and license recorded;
4. honest notes that distinguish observations from upstream claims.

See [CONTRIBUTING.md](CONTRIBUTING.md) before adding an entry.

## Scope

Model weights and third-party source code are not mirrored here. Every model remains governed by its own upstream license and terms. This repository documents Rogue Paradigm's experience and may later host small integration examples and ComfyUI workflow files.

## License

The original content of this repository is released under the [MIT License](LICENSE). Referenced models and projects retain their own licenses.

## Tested applications

- [Voice Clone Studio](applications/voice-clone-studio.md): voice generation with Qwen3-TTS, voice conversion with Chatterbox, and sound generation with MMAudio
