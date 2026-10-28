# The recording session

## Setup checklist (tell the creator)

- **Camera:**
  - The Mac's camera, or an iPhone via Continuity Camera, which is sharper. Mount it at eye level.
  - Sit centred, with a hand's width of space above the hair. The bubble shows the head breaking out over
    the top of a circle, so the hair needs room.
  - Keep the same seat for every reel, and one crop fits all.
- **Mic:** a clip-on or USB mic if they have one. The page has a mic picker.
- **Background:** a plain wall or a virtual background both cut out fine. Turn off Portrait (background
  blur), because the cut-out needs the real edge. Presenter Overlay won't show up, and that's expected.
- **Eye line:** make the browser window small and put it right under the camera, so their eyes stay near
  the lens while reading.

## The teleprompter

```bash
node $R/teleprompter/server.mjs --project <proj> [--port 3918]
```

It serves `http://localhost:3918` and reads `scripts/reels.json`. Nothing leaves the machine.

How the creator uses it:
- Pick the reel and set the speed (110–260 wpm). Most people end up at 200–220.
- **Record** gives a 3-2-1 countdown, then the lines run karaoke-style.
- **Tap** anywhere to restart the current line; a tap in the line's first second goes back one line. It
  keeps recording either way.
- **Stop** or Esc ends the take.
- A red banner means an upload failed: stop and check the server.

What it saves:
- `recordings/raw/<reel>-<take>.webm`, VP9 + Opus. Each second's chunk is sent to the server as it's
  recorded, so a crash keeps everything up to the last second.
- `recordings/raw/<reel>-<take>.log.json`, with every line start and tap in seconds from the start of the
  recording.

Every Record press is a new take. The latest **complete** take (its log reaches the last line) is the one
to import.

## Check the first reel before the rest

1. Import it, transcribe it and run `takes.py`.
2. Check:
   - every line was found;
   - misreads versus mishearings (re-transcribe a doubtful window with and without a hint, and if both
     hear the same thing, it was said);
   - speech level;
   - pause noise.
3. Make one 3-second bubble preview from the take, and show it to the creator together with any misread
   lines.

## After the session

- Queue all bubbles in one background job, one reel after another. The cut-out is CPU-heavy, and running
  them in parallel only slows everything down.
- Keep the takes' hand edits (dropped lines, ad-lib windows) in EDIT-NOTES. `takes.py` regenerates
  `takes/*.json` from scratch.
