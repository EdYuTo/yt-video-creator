# Risks to check before a Short goes out

## Copyrighted audio (Content ID on YouTube; takedowns or muting on TikTok and Instagram)
You can't listen, so find the likely spots and **tell the user which clips to play once before posting**:
- **In-game music**: CS2 MVP anthems and music kits at round end, Apex lobby music, Valorant agent-select
  music. They're usually short, but Content ID matches short clips.
- **Song-request bots** or background music on stream: look for "music", "song" or "!sr" in the transcript,
  and "Now playing" overlays on sheets.
- **Videos watched on stream** (TV shows, trailers, YouTube videos): exclude those ranges. They show up
  on the overview sheet as non-game footage.
- Don't add music by default. The stream audio is the content.

## Privacy
Ask up front and follow the user's choice. Defaults if you can't ask:
- **Other players' gamertags** (scoreboard, kill feed, kill cards, MVP banner, spectator label): the
  first user wanted them **visible**. Ask; blur with `gameBlur` / per-cut `blur` only if they want it.
- **Chat and alerts**: blur a viewer's name when it's tied to something embarrassing or obscene (e.g. an
  alert shown while the streamer reads out a crude message). Otherwise viewer names in alerts are usually fine.
- **Friends' voices and names** (Discord): keep them, but list them in the report so the user can check
  their friends are OK with it.
- **Desktop, Steam, Discord, lobbies, DMs, notifications**: blur the game panel (`blurGame`) during those
  cuts. Personal info on screen (emails, phone numbers, addresses, real names in DMs) must never ship.
- **Other people on camera**: use yt-video-creator's `faces.py scan --edges` on the renders.

## Content
- Profanity and crude topics are common. Note them per Short, since some platforms limit the reach of
  such videos, and offer bleeps if the user wants them.
- Remove anything that needs context the viewer won't have, or add it in the hook line.
