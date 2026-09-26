---
name: yt-video-creator
description: Edit a folder of raw footage (camera clips, phone videos, photos) into a finished YouTube video with Remotion — either a 16:9 long-form video or a 9:16 YouTube Short — including shot selection, sped-up process shots, captions/titles, beat-synced music, and a rendered MP4. Use this whenever the user points at a folder of clips and wants a video made, edited, cut, or assembled from it (recipes, tutorials, vlogs, builds, trips, DIY, product demos), wants a YouTube upload or Short from raw footage, or wants a vertical cut of an existing edit — even if they don't say "Remotion" or "skill".
---

# YouTube video creator

Turn a folder of raw footage into a rendered YouTube video. You can't watch video, so the workflow is built around **contact sheets**: grids of timestamped frames you read as images. They tell you what's in each clip and give you the exact in/out points to write into the edit.

Bundled resources (paths relative to this skill's directory):
- `scripts/setup_project.sh` scaffolds a Remotion project next to the footage and links the media.
- `scripts/probe.py` lists the media with durations and resolutions.
- `scripts/sheets.py` makes contact sheets: an `overview` per clip, and `fine` sheets for a time range. `fine` also checks rendered output.
- `scripts/music.py` gives the song's loudness map, breaks and onsets, and BPM plus beat phase.
- `scripts/stills.mjs` renders sample frames from a composition without re-bundling each time.
- `assets/template/` is the Remotion project: `LongForm` (1920×1080) and `Short` (1080×1920) compositions. **All creative decisions go in `src/long-edit.ts` / `src/short-edit.ts`**, which are data only. Layout lives in the `.tsx` files; the look lives in `src/theme.ts`.
- `references/formats.md` covers YouTube specs, Shorts safe zones and pacing. Read it before planning the edit.

All Python scripts take `--project <remotion project dir>` so they use Remotion's bundled ffmpeg (see Gotchas). Put contact sheets and other scratch output in the session scratchpad, not the footage folder.

## Workflow

### 1. Ask what to make (one question round)

Before any heavy work, ask with a single multi-question prompt:
- **Format**: YouTube long-form 16:9 (default when unsure), a YouTube Short 9:16, or both.
- **Length**: long-form is usually 2–3 min for a process video; a Short is 30–45 s (60 s max is safest across platforms).
- **On-screen text language.**
- **Music**: the user supplies a file, or silent with a music slot. If they give a YouTube link, look up the title (the oEmbed endpoint `https://www.youtube.com/oembed?url=<link>&format=json` works with WebFetch). Don't download it yourself: ripping audio from YouTube breaks its terms, and a copyrighted track can get the upload claimed. Many links are YouTube Audio Library tracks, which are free to use: tell the user to download it from YouTube Studio → Audio Library and save it as `public/music.mp3`. Keep working while they do.
- **Story details** the footage can't tell you: a recipe, steps, names, what matters. Often the user has already given these; don't ask again.

If they say something like "check what's best for YouTube", decide yourself using `references/formats.md` and say what you picked.

### 2. Scaffold and inventory

```bash
bash <skill>/scripts/setup_project.sh <footage_dir> <name>-video   # → <footage_dir>/<name>-video/
python3 <skill>/scripts/probe.py <footage_dir> --project <proj>
```
Never modify or move the user's original files. The project only links to them.

### 3. See the footage

```bash
python3 <skill>/scripts/sheets.py overview <footage_dir> --out <scratch>/sheets --project <proj>
```
Read every sheet. Write a clip → content map as you go (e.g. "0583: hand mixer at sink; eggs poured 3:36"). Note cameos and happy accidents too (a pet, a reaction): they make great beats. Also note what's **missing**: if a step has no footage, plan to caption it over the nearest shot rather than inventing footage. Tell the user about the gap at the end.

Photos: tile them into one image with Pillow and look at them. They're usually the best-looking "hero" frames, good for the intro, the end card and a montage.

### 4. Plan the story, then find exact points

Map clips onto the story (the user's steps, or chronology). For each shot you intend to use, run a `fine` sheet over the relevant range, every 3–12 s depending on clip length:
```bash
python3 <skill>/scripts/sheets.py fine <clip> <start> <end> <step> --out <scratch>/sheets --project <proj>
```
Pick the in-point where the action **starts** (the ingredient hitting the bowl, not the empty bowl before it). The most common mistake is starting a shot a few seconds early, so the payoff happens after the cut.

For 9:16, also read off the horizontal position of the subject in each shot (as a % of frame width). That becomes the shot's `x` crop focus. A 9:16 crop keeps only ~32% of a 16:9 frame's width, so a centered default often loses the action.

### 5. Music (if provided)

```bash
python3 <skill>/scripts/music.py <proj>/public/music.mp3 --project <proj> [--window START LEN]
```
- **Long-form**: set `TARGET_SEC` to the song's duration so the video ends with the music. The outro card absorbs the difference. If the song is much shorter than the requested length, tighten the edit rather than looping the song, and tell the user.
- **Short**: choose `MUSIC_START_SEC` at a hard onset right after a break (the script lists breaks → next onset). Choose the end where a phrase decays into the next break, ideally 30–45 s later. Re-run with `--window <start> <len>` to get the BPM and beat phase for that stretch. Put those into `BEAT_SEC` / `BEAT_OFFSET_SEC`, and give every shot a length in beats, so cuts land on the beat.

### 6. Write the edit

Fill in `long-edit.ts` and/or `short-edit.ts`, replacing all the example data. Guidance:
- Speed up process footage heavily (4–30×) and keep human moments (reactions, tasting, talking) at 1×.
- **Long-form**: ~2.5–4 s per shot. Use sections with a caption that spans their shots, `chip` for quantities and specs, `counter` for elapsed-time moments (oven, drive, curing), and an outro that summarizes (e.g. full recipe) for viewers who pause.
- **Short**: the hook comes first (the payoff shot plus a punchy line), then 1–2 beats per shot, one- or two-word headlines, and an end card pointing to the caption/description.
- Theme: adjust `theme.ts` fonts and colors to the subject.
- Remove unused `LIST_CARD` or `MONTAGE` entries instead of leaving placeholders. Only render the compositions the user asked for.

`npm run typecheck`, then render sample stills (one per section is ideal) and **look at them**:
```bash
cd <proj> && node <skill>/scripts/stills.mjs LongForm <scratch>/stills 60 300 900 ...
```
Tile them into a grid with Pillow before reading, so one image shows many frames.

### 7. Render and verify

Render in the background (long-form takes several minutes):
```bash
cd <proj> && npx remotion render LongForm out/long.mp4     # or: Short out/short.mp4
```
Then check the actual output. Run `sheets.py fine out/<file>.mp4 0 <duration> 1 --width 180` for one frame per second, and read it looking for: empty or pre-action shots, subjects cropped out in 9:16, captions overlapping the subject or platform UI, text overflowing. Fix `from`/`x` values and re-render. Confirm the duration, resolution and audio stream with ffprobe.

### 8. Report

Give the user: output path(s), specs (resolution, duration, size), the structure of the edit, anything you assumed or that the footage lacked, and how to tweak it (edit file + `npm run studio` / render command). For a Short, also give a ready-to-paste caption/description. For long-form, offer a YouTube description with the full recipe or steps.

## Gotchas (all hit in practice)

- **Homebrew ffmpeg is often broken** (e.g. `Library not loaded: libx265.215.dylib`). Don't fix the system install unasked. The scripts use Remotion's bundled binary, which needs `DYLD_LIBRARY_PATH` set to its folder (handled in `_ff.py`). That build has no `drawtext`/`tile` filters and no raw `s16le` output, so tile images with Pillow and decode audio to WAV.
- **Media in `public/`**: symlinks pointing outside `public/` 404 in the render server, relative symlinks break inside the bundle, and symlinked JPEGs fail to decode. Use hard links for video (same disk, no extra space) and copies for photos. `setup_project.sh` does this.
- `trimBefore` is in source frames at the composition fps: `Math.round(from * FPS)`. With `playbackRate`, the source advances `speed ×` faster than the timeline.
- Big 1080p/4K clips render fine through `OffthreadVideo`. If a codec won't decode (HEVC 10-bit, ProRes RAW), transcode a proxy for that clip only.
- Keep the user's git hygiene: the project's `.gitignore` excludes `public/footage`, music and `out/`. Don't commit unless asked.
