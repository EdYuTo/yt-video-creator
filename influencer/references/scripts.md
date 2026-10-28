# Writing reel scripts that sound like the creator

The first version of this workflow wrote neutral, article-style scripts. They were accurate and easy to
read on a teleprompter, but the creator's verdict was that they didn't sound like them. A reel works when it
sounds like a person talking to a friend. Accuracy comes from the fact table; tone comes from the creator.

## Get their voice before writing a word

In order of usefulness:
1. **A rambling take on the topic.** Have them talk to camera for 2–5 minutes, unscripted. Transcribe it
   (`transcribe.py skim`). This is the best source by far, because it has their openers, their fillers
   worth keeping, their analogies and their opinions.
2. Old videos or posts of theirs (transcribe or read).
3. Messages or notes in their own words.
4. As a last resort, ask three questions and transcribe the answers: "How would you explain this to a
   friend?", "What do people usually get wrong?", "What happened to you with this?"

From that material, note:
- how they open;
- words they repeat;
- slang and code-switching (e.g. Portuguese with English tech terms);
- how long their sentences run;
- whether they joke, and how;
- the stories they reach for.

## Write

- **Talk, don't write.**
  - Contractions, short sentences, direct address ("você", "you").
  - Start lines with how they'd start them ("Olha…", "So here's the thing…").
  - Avoid article connectors ("Furthermore", "Além disso,") unless they actually say them.
- **Keep their framing.** If the raw take said "everyone says you need a fancy camera — you don't", keep
  that rhythm. Just make the claim defensible, or make it theirs: "everyone says you need a fancy camera.
  This whole video? Shot on my phone."
- **First person when they want it.** Their story ("my first video got 12 views") beats a generic
  claim, as long as they're happy to share it and it's true. Ask; don't assume either way.
- **Hook in their words.** The first line (and the hook card) is a surprising fact, a strong opinion or a
  question, in their phrasing.
- **One idea per line, ≤ ~20 words**, so each line is one breath and one teleprompter line. The demo
  changes on line boundaries, so a line is also a visual unit.
- **Facts only from the fact table.** Soften where the table says to soften. Never invent numbers, prices
  or "studies show".
- **No mandatory sign-off.** A "save this reel" line on every reel gets annoying. Put the call to action on
  the end card, and in the spoken text only when it adds something.
- **Read it aloud yourself** (in your head, at speaking pace) and cut anything you'd stumble on: long
  numbers, nested clauses, acronyms that need spelling out.

## Shape of a reel (40–75 s)

1. Hook (1 line): why should I keep watching?
2. What it is (1–2 lines).
3. The substance (4–8 lines): what matters, how to do it, the mistake to avoid. Each line names something
   the demo can show.
4. A takeaway (1 line), optionally a pointer to the series' overview reel.

## In `reels.json`

Each line has:
- `text`;
- `demo`, a beat id or `card`;
- `head`: `bl` (default, bottom-left), `tl` (when the demo's key content is bottom-left), or `big` (the
  hook, or a moment that's about the person);
- `anns`: labels, handwritten notes, ticked lists, bars, rings and arrows, timed with `in`/`out` as
  fractions of the line.

Keep annotations short (2–5 words). They echo the line; they don't repeat it. Mark claims the creator
should double-check with `"confirm": true`; the export flags them.

Optional top-level `"rules"` make the validator enforce project policy, e.g.
`{"noPrices": true, "banned": ["leaked"]}`.

## When the creator ad-libs

Let them. The take picker keeps what they said and the subtitles follow it. Only a changed *fact* needs a
re-read.
