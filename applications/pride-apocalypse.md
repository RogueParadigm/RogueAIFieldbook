# Pride Apocalypse

## Verdict

**Tested** on 2026-09-03. A standalone local audio stack was installed for this project and used
to generate the game's placeholder music and sound effects.

## Identity

| Field | Value |
| --- | --- |
| What it is | Fixed-camera arcade farm-defence prototype, Unreal Engine 5.8 |
| Location | `E:\Dev\GameDev\Unreal Projects\PrideApocalypse` |
| Audio stack | `E:\Dev\Tools\AIAudio` — its own venv, its own Hugging Face cache |

## Model stack

| Capability | Model | Note |
| --- | --- | --- |
| Music generation | ACE-Step **v1 3.5B** | [Field note](../models/music-generation/ace-step-1.5.md) |
| Sound generation | MMAudio **large_44k_v2** | [Field note](../models/sound-generation/mmaudio.md) |

Note the versions: the catalog entry is named "ACE-Step 1.5", but what `pip install -e` of
[ace-step/ACE-Step](https://github.com/ace-step/ACE-Step) actually pulls at `main` is
`ACE-Step/ACE-Step-v1-3.5B`. The 1.5 checkpoints are a separate download. Whatever the catalog
says, this project ran v1.

## Environment

| Field | Value |
| --- | --- |
| Operating system | Windows 11 |
| GPU | NVIDIA GeForce RTX 3060 12 GB |
| Runtime | Python 3.12, PyTorch 2.6.0 with CUDA 12.4 |
| Install | `E:\Dev\Tools\AIAudio\install.ps1` (idempotent; re-running skips finished steps) |

Both models fit in 12 GB but **not at the same time** — they are run one after the other, not in
parallel. ACE-Step is loaded with `cpu_offload=True`.

## What was generated

Three music loops and nine sound effects, all under
`PrideApocalypse/SourceArt/AIAudio/`, imported into `/Game/PrideApocalypse/Audio/AIGenerated/`.

| Track | Tempo | Length |
| --- | --- | --- |
| Combat loop | 132 BPM | 16 bars, 29.09 s |
| Draft loop | 96 BPM | 8 bars, 20.00 s |
| Defeat sting | 80 BPM | 4 bars, 12.00 s |

## What we learned

### A generative model writes pieces, not loops

ACE-Step writes music with a beginning and an end. A game needs a bar that follows itself
forever. The working method was: generate long (80–90 s), take a stretch from the middle whose
length is a whole number of bars at the requested tempo, and cross-fade its tail back over its
head so the last sample leads into the first.

One fixed cross-fade length is not enough. Whether a seam is audible depends on what the music
happens to be doing there — a fade across a cymbal decay hides itself, one across a bare downbeat
does not. Searching a small grid of start points and fade lengths, scoring each by the size of
the wrap-around jump against the track's own median sample-to-sample step, took the worst seam
from 3.1× typical to 1.4× without regenerating anything. Re-cutting costs a second; a new render
costs minutes.

Scripts: `generate_pride_music.py`, `recut_loops.py`, `check_loops.py`.

### MMAudio puts the event wherever it likes

Text-to-audio (no video) works and is fast, but the requested event lands somewhere inside the
clip with near-silence around it, and the clip has to be cropped down to it.

Cropping at the first sample above a fraction of the peak fails two ways: a stray tick in the
lead-in captures the cut and the file starts on silence, and a sound that swells — cloth tearing,
machinery spinning up — never trips the threshold until it is half over. Sliding a 60 ms window
and taking the loudest one is reliable where the threshold was not. Guard the crop against the
end of the render, or clips silently come out a third of their requested length.

Match levels on **RMS with a peak ceiling**, not on peak. Peak-matching scores one sharp click in
silence the same as a sustained boom; they are nowhere near equally loud to a listener.

Seed from a stable digest of the effect name, not `hash(name)` — Python salts string hashes per
process, so nothing would ever be reproducible.

### Two effects the model would not give us

`SFX_Impact` ("bullet hitting a body") kept coming back as a thin tick — RMS 0.026 after level
matching, meaning almost all silence. `SFX_TurretBuild` puts its loud moment at the very end of
the render, so the usable crop starts 1.4 s before anything happens. Two prompt rewrites did not
fix either. Generating longer and cropping inside would be the next thing to try.

Honest summary: **seven of nine effects were usable on the first good pass; two were not.**

Scripts: `generate_pride_sfx.py`, `check_sfx.py`.

## Reproducing

```powershell
pwsh -File E:\Dev\Tools\AIAudio\install.ps1
E:\Dev\Tools\AIAudio\.venv\Scripts\python.exe E:\Dev\Tools\AIAudio\generate_pride_music.py
E:\Dev\Tools\AIAudio\.venv\Scripts\python.exe E:\Dev\Tools\AIAudio\recut_loops.py
E:\Dev\Tools\AIAudio\.venv\Scripts\python.exe E:\Dev\Tools\AIAudio\check_loops.py
E:\Dev\Tools\AIAudio\.venv\Scripts\python.exe E:\Dev\Tools\AIAudio\generate_pride_sfx.py
```

Named effects can be regenerated on their own: `generate_pride_sfx.py SFX_Impact`.

## Still unknown

- Whether ACE-Step **1.5** loops better than v1 out of the box; it was never downloaded here.
- Whether MMAudio's `large_44k_v2` is better than `medium_44k` for short game effects — Voice
  Clone Studio tested medium, this project only ran large.
- Nothing here has been judged by ear yet. Every claim in this note is a measurement.
