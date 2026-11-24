# How the phone talks to the clip (for the app, now and later)

Kept simple on purpose, so the web app now and a real App Store app later both use the same thing.

- Bluetooth name: `RAVE CLIP`
- Service UUID: `f3a1c0de-5a7e-4b1d-9c00-000000000001`
- Artist characteristic: `f3a1c0de-5a7e-4b1d-9c00-000000000002` (read, write, write without response)
- To change the look: write the artist name as UTF-8 text, at most 40 bytes, e.g. `Peggy Gou`.
- Empty text or `-` means "no artist playing": the clip shows the bunny face.
- The clip matches names loosely: lowercase, letters and numbers only, accents removed (`RØZ` = `roz`, `Fred again..` = `fredagain`).

## Schedule (auto mode), added in step 3

- Schedule characteristic: `f3a1c0de-5a7e-4b1d-9c00-000000000003` (write)
- The phone writes one line per write, in this order:
  - `C` clears the clip's schedule (auto mode off)
  - `T|<seconds since 1970>` tells the clip what time it is now
  - `S|<start>|<end>|<artist>` one set (times in seconds since 1970), up to 80
  - `GO` turns auto mode on
- In auto mode the clip checks twice a second who's on and switches by itself, so it keeps working while the phone is locked. Nobody on = bunny face.
- Writing an artist to the artist characteristic turns auto mode off (manual).
- The clip forgets the schedule when it's switched off; the app resends it on every reconnect.

## Schedule file format (app side)

Canonical JSON, see `web-app/schedule.js`:
`{ "festival", "stages": [{ "name", "lat", "lon" }], "sets": [{ "artist", "stage", "start": "YYYY-MM-DDTHH:MM", "end" }] }`
Times are festival local time. CSV uploads (columns `artist, stage, date, start, end`, optional `festival`, and optional stage spot as `lat` + `lon` or one `location` column like "34.05, -118.24") are converted to this. Stage `radius` (meters, default 150) = how close counts as being at that stage. The app switches stage after 20 s near a new one and ignores GPS fixes worse than 150 m.

## AI looks, added in AI step 1

- AI look characteristic: `f3a1c0de-5a7e-4b1d-9c00-000000000004` (write)
- The phone writes one line: `character|main|accent|background|effects|motion|text`
  - e.g. `bunny|FF9CC8|FFFFFF|2A0F3D|hearts,sparkles|bounce|` or `heart|FF2FA0|FFD1DC|2B0014|hearts|pulse|I LOVE ROZ`
  - character: bunny, cat, bear, frog, ghost, alien, heart, star, mushroom, cherry, cloud, moon, flower, or none
  - colors: 6 hex digits, no `#`
  - effects: up to 3, comma separated: hearts, sparkles, stars, bubbles, notes, rain, confetti, zzz
  - motion: bounce, float, sway, shake, pulse, dance
  - text: up to 16 plain characters, no `|`
- Like writing an artist, this turns auto mode off. Writing an artist afterwards goes back to artist looks.
- The recipe is made on the phone by `web-app/ai-designer.js` (MiniLM embeddings, runs in the browser). The clip draws it with `festival_clip/ai_look.h`, and the app preview uses `web-app/looks.js`, which draws the same pixels.

## Scenes (words + effects + background + mini-me), added in scene step 1

- Scene characteristic: `f3a1c0de-5a7e-4b1d-9c00-000000000005` (write), up to 200 bytes
- One line of `key=value` pairs joined by `;`, text last:
  `fx=invert;sp=2;st=shadow;fg=FFFFFF;ac=FF2FA0;bg=000000;b2=FF2FA0;bp=solid;av=none;hr=curly;t=ROZ`
  - fx (text effect): still, scroll, wave, bounce, invert, rainbow, glitch, type, pulse
  - sp (speed): 1 slow, 2 medium, 3 fast. Invert flashes at 1/2/3 per second, never faster (seizure safety)
  - st (letters): plain, shadow, outline (bubble)
  - fg letters, ac shadow/bubble, bg background, b2 pattern color: 6 hex digits
  - bp (background): solid, gradient, checker, stripes, dots, stars, hearts, sparkles, rainbow
  - av (mini-me): none, smile, teeth, ooh, grin, chill (faces), dance1, dance2, dance3. Alexia's own GIF sprites, 8 frames each, drawn 4x on the left; the words fit on the right. Old names idle/kiss/dance/jump/squat still work.
  - hr (mini-me hair): straight or curly
  - t (text): up to 24 plain characters, no `;` or `|`. Long text scrolls by itself
- Like the other looks, this turns auto mode off. Drawn by `festival_clip/scene.h`; the app preview `web-app/scene.js` draws the same pixels.
