---
name: stream-highlights
description: Mine a long stream recording (Twitch/YouTube/Kick VOD, podcast or gameplay session, hours long) for its most engaging, potentially viral moments and turn them into a SET of vertical Shorts/TikToks/Reels — facecam + gameplay layouts, word-synced karaoke captions, hook titles, punch-in/shake/sticker effects, freeze-frame punchlines — plus a report with titles, captions, hashtags and risks per clip. Use this whenever the user wants highlights, clips, shorts or "viral moments" cut from a stream, VOD, livestream or long recording, even if they don't say "skill" or name the tools. For editing a folder of normal footage into one video, use yt-video-creator instead (this skill builds on it).
---

# Stream highlights → Shorts

You turn one long recording (hours, tens of GB) into a **set** of 15–60 s vertical Shorts. You can't watch hours of video, so the approach is to **mine cheaply, then look closely only at the candidates**:
- decode the audio once;
- transcribe everything with a fast local model;
- rank 30-second windows by what's said and how loud it is;
- **read** around the best candidates, which is where the real choices happen;
- check the visuals of the chosen moments only.

Each chosen moment becomes its own Short, and a report ties the set together.

This skill builds on **yt-video-creator** (the parent directory in the same repo). It reuses that skill's ffmpeg locator, `transcribe.py`, `sheets.py`, faces tooling, Remotion scaffold and versioned `render.mjs`. Read its **Gotchas** and **Protect the user's work** sections: they all apply here.

| file | what it does |
|---|---|
| `scripts/setup_stream.sh <vod> [name]` | Base scaffold plus the stream component, `source/vod.<ext>` alias, `shorts.json` from the example, `render-shorts.sh`, and the npm scripts `build:shorts` / `render:shorts` |
| `scripts/vod_audio.py` | Decodes the whole VOD to a 16 kHz WAV once (~25 s for 3.5 h) plus loudness signals: per-10-min energy arc and peaks → `analysis/audio.json` |
| `scripts/skim_vod.py lang/skim/ctx` | Detects the language on 3 windows; chunked, resumable skim transcription merged into `analysis/vod_skim.txt` (with a loudness column); `ctx` prints the transcript around time ranges |
| `scripts/find_moments.py` | Ranks 30-s windows (laughter, swearing, surprise, chat address, game events, story setups, speech density, loudness; pt/en/es patterns) → `analysis/moments.md`, a reading list |
| `scripts/detect_cam.py` | Finds the facecam overlay box (the face at a fixed spot across samples, refined by the overlay's static borders) and writes a check image |
| `scripts/build_shorts.py` | `shorts.json` (VOD time) → per-cut-group proxies (1440p/1080p 30 fps, loudnorm −14 LUFS) + karaoke captions from word timestamps + effects → `src/shorts-data.ts` |
| `scripts/verify_short.py` | Specs, integrated LUFS and true peak, and a 1 fps contact sheet per render |
| `assets/stream/StreamShort.tsx` | Layouts `stack` / `face` / `game` with animated switches, karaoke captions, hook, stickers, punch/shake/flash, freeze-frame outro, blur boxes |
| `references/plan.md` | The `shorts.json` format with every field. **Read before writing it.** |
| `references/moments.md` | What makes a stream moment work as a Short, and how to cut it |
| `references/risks.md` | Content ID (in-game music, song bots, videos watched on stream) and privacy (gamertags, chat, Discord, friends' voices) |

Python scripts that import numpy, whisper or OpenCV need the venv python from `yt-video-creator/scripts/setup_speech.sh` (`$VENV_PY`). The others run on system `python3`.

## Workflow

### 1. Ask (one round, or choose defaults and list them if you can't ask)
- How many Shorts, and for which platforms (YouTube Shorts, TikTok, Reels: the same 1080×1920 file works for all three).
- The channel name or handle, if they want it on the outro.
- Whether friends or guests consent to their voices and names being used, and whether other players' gamertags should be blurred. In the first run, the user wanted gamertags visible.
- Whether profanity and crude topics are fine, or should be bleeped.
- The caption language (default: the stream's language).

### 2. Scaffold and decode
```bash
bash <skill>/scripts/setup_stream.sh <vod> shorts-video
VENV_PY=$(bash <yt-video-creator>/scripts/setup_speech.sh)
cd <proj> && $VENV_PY <skill>/scripts/vod_audio.py source/vod.mp4 --project .
```
Read the probe line and the 10-minute energy arc: game segments, breaks, and muted or quiet stretches show up there.

### 3. Transcribe and rank (run in the background; do visuals meanwhile)
```bash
$VENV_PY <skill>/scripts/skim_vod.py lang --project .                   # all windows should agree
$VENV_PY <skill>/scripts/skim_vod.py skim --project . --language pt     # ~25x realtime on Apple Silicon
$VENV_PY <skill>/scripts/find_moments.py --project . --lang pt
```
Meanwhile, get the structure: one `sheets.py overview source/vod.mp4 -n 32 --width 240` sheet shows the whole VOD (which games, the facecam, non-game stretches such as a TV show or Discord). Run `$VENV_PY detect_cam.py source/vod.mp4 --project .` and **look at the check image** before pasting `cam` into `shorts.json`.

### 4. Choose the moments by reading
`find_moments.py` gives you a reading list, not the answer. Open the top ~30 windows with `skim_vod.py ctx --project . 1:05:00-1:07:30 ...` and read ±1–2 minutes around each. In the first run the best Shorts ranked mid-table:
- a storytime with a punchline;
- friends roasting the streamer;
- "I'm top of the scoreboard, so we're doomed".

Pick moments that are understandable **without context**, have a hook in the first 1–2 s and a payoff, and ideally end on a quotable line. `references/moments.md` has the patterns. Aim for 5–8 Shorts and keep 10+ runners-up for the report.

For each winner:
- use `sheets.py fine` on the range (small width) to confirm the visual payoff (death screen, round won or lost, the face reaction) and spot privacy problems;
- get word timestamps: `$VENV_PY <yt-video-creator>/scripts/transcribe.py words vod:<s>-<e> ... --project . --language pt` (source name `vod`, since `source/vod.mp4` exists).

### 5. Write shorts.json, build, check stills
Write `shorts.json` following `references/plan.md`:
- **cuts**: trim dead air, and start as close to the payoff as the hook allows;
- **layouts**: `stack` for gameplay, `face` for reactions and stories, `game` for pure plays; switch on the beat;
- **hl**: highlighted key words;
- **fix**: caption corrections (Whisper mishears slang, names and maps);
- **fx**: punch, shake, flash and sticker text on the beats;
- **hook** and **outro**: a punchline freeze card, not a generic "follow me".

```bash
npm run build:shorts                      # WARN lines: missing captions, fx outside cuts, length out of 15–60 s
node stills.mjs short-01 <scratch>/stills 0 45 200 ...
```
Look at the stills: the hook on frame 0, the caption position, blur boxes, and the layout switches.

Montages that jump across hours are fine. The builder makes one proxy per group of nearby cuts, never one spanning the gap (a 2.7-hour proxy happened once).

### 6. Render and verify
```bash
npm run render:shorts -- short-01 short-02 --note "first cut"    # versioned: out/versions/
python3 <skill>/scripts/verify_short.py out/short-0*.mp4 --project . --sheets <scratch>/verify
```
Look at every 1 fps sheet. Target −14 LUFS and a true peak ≤ −1 dBTP. If others are on camera, run the privacy face scan from yt-video-creator (`faces.py scan --edges`).

### 7. Report: out/SHORTS.md
For each Short:
- file, length, and source VOD timestamps;
- the hook and payoff (why it could perform);
- a title, a caption with 3–5 hashtags, and the best platform;
- risks: copyrighted audio heard in it, other people, profanity, context needed.

Then the ranked runners-up with timestamps. In the chat, summarize the set, say what the user should check before posting (anything with game or background music, anything with friends), and say which old versions are kept.

## Gotchas
- **Language**: detect once on 3 windows, then force it. Per-chunk auto-detection drifts on game audio and music.
- **Audio signals are a tiebreaker.** For a talkative streamer, loudness alone found none of the best moments, and a quiet or muted hour dominated raw "spikes" until the baseline was clamped to the global median.
- **Whisper mishears game slang and names** (Anubis → "Nubis", "stab" for TAB). Fix captions with `fix` by word or by source time, checked against what's on screen.
- **The facecam upscale is soft**: a ~550 px cam scaled to 1080 wide. It's acceptable, but keep `face` layout beats short and let the captions and effects carry them.
- **Frame 0 matters**: platforms often take the thumbnail from early frames, so the hook is full size on frame 0.
- **Captions** sit at the layout seam (below the facecam), never in the bottom ~25%, and keep 150 px from the right edge.
- Rendering takes ~2.5 min per 40-s Short (≈3.5× realtime), plus seconds per proxy. Check with stills before rendering all of them.
