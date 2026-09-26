# Talk footage: dialogue, silences, subtitles

For vlogs, food and travel videos, interviews: anything where what people *say* matters.
Learned on a 93-min restaurant dinner (Portuguese conversation, Japanese staff) cut to 7 min.

## Pipeline

1. **Setup once**: `bash <skill>/scripts/setup_speech.sh` prints the venv python (`$VENV_PY`).
   Whisper models download from Hugging Face on first use. Audio never leaves the machine; don't
   send the user's audio to web transcription services.
2. **Skim**: `$VENV_PY transcribe.py skim <ids...> --project <proj> --language <lang>`.
   The small model runs at about 4–5× realtime on Apple Silicon (40 min of audio ≈ 9 min). Run it in
   the background for long footage and start on the contact sheets meanwhile.
3. **Choose** conversations from `transcripts/<id>.txt` (see below). Write down windows as
   `id:start-end` with ~0.5 s of slack on each side.
4. **Words**: `$VENV_PY transcribe.py words <id>:<s>-<e> ... --project <proj> --language <lang>`
   (large-v3-turbo, ~2–3 min for ~17 min of windows). Results merge into `transcripts/words.json`.
   Re-running a window replaces it.
5. **Plan**: add `{"clip", "talk": [s, e], "subs": [[s, e, "text"], ...]}` items. The subtitle
   times come from the word-level transcript, in source time. `build_edit.py` cuts silences
   (words padded 0.2/0.3 s, gaps under 0.75 s merged) into jump-cut shots with 2-frame audio ramps,
   and moves each subtitle onto the cut timeline without letting it run into the next one.
6. **Verify**: `audio_levels.py` on the render, and listen-proxy by re-reading the transcript of what
   you kept.

## Transcription pitfalls

- **Force the language.** Whisper auto-detects from the first 30 s; one waiter speaking Japanese
  turned 40 min of Portuguese into repeated nonsense Japanese. Speech in other languages then comes
  out roughly translated into the forced language, which is usually fine as subtitle material.
- The **small model loops** on noise and music ("RICARDO" ×12, the same question ×14).
  `condition_on_previous_text=False` (already set) helps; for kept windows always use `words`
  (turbo), never the skim text, for timing and subtitles.
- **Mixed-language scenes** (ordering in Japanese, the chef's English): keep what's funny or
  telling, and subtitle it with what was meant, not a literal transcript of broken speech.
- **Energy-based silence detection doesn't work in noisy rooms**: grill, fans and chatter kept
  55 of every 60 s above threshold. `speech_map.py` is only useful for quiet footage (talking
  to camera at home, voice-over).

## Choosing what to keep

- Keep: reactions to the food or place ("it melts in your mouth"), explanations the viewer learns
  from (how to eat it, what it is, prices), funny exchanges, interactions with staff and locals.
- Cut: logistics (trains, phone battery, paying the bill unless it's funny), repeated debates,
  long "is it worth it" loops, meta talk about the channel, anything a guest might not want public.
- Aim for talk windows of 5–25 s and alternate them with 3–6 s of b-roll or a photo. That rhythm
  is what makes a 7-min cut from 90 min feel fast without losing the people.
- Bloopers: failed attempts, laughing fits, broken-language moments. Put them in `long.post`
  (grayscale after the credits, own audio, with subtitles). Use `"cut": false` if the pauses are part
  of the joke.

## Subtitles

- Write them in the on-screen language the user chose (translate as needed). Keep lines short (≤ 60
  characters) and split long sentences across several `subs` entries at natural pauses.
- In talk videos section titles move top-left and leave after ~4.5 s (`captions: "auto"`), because
  subtitles own the bottom of the frame.

## Music with dialogue

`long.music.mode: "broll"`: music plays only under b-roll, photos and cards, never under speech,
around volume 0.14–0.2. `audio_levels.py` should show music-only b-roll 6–8 dB below talk. The
song's position carries over between b-roll runs, so it plays through instead of restarting. It
wraps (with fades) only if the b-roll total exceeds the song. Use `"ambient": 0.2–0.4` on 1× b-roll
where the source sound adds something (sizzle, street).
