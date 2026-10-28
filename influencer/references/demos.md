# Screen demos at 9:16

Demos are recorded **after** the voice is cut. Each `demo` id in `reels.json` is a beat. Consecutive lines
with the same id form a run that plays one continuous clip; `assemble_reels.py` prints the minimum length
of each run. Record every beat with `--seconds` set to the run length plus 1.

## Types (`demos/manifest.json`)

| type | use it for | manifest entry |
|---|---|---|
| `web` | live websites and web apps | `{"type": "web"}` → clip `demo-<id>`, recorded with `demo_rec.mjs` |
| `video` | a recorded clip that already fits 9:16 (or skip a loading screen with `from`) | `{"type": "video", "clip": "demo-<id>", "from": 3.5}` |
| `crop` | part of an existing landscape recording (a desktop app, an old screen capture) | `{"type": "crop", "clip": "<id>", "from": s, "rect": [x0,y0,x1,y1], "rectTo": [...]}`, fractions of the source; `rectTo` pushes in over the line |
| `card` | nothing on screen; the annotations carry it | no entry needed |

## Logged-in websites

1. `node $R/scripts/demo_rec.mjs login --urls https://a.com,https://b.com` opens **real** Google Chrome on
   the dedicated profile `~/.cache/yt-video-creator/browser-profile-chrome`. Google refuses sign-in inside
   automated Chromium, which is why this step uses real Chrome.
2. The creator signs in, then **quits** that Chrome (⌘Q). Closing the window isn't enough, because the
   running app keeps the profile locked.
3. Check: record a 4-second beat per site and look at the last frame for their avatar or name.

## Beats (`demos/beats.mjs`)

```js
export default {
  "r1-problem": {
    url: "https://example.com/page",
    async run(page, h) {
      await h.pause(800);                      // let the line's first words land
      await h.scrollTo("#example-1", 1400);    // eased scroll; optional container selector for SPAs
      await h.click("button.tab-2");           // animated cursor dot, then click
      await h.type("input[name=q]", "query");  // refuses password fields
      await h.pause(2000);
    },
  },
};
```

- Time each action to the line it illustrates. Line starts within a run are the cumulative take durations
  (`takes/<reel>.json`).
- The viewport is 432×768 CSS px at device scale 2.5, so sites render their mobile or narrow layout.
  Check that the content you need actually fits. Some sites remember panel widths in the profile, so
  adjust them once, by hand or in the beat.
- Keep the key content out of the bubble's corner. `bl` covers roughly x 5–32 % and y 51–72 % of the
  frame, `tl` the top-left. Subtitles own y 76–86 %, and the platform's buttons the right 12 %.
- `h.hide([...])` is for cookie banners and app-install bars only.

```bash
node $R/scripts/demo_rec.mjs record --project <proj> --beats <proj>/demos/beats.mjs --id r1-problem --seconds 26
```

The clip is written to `recordings/demos/<id>.mp4` and registered as `demo-<id>`. A `WARN … overran` means
the beat took longer than `--seconds`: raise it.

## Code on screen

Don't show real proprietary code. Write a short mock file that has exactly the problems or ideas the
script names, with lines ≤ 40 characters so they fit a phone width without scrolling. Then:

```bash
node $R/assets/code-viewer/build_viewer.mjs mock/ListView.swift demos/code.html --lang swift
```

The page gives each line an id `#L<n>` and exposes `window.mark(from, to)`, `unmark()` and
`scrollToLine(n)`. A `web` beat on `file://…/code.html` can then scroll to a bug and highlight it while
the creator talks about it.

## Desktop apps and old recordings

Desktop apps can't be driven. Reuse an existing screen recording as a `crop` beat. Measure the rectangle
on a gridded still at each moment you use, because windows move. Push in (`rectTo`) to make text
readable, and avoid regions with content the creator doesn't want readable.
