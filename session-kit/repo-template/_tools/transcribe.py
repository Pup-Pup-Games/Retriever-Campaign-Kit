#!/usr/bin/env python
"""
transcribe.py — turn a session audio recording into a text transcript, locally.

Wraps faster-whisper (offline, free, private) to transcribe a recorded session into
a timestamped Markdown transcript that /retriever-recap then reads. There are two ways
to run it, depending on how you captured the audio:

  1. Single file  (--input):
       one recording of the whole table. Optionally run speaker diarization
       (--diarize, via whisperx) so lines are grouped by "Speaker N", which you map
       to player names once. Diarization is a guess; expect errors during crosstalk.

  2. ISO tracks  (--track, repeatable):  ← recommended when you record per-person mics
       one clean track per person (e.g. each Rodecaster Pro 2 multitrack input as its
       own WAV). Each track IS a known speaker, so there is nothing to guess: every
       line is labelled with that person, and the tracks are merged into one
       chronological transcript. More accurate than diarization, and no HF token.

       ASSUMPTION: the tracks are the *simultaneous* ISO recordings of one take — they
       start at the same instant and share a clock (which is how a Rodecaster / Craig
       multitrack capture works). Timestamps are compared across tracks to interleave
       them, so a track that starts late will land in the wrong place.

Recommended capture:
  - per-person mics: record each as its own track, use --track (best for transcription)
  - all in-person, one mic: one center-table mic to a single file, use --input
  - with a remote player: the Craig Discord bot (craig.horse) records a clean track
    per person; pass each as a --track, or transcribe the mixed-down file with --input

Usage:
  # ISO tracks — one per person; label=path, repeat --track per mic:
  python transcribe.py --track "GM=gm.wav" --track "Brann=p1.wav" \
      --track "Wren=p2.wav" --track "Aldra=p3.wav" --track "Hask=p4.wav" \
      --group your-campaign-wednesday \
      --out groups/your-campaign-wednesday/sessions/session-01/_work/transcript.md

  # ISO tracks on a GPU (much faster for a long session):
  python transcribe.py --track "GM=gm.wav" --track "Brann=p1.wav" \
      --device cuda --compute-type float16 ...

  # Single mixed file:
  python transcribe.py --input session.mp3
  python transcribe.py --input session.m4a --model medium --diarize

Dependencies (install once):
  pip install faster-whisper
  # optional speaker diarization (single-file --diarize only):
  pip install whisperx        # also needs a HuggingFace token for the diarization model
"""
import argparse, os, sys, datetime, json

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, ".."))


def hms(seconds):
    return str(datetime.timedelta(seconds=int(seconds)))


def default_out(input_path):
    base = os.path.dirname(os.path.abspath(input_path))
    return os.path.join(base, "_work", "transcript.md")


def parse_track(spec):
    """Parse a `Label=path` --track value into (label, path)."""
    if "=" not in spec:
        sys.exit(f"--track must be LABEL=path (got: {spec!r})")
    label, path = spec.split("=", 1)
    label, path = label.strip(), path.strip()
    if not label or not path:
        sys.exit(f"--track must be LABEL=path with both sides non-empty (got: {spec!r})")
    return label, path


def load_roster(group):
    """Return {character: player} for a group from config.json, or None if no config."""
    path = os.path.join(REPO, "config.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        cfg = json.load(f)
    g = cfg.get("groups", {}).get(group)
    if not g:
        sys.exit(f"Group '{group}' not found in config.json.")
    return g.get("roster", {})


def load_model(model_name, device, compute_type):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        sys.exit("faster-whisper is not installed. Run:  pip install faster-whisper")
    return WhisperModel(model_name, device=device, compute_type=compute_type)


def segments_of(model, input_path, language, label=None):
    """Transcribe one audio file; return [(start_seconds, text), ...], skipping blanks."""
    segments, info = model.transcribe(input_path, language=language, vad_filter=True)
    tag = f"[{label}] " if label else ""
    print(f"{tag}detected language: {info.language} (p={info.language_probability:.2f})",
          file=sys.stderr)
    out = []
    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        out.append((seg.start, text))
        print(f"  {tag}[{hms(seg.start)}] {text[:70]}", file=sys.stderr)
    return out


def transcribe_plain(input_path, model_name, language, device, compute_type):
    model = load_model(model_name, device, compute_type)
    return segments_of(model, input_path, language)


def transcribe_tracks(tracks, model_name, language, device, compute_type):
    """One shared model; transcribe each ISO track, label every line, merge by time.

    `tracks` is a list of (label, path). Returns [(start, "**Label:** text"), ...]
    sorted by start time so the separate per-person tracks read as one conversation.
    """
    for _, path in tracks:
        if not os.path.exists(path):
            sys.exit(f"No such track audio: {path}")
    model = load_model(model_name, device, compute_type)
    merged = []
    for label, path in tracks:
        print(f"\n=== {label}: {os.path.basename(path)} ===", file=sys.stderr)
        for start, text in segments_of(model, path, language, label=label):
            merged.append((start, f"**{label}:** {text}"))
    # stable sort keeps each track's internal order when two lines share a start time
    merged.sort(key=lambda r: r[0])
    return merged


def transcribe_diarized(input_path, model_name, language, device):
    try:
        import whisperx  # noqa: F401
    except ImportError:
        sys.exit("--diarize needs whisperx. Run:  pip install whisperx  "
                 "(and set a HuggingFace token for the diarization model). "
                 "Without it, run the plain transcript and label speakers by hand, "
                 "or record per-person tracks and use --track instead.")
    import whisperx
    dev = "cuda" if device == "cuda" else "cpu"  # whisperx needs an explicit device
    audio = whisperx.load_audio(input_path)
    model = whisperx.load_model(model_name, dev, compute_type="int8")
    result = model.transcribe(audio, language=language)
    align_model, meta = whisperx.load_align_model(language_code=result["language"],
                                                  device=dev)
    result = whisperx.align(result["segments"], align_model, meta, audio, dev)
    hf = os.environ.get("HF_TOKEN")
    diarize = whisperx.DiarizationPipeline(use_auth_token=hf, device=dev)
    diar = diarize(audio)
    result = whisperx.assign_word_speakers(diar, result)
    lines = []
    for seg in result["segments"]:
        spk = seg.get("speaker", "Speaker ?")
        lines.append((seg["start"], f"**{spk}:** {seg['text'].strip()}"))
    return lines


def write_markdown(lines, out_path, source_label):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(f"# Transcript — {source_label}\n\n")
        f.write("<!-- Raw transcript. Working file; not committed (see .gitignore). "
                "Feed to /retriever-recap. -->\n\n")
        for start, text in lines:
            f.write(f"[{hms(start)}] {text}\n\n")
    print(f"\nWrote {out_path}  ({len(lines)} segments)")


def main():
    ap = argparse.ArgumentParser(description="Transcribe a session recording locally.")
    ap.add_argument("--input", help="path to a single audio file (whole-table recording)")
    ap.add_argument("--track", action="append", default=[], metavar="LABEL=path",
                    help="one ISO track as LABEL=path (repeat per person); merged by time")
    ap.add_argument("--group", help="group key in config.json; checks --track labels "
                    "against the roster and warns on typos")
    ap.add_argument("--out", help="output .md path (default: <audio dir>/_work/transcript.md)")
    ap.add_argument("--model", default="large-v3",
                    help="whisper model: tiny|base|small|medium|large-v3 (default large-v3)")
    ap.add_argument("--language", default="en", help="spoken language code (default en)")
    ap.add_argument("--device", default="auto", help="auto|cpu|cuda (default auto)")
    ap.add_argument("--compute-type", default="int8",
                    help="faster-whisper compute type: int8 (CPU) or float16 (GPU). "
                         "default int8")
    ap.add_argument("--diarize", action="store_true",
                    help="single-file only: label speakers via whisperx (extra dependency)")
    args = ap.parse_args()

    if bool(args.input) == bool(args.track):
        sys.exit("Provide exactly one of --input (single file) or --track (ISO tracks).")
    if args.track and args.diarize:
        sys.exit("--diarize is for --input only. With --track, each track is already a "
                 "known speaker, so no diarization is needed.")

    if args.track:
        tracks = [parse_track(t) for t in args.track]
        if args.group:
            roster = load_roster(args.group)
            if roster is not None:
                known = set(roster) | {"GM", "DM", "Narrator"}
                for label, _ in tracks:
                    if label not in known:
                        print(f"warning: track label '{label}' is not a character in "
                              f"group '{args.group}' (roster: "
                              f"{', '.join(sorted(roster)) or 'none'})", file=sys.stderr)
        out = args.out or default_out(tracks[0][1])
        lines = transcribe_tracks(tracks, args.model, args.language,
                                  args.device, args.compute_type)
        source_label = f"{len(tracks)} ISO tracks ({', '.join(l for l, _ in tracks)})"
    else:
        if not os.path.exists(args.input):
            sys.exit(f"No such audio file: {args.input}")
        out = args.out or default_out(args.input)
        if args.diarize:
            lines = transcribe_diarized(args.input, args.model, args.language, args.device)
        else:
            lines = transcribe_plain(args.input, args.model, args.language,
                                     args.device, args.compute_type)
        source_label = os.path.basename(args.input)

    write_markdown(lines, out, source_label)


if __name__ == "__main__":
    main()
