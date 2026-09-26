# shorts.json

All times are **VOD source seconds** (read them off `vod_skim.txt`, `moments.md`, sheets and
`words.json`). `build_shorts.py` maps them onto each Short's timeline.

```jsonc
{
  "src": "vod.mp4",                    // under source/ (setup_stream.sh creates the alias)
  "fps": 30,
  "cam": [2014, 0, 546, 448],          // facecam overlay box, source px (detect_cam.py, then LOOK)
  "camBlur": [],                       // boxes inside the cam to blur (overlays, alerts), source px
  "gameBlur": [],                      // boxes blurred in every game panel (e.g. a chat box), source px
  "loudnorm": "I=-14:TP=-1.5:LRA=11",  // per-proxy normalisation; Shorts platforms sit near -14 LUFS
  "words": "transcripts/words.json",   // from transcribe.py words vod:<s>-<e>
  "shorts": [{
    "id": "short-01",                  // composition id and output name (out/short-01.mp4)
    "tag": "CS2",                      // small top-left label after the hook (game, STORYTIME, LIVE)
    "hook": {"text": "LINE ONE\nLINE TWO", "sub": "small pill line", "sec": 2.2},
    "cuts": [                          // in order; each becomes a segment
      {"s": 1575.0, "e": 1583.5, "layout": "stack", "gameX": 0.5},
      {"s": 1601.0, "e": 1609.5, "layout": "face",
       "blurGame": true,               // blur the whole game panel (menus, Steam, Discord, lobby)
       "blur": [[40, 1200, 600, 60]]}  // extra boxes for this cut, source px
    ],
    "hl": ["comeback", "first"],       // highlighted caption words (case/accent-insensitive)
    "fix": {"stab": "TAB",             // caption fix by word...
            "5328.70": "tomei",        // ...or by the word starting at this source time
            "5330.10": ""},            // "" drops a word
    "caps": [[s, e, "MANUAL TEXT"]],   // optional: manual captions instead of words.json
    "fx": [                            // at source time t, inside a cut
      {"t": 1586.0, "kind": "punch", "len": 0.6, "strength": 0.22, "text": "COMEBACK?"},
      {"t": 1600.2, "kind": "shake", "len": 0.6, "strength": 22},
      {"t": 1603.0, "kind": "flash", "len": 0.3}
    ],
    "outro": {"text": "COMEBACK\nCANCELLED", "sec": 1.5}   // freeze-frame punchline card
  }]
}
```

## Layouts (1080×1920)

| layout | what it shows | use for |
|---|---|---|
| `stack` | cam panel 1080×760 on top, gameplay 1080×1160 below (full-height crop around `gameX`, never sliding into the cam overlay) | gameplay beats with the reaction visible |
| `face` | cam panel 1080×1290 plus a zoomed game strip | reactions, stories, punchlines |
| `game` | full-height game with the cam as a rounded bubble | pure plays where the face doesn't matter |

Layout changes animate over 7 frames, so switching `stack` → `face` on the punchline reads as a deliberate zoom. `gameX` (0–1) moves the game crop: 0.5 is the crosshair, and lower values move it left toward a minimap or kill feed.

## Captions
Karaoke chunks of 1–3 words (≤17 characters), broken on pauses over 0.35 s, punctuation and cut boundaries. Words not yet spoken are dimmed, the spoken word pops, and `hl` words are yellow and larger. The y position follows the layout seam (below the cam), never the bottom 25%, with a 150 px right margin.

## Effects
- `punch`: spring zoom by `strength` (default 0.22).
- `shake`: amplitude in px (default 26).
- `flash`: a white flash.
- `text` on any effect adds a sticker. Stickers go below the eyes in `face` layout and over the game in `stack`.

Use 3–6 effects per Short, on real beats (the reveal, the death, the punchline), not as decoration.

## Montages
Cuts may jump across hours (e.g. three "small streamer" moments at 0:00:56, 1:30:28 and 2:45:31). The builder groups cuts less than 20 s apart into one proxy each.
