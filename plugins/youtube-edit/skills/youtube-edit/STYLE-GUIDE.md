# Style guide

This is the Deal Smith Realty look the skill ships with (adapted on Monday, October 5, 2026 from the WeAreNoCode kit's original channel look).

Where it lives: YOUR colours are in your own config, `~/.config/youtube-edit/config.json` (`brand.highlight`, `brand.anchor`, `brand.punchline`); `/video-setup` asks for them, and leaving them alone keeps the gold below. The composer writes your colours over these defaults on every page. Every rule below is written into `youtube-edit/SKILL.md`; your own changes to the look go in `~/.config/youtube-edit/MY-RULES.md`. You don't need to open any of these; Claude does it.

## Colours (Deal Smith Realty brand)

The defaults come from the Deal Smith Realty brand sheet. The composer keeps the kit's token
NAMES (`--cyan`, `--blue`, `--magenta`, `--amber`) so every rule still resolves; read them as the roles below.

| Role (config key) | Token name in compose.py | Default (DSR) value |
|---|---|---|
| Highlight (key words, ticks, bars) (`brand.highlight`) | `--cyan` | Gold-400 `#FFBB00` (brand primary) |
| Deep anchor (gradient end, a word-highlight block with white text) (`brand.anchor`) | `--blue` | Gold-700 `#8F6A10` |
| Punchline (the payoff word, the last step of a diagram) (`brand.punchline`) | `--magenta` | Gold-100 `#FCEFAE` (bright sheen) |
| Money and stakes (dollar figures, warnings) | `--amber` | Gold-400 `#FFBB00` (same as highlight: the brand has one accent) |
| Text | `--white` | White `#FFFFFF` |
| Light surface (bright scenes, cards on dark) | | Bone `#F7F4EE` |
| Dark surface | | DSR Black `#0A0A0A` |

Rules: gold is the only accent; never a second hue for emphasis. A dark gold block behind white text is fine; dark gold
as a highlighted WORD on dark footage is not (it disappears). One gradient per frame. The Gold-700 to Gold-400 range
is the only gradient.

## Font

| | Mine | Yours |
|---|---|---|
| Font | DM Sans, weights 400, 500 and 700 (in `youtube-edit/assets/fonts`). The DSR brand fonts are Instrument Serif (display) and Geist (body), but no local woff2 copies exist yet; until they are added to `assets/fonts/` and wired into compose.py, DM Sans stays. | |
| Headlines | 700, with a thin stroke in the same colour to make it heavier | |
| Big numbers | Every digit written out (`$207,000,000`, never `$207M`), white, counting up | |

## Cards and text on screen

| | Mine | Yours |
|---|---|---|
| Card style | Frosted glass: light glass on dark scenes, dark glass on a bright room | |
| Default for words | One line at the bottom, key words in the highlight colour | |
| Lists | Never a list panel. Each item becomes its own thing: pills next to my head, a diagram, one animation per number | |
| My face | Not the default background. 40% or more of a talking section is full-screen animation | |
| A person or job I mention | 3 seconds of B-roll of that person doing it | |
| An app I name | A clean, designed window of it, not a screenshot | |
| A website or post I name | The real page, in a browser window, scrolling | |

## Motion

| | Mine | Yours |
|---|---|---|
| Things coming in | 0.4 s, soft ease out. No bounces, no flips | |
| Things leaving | 0.35 s | |
| Timing | Every animation lands on the word it belongs to, a beat before I say it | |
| Variety | Never the same type of animation twice in a row | |
| Busy check | About 7 animations and 7 camera moves per 90 seconds | |

## Camera

| | Mine | Yours |
|---|---|---|
| Zoom anchor | The top of the frame, so my head never gets cropped | |
| Punch-in on a key word | 118 to 125%, a third of a second | |
| Slow creep across a thought | 110 to 112% over 5 to 10 seconds | |
| At every cut | Back to 100% | |

## Sound

| | Mine | Yours |
|---|---|---|
| Default | Silence. A sound has to earn its place | |
| Allowed | A pop when a logo lands, a light click when a cursor clicks, typing only when someone types, a cha-ching at very low volume for money | |
| Never | A whoosh under text | |
| Music | Something tense under the hook, then lo-fi, very low, ducked under my voice | |

## Cuts

| | Mine | Yours |
|---|---|---|
| Retakes | Keep the last take of every line | |
| Pauses | Nothing longer than about 0.4 s after a sentence | |
| Live demos | Show the result, not the waiting | |
| Flash cuts | Never | |
