# plan.json

The edit's single source of truth. **All times are source times in seconds**: the numbers on
contact sheets and in transcripts. `build_edit.py --project <proj>` (or `npm run build`) turns it
into `src/edit-data.ts` (frames) and `edit-map.json` (what is where on the timeline).

## Top level

| key | meaning |
|---|---|
| `fps` | 30 |
| `clips` | `{id: {file, media: "link"\|"proxy", dur, audio, lrf?}}`, filled by setup_project.sh. `id` is the file stem |
| `language` | the speech's language code (transcribe.py still takes `--language`; takes.py and export_srt.py default to this) |
| `words` | path of the word-timestamp JSON (`transcripts/words.json`) |
| `silence` | `{"pad": [0.2, 0.3], "gap": 0.75}`: pad each word before/after, merge islands closer than `gap` |
| `loudnorm` | proxies only: normalise each proxy to −18 LUFS so talk levels match across clips |
| `blur` | `[{clip, from, to, rects: [[x, y, w, h], ...]}]`: privacy boxes in % of the frame, applied to every shot overlapping `from`–`to` of that clip |
| `long` | the 16:9 video (omit or empty for none) |
| `short` | the 9:16 video (omit or empty for none) |

## Long-form items

```jsonc
// b-roll: `dur` is timeline seconds; source used = from .. from + dur*speed
{"clip": "MVI_0580", "from": 112, "dur": 2.5, "speed": 16,
 "chip": {"big": "240 g", "small": "chocolate"},   // optional top-right card
 "ambient": 0.3,     // optional source sound under 1x b-roll (sizzle); default long.ambient (0)
 "music": true,      // default true for b-roll
 "fit": "blur",      // letterbox over a blurred copy (square/vertical phone clips)
 "x": 45, "y": 50}   // crop focus %, rarely needed in 16:9

// talk: silence-cut from word timestamps into jump-cut shots with source audio (vol 1)
{"clip": "DJI_0021", "talk": [284.8, 300.0], "cut": true,
 "subs": [[285.1, 286.2, "Is this a little bell?"], [290.2, 291.9, "\"Push to call for service.\""]]}
// "cut": false keeps the window whole (music, a sizzle, a reaction with meaningful pauses)

// still photo with slow zoom
{"photo": "footage/photo12.jpg", "dur": 2.5}
```

Sections: `{"title", "sub", "step", "counter", "items": [...]}`. Every key except `items` is optional.
`counter`: `{"from": 0, "to": 22, "max": 25, "format": "min"|"int"|"dec1", "label": "200 °C"}`,
a ring that counts across the section.

Cards and the rest of `long`:

```jsonc
"intro":    {"kicker": "KOBE, JAPAN", "title": "A5 Kobe Beef\nYakiniku Night", "subtitle": "..."},
            // drawn over section 0: make its first item the hero shot/photo, ~4-7 s
"listCard": {"sec": 6.5, "title": "You'll need", "rows": [["320 g", "flour"]], "photo": "footage/x.jpg"},
            // placed right after section 0
"outro":    {"sec": 8, "photo": "...", "columns": [{"title": "Ingredients", "items": [...]},
                                                    {"title": "Method", "numbered": true, "items": [...]}]},
"credits":  {"sec": 9, "lines": [["Thanks for watching!", ""], ["Music", "\"Song\" — Artist (YouTube Audio Library)"]],
             "teaser": "Wait... bloopers"},   // [big line, ""] or [label, value]
"post":     [ ...items... ],                  // after credits: grayscale + "BLOOPERS" tag, own audio
"captions": "auto",                           // auto: top-left if the video has subtitles, else bottom-left
"burnSubs": true,                             // false: no subtitles in the picture; export them as caption tracks
"ambient":  0,
"music":    {"file": "music.mp3", "mode": "auto", "volume": 0.15, "startSec": 0, "matchSong": false}
            // volume default: 0.7 for bed, 0.15 for broll and duck
```

Music modes: `bed` (one track under everything), `broll` (only under b-roll/photos/cards, silent under
talk), `auto` (broll if there is talk, else bed), and `duck`: one continuous bed under everything that
dips to `duckVolume` (default 0.04) under talk instead of going silent. It plays `startSec`..`loopTo`, then
loops `loopFrom`..`loopTo` (defaults 0 and the song's end) for as long as the video runs; bounds must satisfy
`0 <= loopFrom < loopTo <= song length` and `startSec < loopTo` (build_edit stops with an error otherwise).
`{"mode": "duck", "volume": 0.14, "duckVolume": 0.035, "loopFrom": 0.52, "loopTo": 116.7}`.

Caption tracks instead of burned-in subtitles: set `"burnSubs": false`, build and render, then
`python3 <skill>/scripts/export_srt.py --project <proj> [--orig-lang pt]` → `out/captions.en.srt` (the plan's
subtitles on the final timeline) and `out/captions.<lang>.srt` (what was said: from `captions.<lang>.json` in
the project, one cleaned line per English cue in order, else straight from the word timestamps). `<lang>`
defaults to plan.json `language`. Upload them as YouTube caption tracks.

Order on the timeline: section 0 (with the intro) → listCard → sections 1..n → outro → credits → post.

## Short

```jsonc
"short": {
  "music": {"file": "music.mp3", "startSec": 27.7, "beat": 0.566, "offset": 0.05, "tail": 0.4, "volume": 0.85},
  "sections": [
    {"big": "Freezer cookies", "small": "bake one whenever you want",
     "items": [{"clip": "phone", "from": 7.5, "beats": 6, "fit": "blur"}]},      // the hook
    {"big": "225 g", "small": "butter", "items": [{"clip": "MVI_0576", "from": 45, "beats": 2, "speed": 3, "x": 47}]}
  ],
  "end": {"beats": 4, "photo": "footage/photo2.jpeg", "big": "Full recipe\nin the caption", "small": "save it for later"}
}
```
`beat` / `offset` / `startSec` come from `music.py`. The source used by an item is `from .. from + beats*beat*speed`.

## Thumbnail

```jsonc
"thumbnail": {
  "panels": [   // 1 panel = full bleed, 2 = diagonal split
    {"clip": "DJI_20250413133512_0021_D", "at": 1566.0, "cx": 0.42, "cy": 0.3, "zoom": 1.35},  // frame from the ORIGINAL
    {"photo": "footage/steak.jpeg", "cy": 0.62, "zoom": 1.12, "dx": 19}
  ],
  "title": "A5 KOBE\nBEEF",      // <= 4 words, huge, outlined
  "badge": "¥40,000 dinner",      // optional hook, top-right
  "kicker": "KOBE, JAPAN"         // optional small line above the title
}
```
`cx`/`cy` = focus point (0–1) that `zoom` scales around; `dx`/`dy` shift the image in % of the canvas
(positive = right/down). With two panels, the left panel shows canvas x 0–~52% and the right one ~52–100%,
so a subject centered in its photo needs `dx` ≈ +20 on the right panel. Render with
`npm run render:thumb` → `out/thumbnail.jpg` (1280×720, well under YouTube's 2 MB limit).

## Example A: music-driven process video (cookies, abridged)

```json
{
  "long": {
    "intro": {"kicker": "MAKE-AHEAD", "title": "Chocolate\nChunk Cookies", "subtitle": "Freeze the dough, bake whenever you want"},
    "listCard": {"sec": 6.5, "title": "You'll need", "rows": [["320 g", "white flour"], ["225 g", "butter"]], "photo": "footage/photo2.jpeg"},
    "sections": [
      {"items": [{"photo": "footage/photo1.jpeg", "dur": 4}]},
      {"title": "Weigh everything first", "items": [
        {"clip": "MVI_0576", "from": 34, "dur": 2.4, "speed": 6, "chip": {"big": "225 g", "small": "butter"}}]},
      {"step": 2, "title": "Chop the chocolate", "sub": "240 g, into chunks", "items": [
        {"clip": "MVI_0580", "from": 112, "dur": 2.5, "speed": 16}]},
      {"step": 10, "title": "Bake at 200 °C", "sub": "20–25 minutes",
       "counter": {"from": 0, "to": 22, "max": 25, "format": "min", "label": "200 °C"}, "items": [
        {"clip": "MVI_0592", "from": 30, "dur": 3, "speed": 25}]}
    ],
    "outro": {"sec": 7, "columns": [{"title": "Ingredients", "items": ["320 g white flour"]}, {"title": "Method", "numbered": true, "items": ["Melt the butter."]}]},
    "music": {"mode": "bed", "volume": 0.7, "matchSong": true}
  }
}
```

## Example B: talk / food vlog (Kobe, abridged)

```json
{
  "silence": {"pad": [0.2, 0.3], "gap": 0.75},
  "blur": [{"clip": "DJI_20250413142648_0023_D", "from": 271, "to": 289, "rects": [[78, 8, 22, 40]]}],
  "long": {
    "intro": {"kicker": "KOBE, JAPAN", "title": "A5 Kobe Beef\nYakiniku Night", "subtitle": "Two hours, a dozen courses and my broken Japanese"},
    "sections": [
      {"items": [{"clip": "DJI_20250413141512_0022_D", "from": 124, "dur": 6.5}]},
      {"title": "The private room", "sub": "Yakiniku in Kobe, Japan", "items": [
        {"clip": "DJI_20250413133512_0021_D", "from": 196, "dur": 4, "speed": 3},
        {"clip": "DJI_20250413133512_0021_D", "talk": [284.8, 300.0], "subs": [
          [285.1, 286.2, "Is this a little bell?"], [290.2, 291.9, "\"Push to call for service.\""]]}]},
      {"title": "On the grill", "items": [
        {"clip": "DJI_20250413133512_0021_D", "from": 1418, "dur": 5, "speed": 6, "ambient": 0.3},
        {"photo": "footage/photo11.jpg", "dur": 2.5},
        {"clip": "DJI_20250413133512_0021_D", "talk": [1552.3, 1575.8], "subs": [[1561.4, 1565.0, "Wow, it melts in your mouth."]]}]}
    ],
    "credits": {"sec": 9, "lines": [["Thanks for watching!", ""], ["Filmed at", "a yakiniku restaurant in Kobe, Japan"]], "teaser": "Wait... bloopers"},
    "post": [{"clip": "DJI_20250413142648_0023_D", "talk": [2192, 2243], "subs": [[2193.0, 2195.5, "How do I ask for this?"]]}],
    "music": {"mode": "broll", "volume": 0.14}
  }
}
```

## Reels (1080x1920 talking head)

`Short` is beat-synced b-roll with no dialogue. For vertical video where what's *said* matters
(talking to camera, screen recordings with commentary), use `reels`: a list of independent vertical
videos, each with its own hook card, end card, music and annotations, registered as compositions
`Reel1`, `Reel2`, ... Items use the same grammar as `long.sections[].items`, plus the keys below.

```jsonc
"proxyBox": [3024, 1964],       // keep native resolution: reels zoom into screen recordings
"proxyEncoder": "x264",         // h264_videotoolbox corrupts fast-scrolling screen content
"reels": [{
  "id": "Reel1", "slug": "three-steps", "title": "Three steps",
  "hook": {"sec": 2.6, "big": "Three\nsteps", "small": "in order"},
  "end":  {"sec": 4.0, "big": "Save this", "small": "which one is hardest?",
           "items": ["Plan", "Build", "Ship"]},                   // numbered recap
  "music": {"file": "music.mp3", "mode": "duck", "volume": 0.14, "duckVolume": 0.035,
            "loopFrom": 0.52, "loopTo": 116.7},                   // null = no music at all
  "items": [
    // v1, the speaker's own picture: board layout + framing
    {"clip": "<id>", "talk": [127.3, 135.2], "trans": "zoom", "box": 36, "x": 4, "y": 42, "zoom": 1.15,
     "subs": [[127.3, 131.4, "Subtitle"]],
     "anns": [{"at": [127.8, 135.2], "kind": "label", "x": 6, "y": 5, "text": "1 · PLAN"}]},
    // v2, a demo picture under the voice + the speaker as a head bubble
    {"clip": "voice-r1", "talk": [2.8, 5.4], "subs": [...], "anns": [...],
     "demo": {"clip": "demo-r1-page", "from": 2.84},              // or {"card": true}, see below
     "head": {"clip": "bubble-r1", "pos": "bl"}}
  ]
}]
```

| key | meaning |
|---|---|
| `trans` | entry transition: `"cut"` (default), `"fade"`, `"whip"` (horizontal smear), `"zoom"` (punch in). In-place, so cut speech stays in sync |
| `box` | **board layout**: the picture fills the band from this % down; the space above is a themed panel to draw on |
| `zoom` | extra scale past `cover`, anchored at `x`/`y`: crops past webcam letterbox bars, makes screen text readable (only ~36% of a 16:9 frame's width survives 9:16) |
| `demo` | the picture under this line, muted (the voice plays as audio only). `{"clip", "from", "speed"?, "x"?, "y"?, "zoom"?}` = a video framed like a shot; `{"clip", "from", "rect": [x0, y0, x1, y1], "rectTo"?, "cy"?}` = a crop of the source (fractions) scaled to the full width with its centre at `cy` (0.42) of the height, gliding to `rectTo` over the line; `{"card": true}` = the theme gradient (card-only lines). The demo runs on across the line's silence cuts; one that runs out holds its last frame (WARN) |
| `head` | `{"clip": "bubble-<reel>", "pos": "bl" \| "tl" \| "big"}`: the speaker's bubble (bottom-left, top-left, big centre); it glides from the previous line's position |

`anns` are anchored to **source time** (`"at": [s, e]`), like `subs`, so silence cutting can't desync
them. Positions are % of the 1080x1920 frame. Block annotations draw on a dark card, because they often
land on white pages. Any ann takes `size` (default 1; 0.5–3) to scale its text/card from its anchor
(ring/arrow: the stroke) — e.g. big centred notes on `card` lines.

| kind | fields | drawn as |
|---|---|---|
| `label` | `text` | solid accent pill |
| `note` | `text`, `w`, `rotate` | handwriting + a marker underline that wipes in |
| `list` | `items` (`*` prefix = highlighted), `w` | rows ticked off one at a time with a drawn check |
| `bar` | `bars: [[label, 0-1], ...]`, `w` | labelled proportion bars (e.g. a time budget) |
| `ring` | `x`, `y`, `w` | an ellipse drawn around a point on screen |
| `arrow` | `x`, `y`, `to: [x, y]` | a curved arrow drawn from one point to another |

A `list` that starts ≤ 3 frames after the previous `list` ends, with the same rows (only the `*` moved,
or one list split by silence cuts), is a continuation: build_edit marks it `noIntro` (drawn complete
from its first frame) and the one before `noOutro` (no fade-out), so the card doesn't flash empty.

Framing: don't guess `x`/`y`/`zoom`. Grab the frame at each shot's source time, overlay a percentage
grid, read the target rectangle off it, then solve (`visible_w = (a_out / a_src) / zoom`, `visible_h =
1 / zoom`, `x = (cx - vw/2) / (1 - vw) * 100`). Screen recordings scroll: measure per shot.

Render with `node render.mjs Reel1 out/reel1-<slug>.mp4` (also `stills.mjs`). Environment, only when
needed: `REMOTION_PORT=<port>` when another local server holds Remotion's default port (renders 404 or
hang on "Waiting for root component to load"); `REMOTION_BROWSER=<path>` to use a specific Chrome /
chrome-headless-shell when the one Remotion downloads hangs.

### Scripted reels: script → teleprompter → takes → plan

Instead of cutting existing footage, write the reels first and record them line by line. `<T>` is
this toolkit, `<P>` the project.

1. **Script** `<P>/scripts/reels.json`:
   `{"wpm": 140, "rules": {...}, "reels": [{"id": "r1", "slug", "title", "caption"?, "hook": {big, small},
   "end": {big, small, items?}, "music"?, "lines": [{"text", "demo": "card" | "<beat id>", "head"?,
   "confirm"?, "anns": [{kind, x, y, ..., "in": 0.1, "out": 1.0, "size"?}]}]}]}`. Ann `in`/`out` are
   fractions of the line's take (not `at`). Ids name files (`voice-r1`, `takes/r1.json`).
   `python3 <T>/scripts/check_scripts.py <P>/scripts/reels.json` checks shape and layout (anns clear of
   the head bubble, the subtitle band, the platform's right-hand buttons and each other); content rules are opt-in via
   `"rules": {"noPrices": false, "banned": [regex...], "maxWords": 22, "durationRange": [20, 90]}`.
   `export_scripts.py <P>` writes `<P>/SCRIPTS.md` to review.
2. **Record**: `node <T>/teleprompter/server.mjs --project <P> [--port 3918]`, open the URL, pick the reel,
   Record. Karaoke at the chosen speed; tap/click = restart the line (in its first second: back one line); Esc or
   Stop ends. Writes `<P>/recordings/raw/<reel>-<take>.webm` + `.log.json`.
3. **Import**: `import_take.py <P> <raw.webm> --id voice-r1` (1080p CFR mp4, loudness-normalised, `link`
   clip, log copied for takes.py). Then `transcribe.py words voice-r1:0-<dur> --project <P> --language <lang>`.
4. **Takes**: `takes.py <P> --reel r1` picks the last clean take of each line → `<P>/takes/r1.json`
   (start/end/score/subs). It re-transcribes each take with Whisper prompted with `<P>/scripts/terms.txt`
   (one term per line) + the line (`--language`, else plan.json `language`; `--no-hint` skips it).
5. **Head bubble** (macOS): `bubble.py --cam <P>/recordings/voice/voice-r1.mp4 --matte <P>/recordings/voice/voice-r1.matte.mp4
   --crop X,Y,W --d 640 [--bg-top '#C8A2E8' --bg-bottom '#EBDDF7'] --out <P>/recordings/voice/bubble-r1.webm`.
6. **Demos**, keyed by the lines' `demo` ids in `<P>/demos/manifest.json`: `{"<beat>": {"type": "web"}}`
   (a recorded page, clip `demo-<beat>`), `{"type": "video", "clip", "from", "speed"?, "x"?, "y"?, "zoom"?}`,
   `{"type": "crop", "clip", "from", "rect", "rectTo"?, "cy"?}` or `{"type": "card"}`. Web beats:
   `export default {"<beat>": {url, async run(page, h) {...}}}` in a beats file, with `h.pause(ms)`,
   `h.scrollTo(sel, ms, container?)`, `h.type(sel, text)`, `h.click(sel)`, `h.hide([sel])`, then
   `node <T>/scripts/demo_rec.mjs record --id <beat> --beats <file> [--project <P>] [--seconds N]` →
   1080x1920 CFR 30 `<P>/recordings/demos/<beat>.mp4`, registered in plan.json. The project (for
   Playwright and ffmpeg) is `--project`, else `$DEMO_REC_PROJECT`, else the current directory. Setup there:
   `npm i -D playwright highlight.js`; `--channel chromium`, `verify_viewer.mjs` and the tests also need
   `npx playwright install chromium` (npm doesn't download the browser); the default channel uses installed Chrome. For logged-in
   sites run `demo_rec.mjs login --urls <a,b>` once and sign in by hand (real Chrome, profile
   `~/.cache/yt-video-creator/browser-profile-chrome`; never automated), then quit that Chrome (⌘Q / Chrome → Quit;
   on macOS closing its window leaves it running and holding the profile).
   Code pages: `node <T>/assets/code-viewer/build_viewer.mjs <file> <P>/demos/<name>.html [--lang swift]
   [--title Name]` (highlight.js from the project: `npm i -D highlight.js`) writes an offline, phone-width,
   highlighted page with `#L<n>` lines and `window.mark(from, to)` / `unmark()` / `scrollToLine(n, smooth)`
   for beats; `verify_viewer.mjs <page.html> [shot.png]` checks it fits 432 px.
7. **Assemble**: `assemble_reels.py <P> [--reels r1,r2]` writes plan.json `reels` (the reel at index i of
   reels.json, whatever its id, becomes `Reel<i+1>` and records `"script": "<id>"`; other plan keys kept):
   one talk item per line with a take, demo `from` carried across
   consecutive lines on the same beat, and the minimum length to record for each web beat. Reels not in
   `--reels`, or with no takes yet (WARN), keep their current plan.json entry, found by `script` id (else by
   slug, which check_scripts keeps unique), so reordering reels.json is safe. Then `npm run build`.

Tests (`python -m unittest discover -s tests`, `node --test teleprompter/ assets/template/tests/ tests/*.test.mjs`)
skip what needs media unless `YVC_TEST_PROJECT` / `DEMO_REC_PROJECT` point at a project with node_modules and
`YVC_TEST_FOOTAGE` (+ `YVC_TEST_FOOTAGE_AT`) at a video of a person talking to the camera.
