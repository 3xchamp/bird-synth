# bird-synth — SYRINX·6

A bird-synth engine: six real birds, measured note-by-note from reference
recordings and re-synthesized live in the browser. No recorded audio is played —
every note is built from measured pitch contours, amplitude envelopes, timing
and breath noise. Each voice sits on a continuum: turn **Morph** and it slides
from true birdsong toward electronic synth.

## Play it

Open **`syrinx6.html`** in a browser — the full instrument:

- Six animated birds on a wire, one channel strip each (SING, fader, morph)
- Master **CHORUS** (a conducted dawn chorus), **Morph / Breath / Tempo /
  Space / Volume**, and a two-octave keyboard that plays the selected bird's
  voice at any pitch
- **SONG mode** with a preloadable song library and a FREE PLAY / SONG toggle.
  The demo track is the **Minuet in G major, BWV Anh. 114** (attributed to
  Christian Petzold, from Bach's *Notebook for Anna Magdalena*): the melody
  rotates phrase by phrase through the five songbirds, the owl plays bass,
  and the **FULLNESS** knob fades in a harmony bird, bass movement, body and
  room — sweep Morph mid-song to melt Bach from birdsong into synth

The single-voice lab pages (`cardinal.html`, `owl.html`, …) are the
instruments the bank was built from, one bird at a time. `heron.html` is a
standalone experiment (the Great Blue Heron voice was replaced in the bank by
the Hermit Thrush).

## The voices — measured, not sampled

| Voice | Source recording | License |
|---|---|---|
| Northern Cardinal | XC75501, Jonathon Jongsma | CC BY-SA 3.0 |
| Great Horned Owl | XC11638, Nathan Pieplow | CC BY-NC-ND 2.5 |
| Hermit Thrush | XC1048898, AUDEVARD Aurélien | CC BY-NC-SA 4.0 |
| Carolina Wren | XC364592, Brian Murphy | CC BY-NC-SA 4.0 |
| Song Sparrow | XC1005250, Ryan Douglas | CC BY-SA 4.0 |
| Eastern Towhee | XC1015083, Stanislas Wroza | CC BY-NC-SA 4.0 |

Recordings via [Xeno-canto](https://xeno-canto.org). The reference audio files
are **not** in this repo (their licenses don't all allow redistribution); each
`samples/<species>/SOURCES.md` records exactly what was used.

## How it's built

- `ENGINE-UI-SPEC.md` — the instrument design
- `BUILD-syrinx6.md` — the flagship build log: bank assembly, song mode,
  fullness, and the scheduler exception-safety fix
- `BUILD-<bird>.md` — one build/measurement log per voice
- `analysis/` — measurement JSONs per species, the measurement pipeline
  (ffmpeg + Python), the note-audited Minuet transcription
  (`minuet_bwv_anh114_transcription.json`, sourced from a public-domain
  Bach-Gesellschaft typeset via Mutopia/IMSLP), and the verification suites

Verification (Node): `analysis/verify_syrinx6_audit.js`,
`analysis/verify_syrinx6_harness.js`, `analysis/verify_song_score.js`,
`analysis/verify_song_harness.js` — bank constants are audited against the
measurement JSONs, the song score against the transcription, and playback
behavior in a stub audio graph.

One law runs through the engine: each voice's breath/noise lives on a single
fixed path, shaped only by gain envelopes — never connected or disconnected
per note.
