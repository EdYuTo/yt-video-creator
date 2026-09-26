# yt-video-creator

A [Claude Code](https://claude.com/claude-code) skill that turns a folder of raw footage (camera clips, phone videos, photos) into a finished YouTube video with [Remotion](https://github.com/remotion-dev/remotion). It can produce a **16:9 long-form video**, a **9:16 Short** (the same file works for TikTok and Reels), or both.

## Examples

Both were cut from ~70 minutes of raw overhead kitchen footage, a phone clip and five photos:

| Long-form (1:59) | Short (0:44) |
|---|---|
| [![Long-form](https://img.youtube.com/vi/A-A4ukkqs0s/hqdefault.jpg)](https://www.youtube.com/watch?v=A-A4ukkqs0s) | [![Short](https://img.youtube.com/vi/awqqZKaa6hw/hqdefault.jpg)](https://www.youtube.com/shorts/awqqZKaa6hw) |

The edit data for both lives in [`examples/cookie/`](examples/cookie/).

## Install

```bash
git clone https://github.com/EdYuTo/yt-video-creator ~/.claude/skills/yt-video-creator
```

Requirements: Node.js 18+, Python 3 with Pillow (`pip install pillow`). You don't need a system ffmpeg: the scripts use the one bundled with Remotion.

## Usage

In Claude Code, from a folder of raw clips:

> edit a youtube video from the footage in this folder, it's a recipe for ...

The skill asks for the format (long-form / Short / both), length, text language, music and any story details. Then it:

1. Creates a Remotion project inside the footage folder and hard-links the clips (no extra disk space).
2. Builds timestamped contact sheets of every clip, so Claude can see the footage and pick exact in/out points.
3. Analyzes the music (breaks, onsets, BPM and beat phase). The long-form video ends with the song; a Short starts on a hard downbeat and cuts on beats.
4. Writes the edit as plain data (`src/long-edit.ts`, `src/short-edit.ts`), checks sample stills, renders, then checks the output frame by frame.

Tweak the result by editing those data files and running `npm run studio` or `npm run render:long` / `npm run render:short`.

## Layout

```
SKILL.md                 workflow + gotchas (what Claude reads)
references/formats.md    YouTube / Shorts specs, safe zones, pacing, music licensing
scripts/
  setup_project.sh       scaffold project, link media into public/
  probe.py               list media with duration / resolution / fps
  sheets.py              contact sheets: per-clip overview, fine time ranges, output checks
  music.py               loudness map, breaks -> onsets, BPM + beat phase
  stills.mjs             render sample frames with a single bundle
assets/template/         Remotion project: LongForm (1920x1080) + Short (1080x1920)
examples/cookie/         the edit behind the example videos
```

## Music

Use tracks you own or that are free for YouTube, such as the [YouTube Audio Library](https://studio.youtube.com/channel/UC/music). The skill won't download audio from YouTube links: it looks up the title and asks you to download the track from its source.
