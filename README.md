# yt-video-creator

A [Claude Code](https://claude.com/claude-code) skill that turns a folder of raw footage (camera clips, phone videos, DJI files, photos) into a finished YouTube video with [Remotion](https://github.com/remotion-dev/remotion). It produces a **16:9 long-form video**, a **9:16 Short** (the same file works for TikTok and Reels), or both.

It handles two kinds of video:

- **Music-driven process videos** (recipes, builds, DIY): sped-up b-roll, step captions, quantity chips, timers, a recipe/summary outro, and music under the whole thing.
- **Talk videos** (food vlogs, travel, interviews): local transcription, conversations chosen from the transcript, silences cut from word timings, subtitles, music only under b-roll and silent under speech, credits, black-and-white bloopers after the credits, and privacy blur for bystanders.

## Examples

### Music-driven: a cookie recipe

Both were cut from ~70 minutes of raw overhead kitchen footage, a phone clip and five photos:

| Long-form (1:59) | Short (0:44) |
|---|---|
| [![Long-form](https://img.youtube.com/vi/A-A4ukkqs0s/hqdefault.jpg)](https://www.youtube.com/watch?v=A-A4ukkqs0s) | [![Short](https://img.youtube.com/vi/awqqZKaa6hw/hqdefault.jpg)](https://www.youtube.com/shorts/awqqZKaa6hw) |

The whole edit for both is one file: [`examples/cookie/plan.json`](examples/cookie/plan.json).

### Talk-driven: a food vlog in Kobe, Japan

[![A5 Kobe Beef / Yakiniku Night](https://img.youtube.com/vi/eA6XAgD2w9o/hqdefault.jpg)](https://www.youtube.com/watch?v=eA6XAgD2w9o)

A 7:12 video cut from a 93-minute restaurant dinner: four DJI clips (40 GB of 2.7K 10-bit HEVC), mostly conversation in Portuguese, plus the Japanese staff and a chef. The skill:
- transcribed everything locally, forcing the language, and picked the conversations worth keeping;
- cut the silences using the word timings and added English subtitles;
- kept the music low and only in between the talking;
- blurred the face of a friend who hadn't agreed to be on camera;
- added credits, then the creator's broken Japanese after them as black-and-white bloopers;
- made the thumbnail.

The first complete version took about 1 hour and ~212k tokens with Claude Opus 5.5. Follow-ups brought the total to under 2 hours and ~280k tokens: extra face blurring, and a thumbnail redo to show the higher-grade steak.

## Install

```bash
git clone https://github.com/EdYuTo/yt-video-creator ~/.claude/skills/yt-video-creator
```

Requirements: Node.js 18+ and Python 3 with Pillow (`pip install pillow`). You don't need a system ffmpeg: the scripts use the one bundled with Remotion. For talk videos and the privacy check, `scripts/setup_speech.sh` creates a private venv in `~/.cache/yt-video-creator` with a local Whisper (mlx-whisper on Apple Silicon, faster-whisper elsewhere) and OpenCV. Audio never leaves your machine.

## Usage

In Claude Code, from a folder of raw clips:

> edit a youtube video from the footage in this folder, it's a recipe for ...

> make a foodie video for youtube from ~/Videos/kobe, cut the silences and boring talk, music low in the background, bloopers after the credits

The skill asks for the format, length, language, music, whether talk matters and how to handle other people on camera. Then:

1. **Scaffold**: a Remotion project inside the footage folder links the originals, probes them (codec, bit depth, fps) and decides per clip whether to use it directly or make proxies of only the used ranges (10-bit HEVC, 4K, 60p).
2. **See and hear**: timestamped contact sheets show Claude the footage; local transcripts give it the conversations.
3. **Plan**: the edit is written as `plan.json` in source time. `build_edit.py` does all the frame math: silence-cutting dialogue from word timestamps, placing subtitles, music runs and beat-synced cuts for Shorts, and writing proxies.
4. **Render and verify**: stills per section, a full render (`render.mjs` versions every output and symlinks `public/` instead of copying tens of GB), then a frame-by-frame sheet of the output, per-segment audio levels, and a face scan (including an edge pass for people half out of frame) for anyone who should be blurred.

To change the result, edit `plan.json`, then run `npm run build` and `npm run render:long` (or `render:short`, `render:thumb`), or preview with `npm run studio`. Renders never overwrite each other: the previous output moves to `out/versions/` with the plan that produced it, and each render is logged (add `-- --note "what changed"`).

## Layout

```
SKILL.md                  workflow + gotchas (what Claude reads)
references/
  plan.md                 plan.json format with a music-driven and a talk example
  talk.md                 dialogue workflow: transcription pitfalls, picking conversations, subtitles, ducking
  formats.md              YouTube / Shorts specs, safe zones, pacing, music licensing, privacy
scripts/
  setup_project.sh        scaffold project, link originals, probe, plan.json skeleton
  probe.py                media table + link/proxy recommendation
  sheets.py               contact sheets: per-clip overview, multi-range fine sheets, output checks
  setup_speech.sh         private venv: whisper + OpenCV + YuNet face model
  transcribe.py           skim whole clips (small model) / word timestamps for windows (turbo)
  music.py                loudness map, breaks -> onsets, BPM + beat phase
  build_edit.py           plan.json -> proxies + src/edit-data.ts + edit-map.json
  speech_map.py           loudness-based speech islands (quiet footage only)
  faces.py                face scan of a render mapped to shots + review sheet
  audio_levels.py         per-segment loudness of a render
assets/template/          Remotion project: LongForm (1920x1080) + Short (1080x1920), render.mjs, stills.mjs
examples/cookie/          plan.json behind the example videos
stream-highlights/        companion skill: stream VOD -> set of Shorts
```

## stream-highlights (companion skill)

[`stream-highlights/`](stream-highlights/) mines a long stream recording (a Twitch or YouTube VOD, hours long) for its most engaging moments and cuts a **set** of vertical Shorts. It decodes the audio once, transcribes the whole VOD locally, ranks 30-second windows by what's said and how loud it is, detects the facecam, and renders each moment with facecam and gameplay layouts, word-synced karaoke captions, hook titles, punch-in/shake/sticker effects and freeze-frame punchlines. It also writes a report with titles, captions, hashtags and risks per clip. It reuses this skill's scripts and template.

Install it next to this one:

```bash
ln -s ~/.claude/skills/yt-video-creator/stream-highlights ~/.claude/skills/stream-highlights
```

> make shorts from my twitch vod in ~/Videos/vod, find the moments that could go viral

## Music

Use tracks you own or that are free for YouTube, such as the [YouTube Audio Library](https://www.youtube.com/audiolibrary). The skill won't download audio from YouTube links: it looks up the title and asks you to download the track from its source.
