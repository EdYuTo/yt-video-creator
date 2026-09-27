# YouTube formats

## Long-form (regular upload)
- **1920×1080, 16:9, 30 fps** (match the footage frame rate; 29.97 source at 30 is fine). 4K only if all the footage is 4K and the user wants it.
- H.264, CRF ~16, AAC audio (the template config does this). YouTube re-encodes, so a high-quality master helps.
- Process/recipe/tutorial videos: 2–4 min is the sweet spot for footage like this. Talk/vlog cuts: 5–10 min, alternating talk windows with short b-roll. Front-load the result: open on the finished thing (hero photo or payoff shot) with the title, then show how.
- Readability: captions of at least 38 px at 1080p. Keep text away from the bottom-right corner (YouTube's player controls and end-screen elements).
- End screen: YouTube lets creators add end-screen cards in the last 5–20 s. A calm outro card (summary/recipe) of 7+ s works well for that.
- Thumbnail (optional extra): 1280×720 still. Render a frame with the hero shot and a big title if the user wants one.

## Shorts (and TikTok / Instagram Reels — the same file works on all three)
- **1080×1920, 9:16, 30 fps**, ≤ 60 s to be safe on all platforms (YouTube allows up to 3 min now; others vary). 30–45 s is the sweet spot for a process video.
- **Safe zones**: the bottom ~25% (caption, username, music ticker) and the right ~12% (like/comment/share buttons) are covered by UI, and the top ~8% by tabs/search. Put headlines in the upper-middle band (the template uses `paddingTop: 250` at 1920 tall) and keep key action near the center.
- **Hook**: the first 1–3 s decide retention. Open on the payoff (the gooey break, the finished build) with a short promise line. Don't open on setup.
- **Pacing**: 1–2 beats per shot (≈0.6–1.2 s at 100–110 BPM). Cutting on beats makes even simple edits feel intentional.
- **Text**: one or two words big (≈150 px), plus an optional short pill line. Viewers don't read sentences in Shorts. Put the full details in the caption/description.
- **Cropping 16:9 footage**: only ~32% of the width survives. Set each shot's `x` from a fine sheet: overhead shots usually center at 40–55%, and people walking in and out of frame need a per-shot check. If the subject can't fit, use `fit: 'blur'` (the whole frame letterboxed over a blurred copy) rather than cutting it off.
- Square or vertical phone clips: square uses `fit: 'blur'`; vertical fills natively.

## Music
- Prefer tracks the user owns or that are free for YouTube ([YouTube Audio Library](https://www.youtube.com/audiolibrary)). Content ID claims can block or demonetize uploads. Credit the track in the credits and description even when it isn't required.
- Music-driven long-form (`mode: "bed"`): fade in over 0.5 s and out over the last 2 s. Ideally the video length equals the song length (`matchSong`) so it ends naturally.
- Talk long-form (`mode: "broll"`): music only under b-roll and cards, around 0.15 volume, never under speech. See references/talk.md.
- Short: start at a strong downbeat (after a break) and end on a phrase decay. A short fade (~0.4 s) avoids a click.

## Privacy
- People other than the creator (friends, staff, strangers) may not want to be on YouTube. Ask up front, and by default blur faces that aren't the creator's (`faces.py` + `blur` boxes), or replace the shot.
- Don't name private people or small businesses in titles or credits unless the user asks.
