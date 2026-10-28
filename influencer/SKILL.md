---
name: influencer
description: Make scripted talking-head reels (Instagram Reels, TikTok, YouTube Shorts) on any topic — research and fact-check the claims, write the script in the creator's own voice, run a karaoke teleprompter that records their camera and voice, cut the clean take of every line, float the creator over screen demos as a Presenter-Overlay-style head bubble, record the website/app/code demos at 9:16 with browser automation, and render 1080×1920 videos with subtitles and drawn annotations. Use this whenever someone wants to create reels, a reel series, an explainer, a tutorial or "influencer" content where they talk to camera over a screen demo — even if they only say "make some reels about X", "help me post about X", or "write me a script and record it".
---

# Influencer reels

You help a creator make short vertical talking-head videos on any topic. You can't watch or listen, so
you work through proxies: transcripts with word timings for what was said, contact sheets and stills for
what's on screen. Each reel goes through four stages:

1. **Script.** You research the topic, fact-check it, and write the reel in the creator's voice.
2. **Record.** The creator reads it on a karaoke teleprompter that records camera and mic together.
3. **Demos.** Once the voice exists, you record the screen demos at 9:16, timed to each spoken line.
4. **Composite.** The demo fills the frame, the creator floats over it as a head bubble, and subtitles
   and drawn annotations go on top.

**Voice first, demos after.** Demos are timed to how the creator actually read each line, so never record
demos before the voice is cut.

All tooling lives in the parent `yt-video-creator` repo. Resolve it once:

```bash
R="$(cd "<skill>" && pwd -P)/.."        # <skill> = this skill's base directory (it may be a symlink)
VPY=~/.cache/yt-video-creator/venv/bin/python   # created by $R/scripts/setup_speech.sh
```

| piece | what it does |
|---|---|
| `$R/scripts/setup_project.sh <dir> <name>` | Scaffolds the Remotion project (works with an empty `<dir>`) |
| `$R/scripts/check_scripts.py`, `export_scripts.py` | Validate `scripts/reels.json`; export a readable script for the creator |
| `$R/teleprompter/server.mjs` | Karaoke teleprompter + camera/mic recorder on localhost |
| `$R/scripts/import_take.py`, `transcribe.py words`, `takes.py` | Import a take, get word timings, pick the clean take of each line |
| `$R/scripts/bubble.py` (+ `segment_person.swift`) | Local person cut-out → head bubble video with alpha |
| `$R/scripts/demo_rec.mjs` (+ `demo_helpers.mjs`) | Logged-in Chrome driven by Playwright, recorded at 1080×1920 |
| `$R/assets/code-viewer/build_viewer.mjs` | Any source file as a phone-width, highlightable code page |
| `$R/scripts/assemble_reels.py`, `build_edit.py` | Scripts + takes + demos → `plan.json` reels → Remotion data |
| `$R/references/plan.md` ("Reels") | The exact `plan.json` / `reels.json` fields |

Read these references when you reach their step: [references/scripts.md](references/scripts.md) (writing),
[references/recording.md](references/recording.md) (the session),
[references/demos.md](references/demos.md) (screen demos).

## 1. Ask (one round)

Skip anything the creator already said. If you can't ask, choose defaults and list them.
- **Topic and angle.** What it's about, who it's for, and what the viewer should walk away able to do.
- **Series shape.** One reel or a series. A series usually opens with an overview reel that the others
  point back to.
- **Their voice.** Ask for something that sounds like them: a voice memo, an old video or transcript,
  messages they wrote, or a rambling first take. This is the single biggest input to an organic script.
- **Sources** they trust, and claims they want made or avoided.
- **Languages** for the voice and the subtitles. They can differ: subtitles default to the spoken language, and you translate them
  yourself afterwards (step 6).
- **What's on screen.** Websites (and whether they need to be logged in), apps, code, old recordings, or
  nothing (drawn cards).
- **Music.** Default is none for talking reels; ask.
- **Personal details on screen** (emails, handles, avatars): show them or hide them.

## 2. Research and fact-check

Search the web for every factual claim the reel will make. Keep a table with the claim, the source URL,
and what the script may say: holds as-is, needs softening ("some companies", "usually"), or can't be
stated. Things that change often (prices, product limits) are named but not quoted, unless the creator
insists and you can cite today's official page. Anything the creator remembers but you can't source goes
back to them as a question, not into the script.

## 3. Write the scripts (organic, then checked)

Follow [references/scripts.md](references/scripts.md). In short: write the way *they* talk, not the way an
article reads. Use their phrases, their slang, first person, short spoken sentences, and a hook that sounds
like them. Keep their stories when they want them. Facts still come only from the table.

Store the scripts as data in `scripts/reels.json`. Each reel has a hook card, an end card and lines; each
line has the text, the demo beat it illustrates, the head position and its annotations. Then:

```bash
python3 $R/scripts/check_scripts.py <proj>/scripts/reels.json     # silent = valid
python3 $R/scripts/export_scripts.py <proj>                        # -> SCRIPTS.md, the readable script
```

**The creator reads the whole thing out loud before anything is recorded.** Read-aloud catches what reading
on screen doesn't. Iterate until they say it sounds like them. Don't add a spoken "save this reel" sign-off
to every reel unless they want one; it gets repetitive fast. The end card can carry that.

## 4. Scaffold

```bash
mkdir -p <dir> && bash $R/scripts/setup_project.sh <dir> <name>-reels
cd <dir>/<name>-reels && npm i -D playwright highlight.js && npx playwright install chromium
```

Demos record in the creator's installed **Google Chrome**. Playwright's own Chromium is only for the code-page check and the tests.

**Platform:** macOS. The head bubble uses Apple Vision (Swift), `demo_rec.mjs login` opens Chrome with `open`, and the hinted
re-transcription uses mlx-whisper (Apple Silicon). Elsewhere the hint pass is skipped with a WARN (plain Whisper words), and the
bubble and login steps need a replacement.

In `plan.json` set `"language"` (the voice language, which drives transcription), `"proxyEncoder": "x264"`,
and `"proxyBox"` at native resolution if you'll crop old screen recordings. Reels use `"music": null` unless
asked.

## 5. Record the voice

Follow [references/recording.md](references/recording.md). Run
`node $R/teleprompter/server.mjs --project <proj>` and have the creator open `http://localhost:3918`, pick
camera and mic, and set the speed (110–260 wpm). They press Record and read. A tap on the screen restarts
the current line; a tap in its first second goes back one line. Stop ends the take.

**Have them record one reel, then check it before they do the rest.** Check framing (headroom for the hair
to pop over the bubble), audio level, the eye line, and one bubble preview. Fixing setup after nine reels is
expensive.

## 6. Cut the voice

```bash
$VPY $R/scripts/import_take.py <proj> <proj>/recordings/raw/<reel>-<take>.webm --id voice-<reel>
$VPY $R/scripts/transcribe.py words voice-<reel>:0-<dur> --project <proj> --language <lang>   # one clip per call
$VPY $R/scripts/takes.py <proj> --reel <reel>
```

Use each reel's latest **complete** take; creators often restart instead of tapping. `takes.py` re-transcribes
each line with the line and `scripts/terms.txt` as a hint, so English terms in another language come out
right. It prints a WARN per weak line. Check each WARN:
- **Misheard** (the hint pass recovers the words): nothing to do.
- **Ad-lib with the same meaning:** keep it. The subtitle follows what they said; fix the window by hand in
  `takes/<reel>.json` if the cut clipped it.
- **Misread a fact or didn't finish:** ask for a re-read of that reel, or drop the line (delete it from
  `takes/<reel>.json`; assembly skips lines without a take).

**Subtitles in another language:** after the takes are final, translate the text of each `subs` entry in `takes/<reel>.json` in
place (keep the timings, keep entries short and natural rather than literal).

Re-running `takes.py` regenerates `takes/*.json`, so re-apply any hand edits (dropped lines, ad-lib windows, translations)
afterwards and note them in EDIT-NOTES.

## 7. Head bubble

```bash
$VPY $R/scripts/bubble.py --cam <proj>/recordings/voice/voice-<reel>.mp4 \
  --matte <proj>/recordings/voice/voice-<reel>.matte.mp4 --crop X,Y,W --d 640 \
  --out <proj>/recordings/voice/bubble-<reel>.webm
```

Pick the crop from a gridded still: `W` ≈ 1.5× face width, and the circle (the bottom `W×W` of the
`W × 1.3W` crop) centred on the mouth, with the hair above the rim. If the creator didn't move, one crop
fits every reel of the session. The cut-out runs locally (Apple Vision) and takes about 6 + 6 min per
minute of voice, so queue all reels in one background job, sequentially.

## 8. Demos

Follow [references/demos.md](references/demos.md). One beat per `demo` id in the scripts, timed to the take
durations. `assemble_reels.py` prints how long each run of lines needs. Types: `web` (Playwright on real,
logged-in Chrome), `video`/`crop` (existing footage, cropped and pushed in), `card` (no picture; the
annotations carry it, so make them big with `size`).

## 9. Assemble, check, render

```bash
python3 $R/scripts/assemble_reels.py <proj> [--reels r0,r1]
cd <proj> && npm run build && npm run typecheck
node stills.mjs Reel1 /tmp/stills <frames…>          # one per shot start (edit-map.json seconds × 30)
npm run render:reel1 -- --note "what changed"        # add "render:reelN" scripts per reel
```

Fix every WARN from the build. A demo shorter than its run is the common one: re-record the beat longer.
Look at the stills for annotations under the bubble or the subtitles, text unreadable at phone size, and
empty frames. Render a **pilot of one or two reels** and get the creator's reaction before doing the rest.

Verify each render with a contact sheet (`$R/scripts/sheets.py fine out/<f>.mp4 0-<dur>:2 --out /tmp/sheets --project .`),
the levels (speech ≈ −20 dBFS, peak under −1), and ffprobe (1080×1920, 30 fps, h264 + aac).

## 10. Deliver

Report the files, durations, anything dropped or ad-libbed, and what to double-check. Write a caption per
reel (hook line, value, call to action, the sources list if the creator wants it). Never post or upload
anything without explicit permission for that specific post.

## Gotchas (all hit in practice)

- **Google blocks sign-in inside automated Chromium.** The creator logs in through real Chrome on the
  dedicated profile (`demo_rec.mjs login`), quits it, and only then do you record. A running Chrome on that
  profile locks it, and `record` fails fast.
- **Never type credentials** from automation, and never hide or blur the creator's details unless they ask.
- **`h264_videotoolbox` corrupts fast-scrolling screen content.** Keep `"proxyEncoder": "x264"`.
- **Whisper mishears English terms in other languages** ("reel" became "rio"). Put terms in
  `scripts/terms.txt`; the hinted pass in `takes.py` handles the rest.
- **Re-recording a reel:** `import_take.py` drops the old transcript windows for that clip. Re-run
  `transcribe.py` and `takes.py` for it.
- **Batch `transcribe.py words` with many clips can silently write nothing.** Run one clip per call.
- **Karaoke pace:** creators read faster than they expect. The pauses scale with the speed, so let them
  push it to 200–220 wpm.
- **macOS Presenter Overlay doesn't appear.** It's only offered while an app shares the screen with the
  camera. You build the look afterwards. Virtual backgrounds are fine for the cut-out; Portrait blur is not.
- **Card-only reels look empty.** Centre the annotations and scale them up (`size` 1.6–2.2), and use the
  `big` head position more.
- **Consecutive lines sharing a demo id continue the clip** instead of restarting it. A beat recorded once
  serves every run of that id, from its manifest `from`.
