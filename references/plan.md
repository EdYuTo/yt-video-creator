# plan.json

The edit's single source of truth. **All times are source times in seconds**: the numbers on
contact sheets and in transcripts. `build_edit.py --project <proj>` (or `npm run build`) turns it
into `src/edit-data.ts` (frames) and `edit-map.json` (what is where on the timeline).

## Top level

| key | meaning |
|---|---|
| `fps` | 30 |
| `clips` | `{id: {file, media: "link"\|"proxy", dur, audio, lrf?}}`, filled by setup_project.sh. `id` is the file stem |
| `language` | the transcription language (informational; transcribe.py takes `--language`) |
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
"ambient":  0,
"music":    {"file": "music.mp3", "mode": "auto", "volume": 0.15, "startSec": 0, "matchSong": false}
            // volume default: 0.7 for bed, 0.15 for broll
```

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
