# `_tools/` — the deterministic scripts

Every file mutation in this repo is done by a Python script here, not by hand, so templating
and publishing come out identical every run. The skills in `.claude/skills/` (see
[`.claude/README.md`](../.claude/README.md)) only parse your natural language and then call
these scripts. Pure stdlib except `transcribe.py`, which needs `faster-whisper`.

| Script | Called by | Does |
|---|---|---|
| `stonetop_lib.py` | (shared) | relationship vocabulary + file-mutation helpers; one source of truth |
| `new_note.py` | track, init, recap | stamp a player sheet or entity note from a template (never overwrites) |
| `scaffold.py` | init | build a group's folder structure + world stubs (idempotent) |
| `track.py` | track | apply one playbook-sheet change and log it |
| `relate.py` | relate | normalize a relationship, create notes, write inline field + reciprocal |
| `build_graph.py` | graph | render the Mermaid relationship map |
| `build_gazetteer.py` | map | render the map gazetteer(s) from place notes' map frontmatter + `## Map / Location` |
| `check_map.py` | map | reconcile an SVG map's `keys` layer against the notes' `key:`/`zone:` (exit 1 on drift) |
| `map_distance.py` | distance | distance/time between two map locations: geometric estimate + explicit `travel-to` routes |
| `transcribe.py` | **(you, manually)** | local transcription of a recorded session |
| `post_discord.py` | publish | post a recap to a Discord webhook |
| `publish.py` | table-publish | guard, commit, push, and post in one command |

The rest of this file documents `transcribe.py`, the one script you run by hand.

---

# Transcribing a session

`transcribe.py` turns a recording of a session into the timestamped Markdown transcript that
`/retriever-recap` reads. It runs **locally** via [faster-whisper](https://github.com/SYSTRAN/faster-whisper):
offline, free, and private (no audio leaves the machine, no API key).

Record the table and transcribe **after** the session. After-the-fact transcription is more
accurate than live transcription and less distracting at the table. The in-the-moment
`/retriever-track` and `/retriever-relate` skills cover anything you want captured live.

## Install (once)

```powershell
pip install faster-whisper
```

Optional, for diarization of a single mixed file only (see Mode B):

```powershell
pip install whisperx        # also needs a HuggingFace token in $env:HF_TOKEN
```

## Two ways to run it

How you record decides which mode you use.

### Mode A — ISO tracks (recommended): one mic per person

If you record **one clean track per person**, use `--track`. Each track *is* a known speaker,
so there is nothing to guess: every line is labelled with that person and the tracks are
merged into one chronological transcript. This is strictly more accurate than diarization,
especially during crosstalk, and needs no HuggingFace token.

The simplest way to get clean ISO tracks is a **single multitrack recorder** (for example a
Rodecaster Pro 2, a Zoom PodTrak, or any USB interface feeding a DAW): one mic per input,
each input written to its own WAV by the same recording. A virtual recorder such as **Craig**
on Discord does the same thing for an all-remote table, writing one file per speaker.

```powershell
python _tools/transcribe.py `
  --track "GM=gm.wav" `
  --track "Brann=brann.wav" `
  --track "Wren=wren.wav" `
  --track "Aldra=aldra.wav" `
  --track "Hask=hask.wav" `
  --group your-campaign `
  --out groups/your-campaign/sessions/session-01/_work/transcript.md
```

- `--track "LABEL=path"` once per person. The **LABEL** is what appears on every one of that
  person's lines (use the character name, or `GM`).
- `--group <key>` (optional) checks your labels against that group's roster in `config.json`
  and warns on a typo.
- **The tracks must come from one synchronized recording** — same start, shared clock. A
  single multitrack capture gives you this for free. The script interleaves by timestamp, so
  a track recorded separately (a different start) would land in the wrong place.

#### Capturing a remote player

If one player joins over voice chat (Discord, etc.), the goal is to land their voice as one
more ISO track in the **same** recording as the in-room mics, so it shares the clock. Two
common ways:

- **Bring them in through the board.** Route the call's audio into a channel on your
  multitrack recorder (e.g. a Rodecaster's USB channel) so it records as its own synced
  track, and use the board's mix-minus so they hear the table without echoing themselves.
- **Record the call separately, then align.** A virtual recorder like Craig captures each
  remote speaker to a file; if it's not part of your in-room recording, line up the start
  before transcribing so timestamps match.

> **Fidelity note:** a voice-chat track sounds a little lower-fi than an in-room dynamic mic.
> That's fine for transcription. If you later want podcast-grade quality, have the remote
> player also record themselves locally and send you that file for the *podcast edit only* —
> keep using the synced track for transcription, since the local file won't share the clock.

### Mode B — single file: one recording of the whole table

If you have one recording (a center-table mic, or a mixed-down file), use `--input`.

```powershell
# plain transcript, speakers not separated:
python _tools/transcribe.py --input session.mp3

# attempt to label speakers (a guess; expect errors during crosstalk):
python _tools/transcribe.py --input session.m4a --diarize
```

`--diarize` uses whisperx to group lines as `Speaker 1`, `Speaker 2`, …, which you map to
names by hand once. It is a best-effort guess. If you can record per-person tracks, prefer
Mode A and skip diarization entirely.

## Running on a GPU (much faster)

`large-v3` on CPU is slow for a 3–4 hour session. If the machine has an NVIDIA GPU, add:

```powershell
--device cuda --compute-type float16
```

This works in both modes and is the difference between minutes and hours. CUDA needs
NVIDIA's cuBLAS/cuDNN libraries available; if that errors, fall back to the default
`--device cpu` (slower, but always works).

## All options

| Flag | Default | Meaning |
|---|---|---|
| `--track LABEL=path` | — | one ISO track; repeat per person (Mode A) |
| `--input PATH` | — | one whole-table audio file (Mode B); mutually exclusive with `--track` |
| `--group KEY` | — | check `--track` labels against the group roster in `config.json` |
| `--out PATH` | `<audio dir>/_work/transcript.md` | where to write the transcript |
| `--model NAME` | `large-v3` | `tiny`\|`base`\|`small`\|`medium`\|`large-v3` (smaller = faster, less accurate) |
| `--language CODE` | `en` | spoken language |
| `--device` | `auto` | `auto`\|`cpu`\|`cuda` |
| `--compute-type` | `int8` | `int8` for CPU, `float16` for GPU |
| `--diarize` | off | Mode B only: label speakers via whisperx |

## Output, and what happens next

The script writes a single timestamped Markdown file, by convention to
`groups/<group>/sessions/session-NN/_work/transcript.md`:

```
# Transcript — 5 ISO tracks (GM, Brann, Wren, Aldra, Hask)

<!-- Raw transcript. Working file; not committed (see .gitignore). Feed to /retriever-recap. -->

[0:00:04] **GM:** You come over the rise and the mill is burning.
[0:00:11] **Brann:** I draw my bow and look for the nearest figure.
...
```

Everything under `_work/` and all audio (`*.wav`, `*.mp3`, …) is git-ignored, so the raw
transcript and the recordings stay local. Only the polished `session-NN.md` recap is
committed.

Then run **`/retriever-recap <group> session-NN`**, which reads this transcript and writes the
player-facing recap.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `faster-whisper is not installed` | `pip install faster-whisper` |
| `--diarize needs whisperx` | `pip install whisperx` and set `$env:HF_TOKEN`, or record ISO tracks and use Mode A |
| `Provide exactly one of --input or --track` | you passed both, or neither — pick one mode |
| `warning: track label 'X' is not a character …` | a `--track` label doesn't match the `--group` roster; fix the label (or drop `--group`) |
| Lines from different people land out of order | the ISO tracks weren't recorded in sync — they must share one start/clock |
| Transcription is very slow | use `--device cuda --compute-type float16`, or a smaller `--model` |
