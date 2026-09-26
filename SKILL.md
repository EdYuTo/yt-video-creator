---
name: yt-video-creator
description: Edit a folder of raw footage (camera clips, phone videos, drone/DJI files, photos) into a finished YouTube video with Remotion — a 16:9 long-form video or a 9:16 YouTube Short — including shot selection, sped-up process shots, dialogue kept with silences cut and subtitles, captions/titles, background music (beat-synced for Shorts, ducked under speech), credits and bloopers, privacy blur of bystanders, and a rendered MP4. Use this whenever the user points at a folder of clips and wants a video made, edited, cut, or assembled from it (recipes, food/restaurant vlogs, travel, tutorials, builds, DIY, product demos), wants a YouTube upload or Short from raw footage, or wants a vertical cut of an existing edit — even if they don't say "Remotion" or "skill".
---

# YouTube video creator

You turn a folder of raw footage into a rendered YouTube video. You can't watch video or hear audio, so the workflow runs on proxies for both:
- **contact sheets** (grids of timestamped frames you read as images) for what the footage looks like;
- **transcripts** (local speech-to-text with word timings) for what people say.

The edit is written as **`plan.json`** in *source time*, meaning the timestamps you read off sheets and transcripts. `build_edit.py` then:
- links or proxies the media;
- cuts silences out of dialogue;
- places subtitles, music, beats and cards;
- writes `src/edit-data.ts` for the Remotion template to draw.

You never do frame math by hand.

Bundled resources (paths relative to this skill's directory; `<skill>` below):

| file | what it does |
|---|---|
| `scripts/setup_project.sh` | Scaffolds `<footage>/<name>/`: Remotion template, `source/` links to originals, photos in `public/footage/`, `media.json` from probing, and a `plan.json` skeleton with the clip table |
| `scripts/probe.py` | Media list: codec, bit depth, resolution, fps, audio, and whether each clip should be `link` or `proxy` |
| `scripts/sheets.py` | `overview` (per-clip grid) and `fine` (several `START-END:STEP` ranges of one clip, or of a render) contact sheets |
| `scripts/setup_speech.sh` | One-time private venv (`~/.cache/yt-video-creator`): mlx-whisper or faster-whisper, numpy, OpenCV and the YuNet face model. Prints its python path |
| `scripts/transcribe.py` | `skim` whole clips (small model) → readable transcripts; `words` for chosen windows (large-v3-turbo) → `transcripts/words.json` |
| `scripts/music.py` | Song loudness map, breaks → onsets, BPM and beat phase |
| `scripts/build_edit.py` | `plan.json` → media + `src/edit-data.ts` + `edit-map.json` (also `npm run build`) |
| `scripts/speech_map.py` | Loudness-based speech islands. Only useful for quiet footage |
| `scripts/faces.py` | `scan` a render for faces mapped to shots; `review` tiles the flagged frames |
| `scripts/audio_levels.py` | Loudness of a render per segment kind (talk / b-roll / cards / post) |
| `assets/template/` | Remotion project: `LongForm` 1920×1080, `Short` 1080×1920, `Thumbnail` 1280×720 still, `render.mjs`, `stills.mjs`, `theme.ts` |
| `references/plan.md` | **The plan.json format, with a music-driven and a talk example. Read before writing the plan.** |
| `references/talk.md` | The dialogue workflow in detail (transcription pitfalls, choosing conversations, subtitles, ducking) |
| `references/formats.md` | YouTube and Shorts specs, safe zones, pacing, music licensing |

Python scripts take `--project <proj>` so they use Remotion's bundled ffmpeg (see Gotchas). `transcribe.py`, `speech_map.py` and `faces.py` need the venv python from `setup_speech.sh`; the rest run on system `python3` with Pillow. Put scratch output (sheets, stills) in the session scratchpad, not the footage folder.

## Workflow

### 1. Ask what to make (one question round)

Ask everything in one multi-question prompt. Skip whatever the user already told you, and if you can't ask (e.g. you're a subagent), choose defaults and list them as assumptions.
- **Format**: YouTube long-form 16:9 (the default), a Short 9:16, or both. "Whatever's best for YouTube" means long-form unless the footage is under ~1 min.
- **Length**: process video 2–4 min; talk/vlog 5–10 min; a Short 30–45 s.
- **On-screen text / subtitle language.**
- **Music**: a file the user supplies, or none. For a YouTube link, look up the title (`https://www.youtube.com/oembed?url=<link>&format=json` via WebFetch). Don't download it: ripping audio from YouTube breaks its terms, and a copyrighted track can get the upload claimed. YouTube Audio Library tracks are free; the user downloads the file and saves it as `public/music.mp3`. Keep working meanwhile.
- **Talk**: does the footage have conversation that matters, and in which language(s)? This switches on the dialogue workflow.
- **Other people on camera**: should bystanders or friends who didn't consent be blurred? Default to blurring faces that aren't the creator.
- **Story details** the footage can't tell you: a recipe, steps, place names, what matters, funny moments to keep (e.g. bloopers).

### 2. Scaffold and inventory

```bash
bash <skill>/scripts/setup_project.sh <footage_dir> <name>-video
```
Read the probe table it prints. The `link`/`proxy` column decides media handling: 10-bit, HEVC, >1080p or >30 fps clips get proxies of only the used ranges. Never modify, move or delete the user's originals; `source/` only links to them. If the footage has talk, run `bash <skill>/scripts/setup_speech.sh` now (it takes a few minutes the first time).

### 3. See (and hear) the footage

```bash
python3 <skill>/scripts/sheets.py overview <proj>/source --out <scratch>/sheets --project <proj> -n 8 --width 256
```
Use small thumbnails: sheets are the biggest token cost of this workflow. For DJI footage, the `.lrf.mp4` proxies in `source/` decode much faster; they're fine for sheets and transcription, not for rendering. Read every sheet and write a clip → content map. Note cameos and happy accidents, and what's **missing**: if a step has no footage, caption it over the nearest shot rather than inventing footage, and tell the user.

Tile the photos into one image with Pillow and look at them. They're the best "hero" frames for the intro, section openers, the montage and the end card.

**Talk footage**: transcribe before choosing shots. Contact sheets can't tell you whether a conversation is interesting.
```bash
$VENV_PY <skill>/scripts/transcribe.py skim <id> [<id>...] --project <proj> --language pt
```
Read `transcripts/<id>.txt`. Follow `references/talk.md` for choosing conversations and getting word timings.

### 4. Plan the story, then find exact points

Map clips onto the story (the user's steps, the courses of a meal, the chronology). Then pin exact points:
- **Visual shots**: run `fine` sheets over the candidate ranges, several ranges per sheet:
  `sheets.py fine <proj>/source/<file> 30-40:2 95-110:3 --out ... --project <proj>`.
  Start where the action **starts** (the ingredient hitting the bowl, not the empty bowl before it). The most common mistake is starting a few seconds early, so the payoff lands after the cut.
- **Talk windows**: get word timestamps with `transcribe.py words <id>:<start>-<end> ...`. `build_edit.py` cuts the silences from them, and you write the subtitles from the transcript (translated if needed).
- **9:16 crops**: read the subject's horizontal position (% of width) per shot for `x`. Only ~32% of a 16:9 frame's width survives.

### 5. Music (if provided)

```bash
python3 <skill>/scripts/music.py <proj>/public/music.mp3 --project <proj> [--window START LEN]
```
- **Music-driven long-form** (little or no talk): `mode: "bed"`, optionally `matchSong: true` so the outro card stretches until the song ends. If the song is much shorter than the requested video, tighten the edit rather than looping, and tell the user.
- **Talk long-form**: `mode: "broll"` (the `auto` default when talk items exist). Music plays only under b-roll, photos and cards, at around 0.15 volume, and is silent under dialogue. The song position advances only while it's audible, so a short song rarely needs to loop.
- **Short**: start at a hard onset right after a break (the script lists breaks → next onset), end where a phrase decays, and re-run with `--window` for BPM and beat phase. Shot lengths are then in beats.

### 6. Write plan.json and build

Fill `plan.json` following `references/plan.md`:
- `long.intro`: drawn over the first section, whose first item should be the hero shot or photo.
- `long.sections[].items`: b-roll, talk windows with subtitles, photos.
- `long.listCard`, `long.outro`, `long.credits`, `long.post` (black-and-white bloopers after the credits).
- `long.music`, `blur`, `short`.

Guidance:
- Speed up process b-roll heavily (4–30×). Keep human moments (reactions, tasting, talk) at 1×.
- **Long-form pacing**: ~2.5–4 s per b-roll shot. Open each section on a photo or wide shot. Use `chip` for quantities, `counter` for elapsed time, and an outro summary (e.g. the full recipe) for viewers who pause.
- **Short**: the hook first (payoff shot plus a punchy line), 1–2 beats per shot, one- or two-word headlines, and an end card pointing to the caption.
- Adjust `src/theme.ts` fonts and colors to the subject.

```bash
cd <proj> && npm run build && npm run typecheck
node stills.mjs LongForm <scratch>/stills <frame> <frame> ...   # frames: see edit-map.json (seconds × 30)
```
`build_edit.py` prints the total length, talk seconds, music runs and WARN lines (e.g. talk windows missing word timestamps). Fix every WARN. Look at the stills (tile them into one image), one per section.

### 7. Render and verify

```bash
cd <proj> && npm run render:long      # or render:short; runs in the background, minutes to ~15 min
```
Always render with `render.mjs` (the npm scripts): it keeps previous versions (see "Protect the user's work"), and `npx remotion render` both overwrites the output and copies all of `public/` on every render.

Then verify the output. Don't skip this: it's where the real bugs show up.
- **Picture**: `sheets.py fine out/long.mp4 0-<dur>:2 --width 180 --cols 10`. Look for pre-action or empty shots, subjects cropped out, text overlapping the subject or subtitles, and overflow.
- **Sound** (talk videos): `audio_levels.py out/long.mp4 --project <proj>`. Talk should be around −20 dBFS, music-only b-roll 6–8 dB below it, and the peak under −1 dBFS.
- **Privacy** (anyone besides the creator on camera): `$VENV_PY faces.py scan out/long.mp4 --project <proj> --edges`, then `faces.py review ...` and look at the tiles. `--edges` catches people half out of frame (a friend leaning in from the side, in profile, mostly hair), which the plain scan missed in practice. For every real hit, check the neighbouring seconds with crops of that edge: people lean in and out. About half of the hits are hands, glasses or food. Add `blur` boxes (source time) or replace the shot, rebuild, re-render and re-scan. Tell the user the detector misses profiles and that boxes are static, and point them to the timestamps worth watching.
- Confirm the specs with ffprobe (resolution, duration, audio stream).

**Thumbnail** (offer it for every long-form video): a reaction face plus the subject (the dish, the build) makes a strong 2-panel split. Scan the talk windows around the best reaction with `sheets.py fine`, then grab full-res frames with ffmpeg and crop to the face to compare expressions. Use a ≤4-word title and an optional hook badge, but only claims the footage backs up (a price from the transcript, not a guess). Add a `thumbnail` block (`references/plan.md`), `npm run build`, `npm run render:thumb`, and look at the result.

### 8. Report

Tell the user:
- the output path and specs;
- the structure (sections with source clip@time, what was kept and cut and why);
- the music handling;
- assumptions, missing footage, privacy fixes and where to double-check;
- how to tweak it: edit `plan.json` → `npm run build` → `npm run render:long`, or `npm run studio` to preview;
- after a re-render, which previous version was kept in `out/versions/` (and that you'll delete it only if asked).

Offer a ready-to-paste YouTube description (recipe or steps, music credit). For a Short, give the post caption.

## Protect the user's work

People review, upload and share renders while you work, so a file you "just regenerate" may be the one they already published.
- **Never overwrite or delete an existing render, thumbnail or user file.** Always render through `render.mjs` (the npm scripts). It renders to a temp file, and only on success moves the previous output to `out/versions/<name>-vN.<ext>` with the `plan.json` snapshot that produced it, then logs the render in `out/versions/log.jsonl`. Pass `--note "what changed"` so the log explains each version: `npm run render:long -- --note "blur friend at 1:07"`.
- **Old versions are deleted only when the user asks**, for example after they confirm the new one ("this one is perfect, delete the backup"). When you report a re-render, name the kept previous version and its size so they can decide.
- **Outside a project scaffolded by this skill** (an older project, one made by another agent, the user's own files), back up before replacing anything: e.g. `mv out/video.mp4 out/video-prev.mp4`. Say so in the report.
- The originals in the footage folder are read-only for you. `source/` only links to them, and `setup_project.sh` refuses to scaffold over an existing project.
- To go back to an earlier edit, restore `out/versions/<name>-vN.plan.json` as `plan.json`, then `npm run build` and render. First make sure the current plan is saved: it is if it was rendered (`out/<name>.plan.json`); otherwise copy it aside.

## Gotchas (all hit in practice)

- **Homebrew ffmpeg is often broken** (`Library not loaded: libx265.215.dylib`). Don't fix the system install unasked. The scripts use Remotion's bundled binary via `_ff.py`, and so must you: `DYLD_LIBRARY_PATH` needs to point at its folder. It has scale, crop, trim, concat, loudnorm, silencedetect, libx264, h264_videotoolbox and videotoolbox decode. It has **no** `fps` filter (use `-r 30`), `drawtext`, `tile` or s16le muxer (decode audio to WAV; tile images with Pillow). mlx-whisper shells out to the system ffmpeg, so `transcribe.py` passes it decoded arrays instead.
- **Media and `public/`**: the render server 404s on symlinks leaving `public/`, and symlinked JPEGs fail to decode. `build_edit.py` hard-links `link` clips (copying if on another disk, with a warning) and writes proxies. Raw footage never goes in `public/`.
- **Proxies** are for heavy sources (10-bit HEVC at 2.7K/4K, 60p, files of tens of GB). They're transcoded per used range at 1080p30 H.264 with loudnorm, at ~3–4× realtime with videotoolbox, and they make stills and renders fast. Changing in/out points outside a proxy range triggers a new proxy on the next build.
- **Transcription**: always force `--language`. Auto-detect once turned 40 minutes of Portuguese into garbage Japanese because a waiter spoke first. Loudness-based silence detection fails in noisy places, so cut from word timestamps. More in `references/talk.md`.
- `edit-data.ts` is generated: edit `plan.json` instead. Frames in `edit-map.json` are the ground truth for "what's at 3:34".
- Rendering takes about 2–4 min per video minute at 1080p, and much longer from raw 4K/10-bit, which is another reason for proxies. Use stills to check changes before a full re-render.
- Keep the user's git hygiene: `.gitignore` excludes `public/footage`, `source/`, music, transcripts and `out/`. Don't commit unless asked.
