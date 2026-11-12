# SYRINX·6 — the bank page (build record, 2026-11-12)

**File:** `syrinx6.html` (single file, ~89 KB) — the bird-synth engine's flagship
interface, built to `ENGINE-UI-SPEC.md`. The six lab pages stay as they are;
this page ports all six verified voice engines into one hardware-style synth.

## What it is

- **Chassis:** dark brushed panel, corner screws, engraved-style labels, one
  orange accent + phosphor screen glow. Desktop-first grid that stacks on a
  phone (master under screen, strips 3- then 2-wide, keyboard full width).
- **Screen:** bezel-framed LCD. Six flat-style birds on a wire, drawn as inline
  SVG in their real colors (cardinal red, owl brown/cream, heron blue-grey,
  wren warm brown, sparrow grey-brown, towhee rust/black/white). Under the
  wire, a live scrolling spectrogram strip (master AnalyserNode → canvas,
  log-spaced rows, phosphor→orange palette) and a mono readout line:
  ON AIR (active birds), PHRASE (last phrase type + bird), MORPH (selected
  channel's effective %), GRID (tempo BPM). The screen has a scanline overlay.
- **Animation:** every note/burst scheduled by any voice fires exactly one
  `onNote` callback from inside the scheduling call itself (schedule-time,
  no polling). The screen handler aligns a timer to the note's audio start:
  the bird's lower beak rotates open (per-voice base angle × note intensity),
  head tilts, body bobs, throat patch pulses; the channel LED lights and the
  strip's phrase readout updates for the note's duration.
- **Six channel strips:** name plate (common + Latin), SING button (toggles
  that bird's measured bout grammar, looping with its measured pauses —
  the owl keeps its real 27.5 s inter-series patience), level fader,
  per-bird MORPH knob, channel LED, last-phrase readout. Clicking a strip
  selects it for the keyboard.
- **Master section:** CHORUS and STOP buttons; MORPH, BREATH, TEMPO, SPACE
  knobs; VOLUME knob; signal LED. Knobs are vertical-drag rotary with wheel
  support and value readouts; faders are drag sliders. Every control is wired
  to the graph — no decorative fakes.
- **Keyboard:** two octaves (C4–C6), mouse/touch + computer keys
  (Z-row = lower octave with S D G H J sharps, Q-row = upper with 2 3 5 6 7,
  mapping printed on the keys). It plays the SELECTED bird's voice: that
  bird's lead phrase template (cardinal D, owl P3, heron M-burst, wren L,
  sparrow I, towhee I2) — measured envelope + harmonic recipe + breath —
  transposed chromatically, crossfading to a plain saw+square synth voice
  as the channel's effective morph → 1.

## Audio architecture

- One shared core: channels → mix bus → DynamicsCompressor limiter
  (threshold −18 dB, ratio 6, knee 18 — the cardinal/owl lab setting) →
  analyser → volume → destination.
- Per voice, the lab page's own chain is ported faithfully: the five tonal
  voices keep their bandpass/peaking/lowpass trachea chain at the lab values
  (owl keeps its 520/700 Hz retune for the 323 Hz hoot) and their breath
  filter frequency; the heron keeps its fixed 6-band profile bank
  (300/636/1273/2400/4080/6448 Hz, Q 1.3) + tonal-core design, PEAK_CAP 0.8.
- **Audio law holds:** per voice exactly one fixed breath/noise path, wired
  once at init, shaped only by scheduled gain envelopes (breath peak ≤ 0.05 ×
  the note's own peak, endpoints forced to 0). The BREATH knob trims that
  path's output 0 → its capped maximum; it can only ever turn the measured
  envelope down. The word the audits search for — the per-note re-wiring
  operation — appears zero times in the file.
- **Morph semantics:** per-voice morph composes with master morph as
  m_eff = 1 − (1 − m_voice)(1 − m_master) (master pushes every voice toward
  the electronic end; at master 0 each voice is purely its own knob).
  Pitch log-lerps to the A-major-pentatonic grid, timing to the TEMPO grid,
  saw + FM edge fade in, and at m_eff ≥ 0.5 the voice's plan loops (the lab
  pages' loop-lock, plan cached). TEMPO (60–160, default 112) rescales all
  grid-side times by 112/BPM, so the grid is real, not a label.
- **CHORUS:** stops any solo singing, then one full bout/series/performance
  per bird, staggered in a fixed conductor's order — owl 0 s (the knock in
  the dark), towhee +2.5, wren +5, sparrow +7.5, cardinal +10.5, heron +13
  (the flyover snarl as finale) — each at its channel fader level. A cycle
  ends when the last bird finishes; at master morph ≥ 0.5 it loops with one
  grid bar between cycles. STOP halts all schedulers and chorus, stops every
  sounding source, cancels breath envelopes to 0, and clears pending
  animation (epoch guard).
- **SPACE:** one shared feedback-delay send off the post-fader channel taps:
  0.28 s delay, feedback 0.35 through an 1800 Hz lowpass in the loop,
  wet 0.9 back to the mix. Knob default 0.

## Verification (all headless; scripts kept in `analysis/`)

- `node --check` on the page script: **pass**.
- **DOM audit** (`verify_syrinx6_audit.js`): 24 literal `getElementById`
  targets + 6 dynamic `bird-<id>` targets = **30 checked, all present** in
  the HTML. (Strip internals and keys are built by JS with kept references,
  and are exercised for real by the harness below.)
- **Constants audit — bank vs lab pages:** the bank's data block was
  generated from the lab pages' MEAS literals and re-compared leaf by leaf:
  cardinal 200, owl 188, heron 187, wren 224, sparrow 556, towhee 187 =
  **1,542 numeric leaves, 0 mismatches**.
- **Constants audit — bank vs measurements JSONs:** cardinal 167 + 3 pause,
  owl 160, wren 193, sparrow 492, towhee 156 + 15 grammar, heron 120
  (contours, amp templates, durations, f0/profile/sequence for the heron,
  transitions, pauses) = **1,303 values, 0 mismatches**; max deviation
  0.05, entirely the lab pages' own rounding of medians (e.g. 2131.787 →
  2131.8 Hz). Derived `peak` fields follow the lab pages' documented
  derivations and are covered by the exact bank↔lab port check.
- **Static breath/noise audit:** 0 occurrences of the re-wiring operation;
  exactly 1 wiring site each for breathEnv/breathTrim/noiseEnv/noiseTrim
  (all inside the two voice builders); note renderers (tonalPlay, heronPlay,
  synthNote) contain no wiring calls on the breath/noise paths; exactly one
  envelope writer per path.
- **Stub-graph harness** (`verify_syrinx6_harness.js`): the page runs
  against a fake DOM + fake Web Audio graph on a fake clock — **68 checks,
  0 failures**:
  - init builds exactly **6 runtime noise sources** (one fixed path per voice);
  - 35 s of Sing per voice: cardinal 40, owl 8, heron 24, wren 84, sparrow 48,
    towhee 63 notes — **animation callbacks fired exactly once per scheduled
    note**, per voice;
  - breath caps respected everywhere (worst: owl 0.02232 vs cap 0.02300;
    cardinal 0.01938/0.02300; towhee 0.02220/0.03362); heron noise envelope
    max 0.634 vs 0.8 ceiling, band gains ≤ 1;
  - keyboard plays all six voices at master morph 0, 0.5 and 1 without
    exception; all setters (tempo/breath/space/volume/fader/voice morph)
    execute;
  - chorus at morph 0: every voice sang exactly one performance
    (owl 4, towhee 10, wren 9, sparrow 15, cardinal 10, heron 10 notes) and
    the cycle ended on its own; at master morph 1 the chorus loops and STOP
    ends it; after STOP, zero further notes are scheduled;
  - the plan builders' transition fallback was never used (guardHits = 0).
  - (Note counts vary slightly run to run — the grammars draw measured
    ranges at random, as designed.)

## Limitations — stated plainly

- **Not ear- or eye-verified.** No headless audio or rendering here: the
  claims are code fidelity, audits, and harness behavior. Whether it sounds
  like the birds and whether the birds-on-a-wire animation reads well on a
  real screen is Jimmy's gate in the morning.
- Animation timing is setTimeout aligned to the audio clock (schedule-time
  callbacks, per the spec), so visual onset can jitter by a few ms against
  the audio — inaudible/near-invisible in practice, but it is not
  sample-locked.
- Design choices made at bank level (documented above, not measurements):
  the morph composition formula, chorus order/staggers, tempo rescaling of
  the grid, the keyboard's transposition pin (lead template's first contour
  point) and one-shot (non-sustaining) key envelopes, the synth crossfade
  layer, the unified master compressor (wren/towhee/sparrow lab pages used
  a harder −12 dB / ratio-20 master stage; the bank standardizes on
  −18 dB / ratio 6), and channel default faders (owl 0.90, heron 0.85,
  others 0.80).
- The heron's keyboard mode reuses the M (croak) profile with the key pitch
  as its tonal core — the only pitched handle the measurements support.
- STOP stops scheduled sources immediately; a note in its last ~50 ms tail
  may still be faintly audible as its sources stop — no fade-out ramp is
  applied to note gains on stop.

---

# Swap — Hermit Thrush replaces Great Blue Heron (2026-11-12)

Jimmy's ear-gate on the delivered bank: five birds passed first pass; the Great
Blue Heron "doesn't sound like a bird" and is out of the bank. The Hermit Thrush
(lab page built and verified the same morning; source XC1048898, AUDEVARD
Aurélien) takes its slot. heron.html stays on disk untouched as a standalone
experiment; nothing else about the bank's design changed.

## What changed in syrinx6.html

- **Voice engine removed:** MEAS_HERON, HERON_PEAK_CAP / HERON_BAND_CENTERS /
  HERON_BAND_Q, makeHeronPlan (+ its period helpers), buildHeron (the 6-band
  noise chain), heronPlay, the keyNote heron special case, and every
  noiseEnv / noiseTrim / noiseBusy remnant (stopAll, BREATH knob, SYRINX
  setBreath). The bank now has exactly one audio builder (buildTonal) and one
  breath path shape for all six voices.
- **Voice engine added:** MEAS_THRUSH is the lab page's MEAS literal copied
  verbatim (7 types W/S/U/D/C/u/d, transitions, songPause, the 8 measured song
  forms with per-note freqScale, the pitch ladder). New renderer `thrushPlay`
  is a faithful port of the lab's playNote onto bank infrastructure:
  peak = peakRel × 0.6 (THRUSH_GAIN_SCALE), freqScale from the plan event,
  grid-side durations rescaled by the bank's TEMPO gridScale (the other five
  voices' convention), pan ±0.18 by measured type voice, harm2 always and
  harm3 when measured (all thrush types measure harm3 = 0, so none fires),
  the lab's saw + FM synth layer at m > 0.02, and the measured tremolo: an LFO
  at the type's tremRate driving a series gain in the note's own chain, depth
  tremDepth × (1 − morph) — parameter automation on the note's own nodes only,
  never the breath path; the LFO is regSrc'd so STOP stops it. Breath rides
  the single fixed per-voice path with the standard capped curve
  (≤ 0.05 × note peak, endpoints 0).
- **Grammar:** makeThrushPlan picks one of the 8 measured song forms verbatim
  (per-note freqScale rides each event), offsets accumulate sampled measured
  transitions bird-side / grid periods grid-side (bank planFromSeq guard
  convention: a missing transition would count a guardHit and fall back — all
  14 form transitions are measured, and the harness confirms guardHits = 0).
  Pause between songs: measured songPause [1.391, 4.271, 5.979] s; grid pause
  4.286 s.
- **Strip:** slot 3 (the heron's old position) — HERMIT THRUSH / Catharus
  guttatus, fader default 0.85 (carried from the slot; the owl keeps 0.9, the
  rest 0.8), morph knob, LED, SING, beak throw 10°. Keyboard lead = W (the
  type the measurements name "Lead whistle") through the bank's generic
  keyboard path — unlike the heron, the thrush is a tonal voice, so keys play
  its real lead template with the bank's freqScale-from-key-pitch rule.
- **Screen:** bird-heron SVG replaced by bird-thrush at the same wire position
  (330,190), same flat style and rig (.bob / .head / beak-lo / .throat driven
  by the same per-note callbacks): warm brown upperparts (#7a4e2d body, #5d3a1f
  wing), rufous tail (#a05a2c — the species' field mark), cream breast patch
  with five dark spots grouped in .throat so the spots pulse with it, white
  eye-ring, dark upper bill with pale lower mandible, pinkish legs (#b98a6d),
  tilt −3°.
- **Chorus:** [['owl',0],['towhee',2.5],['wren',5],['sparrow',7.5],
  ['cardinal',10.5],['thrush',13.0]] — the thrush takes the heron's finale
  slot and stagger; the conductor comment now names the thrush's ladder
  finale. End/loop logic untouched.
- **Attribution:** heron credit (XC698523, Thomas G. Graves) replaced by
  "Hermit Thrush — XC1048898, AUDEVARD Aurélien, CC BY-NC-SA 4.0". A
  case-insensitive grep for "heron" over the whole file returns zero hits
  (asserted in the audit).

## Verification (suite extended in place)

- `node --check` on the extracted script: clean.
- **Audit (verify_syrinx6_audit.js): 60 checks, 0 failures.**
  - DOM: 30 ids (24 getElementById literals + 6 bird ids incl. bird-thrush).
  - Bank vs lab pages (exact, tol 0): cardinal 200, owl 188, **thrush 414**,
    wren 224, sparrow 556, towhee 187 numeric leaves — 0 mismatches.
  - Bank vs measurements JSONs: cardinal 167+3, owl 160, wren 193, sparrow
    492, towhee 156+15 — unchanged, 0 mismatches. **Thrush vs
    hermit-thrush-measurements.json: 412 values, 0 mismatches, maxDev
    0.0005** (types incl. contour/amp templates, dur/f/harm2/harm3/peakRel/
    voice/gridDur/n, tremRate and tremDepth = 0.45 × measured depth index,
    all 14 transitions incl. grid periods, songPause triple, gridSongPause,
    the 8-rung ladder, and all 8 song forms' type sequences + freqScales
    re-derived as f_med ÷ type-template-base).
  - Pre/post swap identity: the five unchanged voices' MEAS literals are
    byte-identical to a snapshot of the pre-swap bank taken before editing.
  - Static breath audit: `disconnect` ×0 in the file; createBufferSource
    builder sites = 1 (buildTonal; runtime instance count 6 asserted by the
    harness); breathEnv.connect / breathTrim.connect = 1 each, inside the
    builder only; noiseEnv / noiseTrim sites = 0; no renderer
    (tonalPlay / thrushPlay / synthNote) wires anything on the breath path;
    breath envelope writers = 2 (tonalPlay + thrushPlay), noise writers = 0;
    thrushPlay tremolo block statically present (tremRate/tremDepth,
    LFO-gain → tg.gain, LFO regSrc'd).
- **Harness (verify_syrinx6_harness.js): 70 checks, 0 failures; 448 notes
  scheduled across the run.**
  - Init builds exactly 6 runtime noise buffer sources (one per voice).
  - Per-voice Sing (35 s each): notes == animation callbacks for every voice
    (cardinal 39, owl 8, **thrush 27**, wren 80, sparrow 63, towhee 61).
  - **Thrush tremolo observed at runtime:** during its Sing at morph 0, the
    fake graph recorded oscillator → gain → gain-param wiring (the LFO chain)
    — the harness now logs connections to make this assertable.
  - Breath caps respected for all six voices; thrush max breath curve
    0.01094 vs cap 0.01251.
  - Keyboard plays every voice incl. the thrush at master morph 0 / 0.5 / 1.
  - Chorus at morph 0: all six sang (thrush 7 notes in the finale slot) and
    the cycle self-ended; at morph 1 the chorus was still looping at 6 s and
    STOP ended it; STOP freezes scheduling; guardHits = 0.

## SONG MODE — the library, and the Minuet in G (2026-11-12)

A SONG section now sits between the master row and the channel strips:
a **FREE PLAY / SONG** toggle, a song picker (the library), **PLAY
SONG / STOP**, a meta line, and a progress readout (current part, bar,
and which bird is singing). FREE PLAY is the bank exactly as before.
In SONG mode the strip SING buttons, the CHORUS button, and the
keyboard are inert — dimmed in CSS and blocked in code, inside
`setSing` / `startChorus` / `keyNote` themselves, so the SYRINX API is
gated the same way as the buttons. In FREE PLAY the song transport is
inert (`startSong` returns unless the mode is SONG). Switching modes
stops everything. **MORPH, TEMPO, SPACE, VOLUME and the per-voice
controls stay live in song mode**: song notes render through the
keyboard path itself (below), so the master MORPH knob sweeps a
playing song from birdsong to synth, and TEMPO rescales the song's
beat by the bank's gridScale convention — at the default 112 the
song's own ♩ = 120 stands as written. STOP (either STOP button, or
`SYRINX.stopAll`) halts the song scheduler and everything else.

### The library is data

`SONGS` is an array of song objects — `{id, title, subtitle, credit,
bpm, beatsPerBar, registers, sections, fills, form}`. Scores are
phrase strings of `NAME:beats` tokens (`"D5:1 G4:0.5 A4:0.5 ..."`)
compiled at load by `compileSong` into beat-stamped events; the
`form` array lays sections out in performance order and tags each
4-bar phrase with the voice that sings it in that pass. A `fill` form
entry reserves a one-beat slot at a section joint for an ornament.
Adding a second song later is purely additive data: one more object,
no new code. `SYRINX.songs` lists the library; `SYRINX.songEvents(id)`
exposes the compiled events the audits run against.

### Demo song — Minuet in G major, BWV Anh. 114 (Christian Petzold)

The piece is the famous "Bach minuet" from the *Notebook for Anna
Magdalena Bach* (1725); it was composed by **Christian Petzold**, and
the UI and this doc credit it exactly that way.

**Score source.** The encoding was NOT written from memory. It was
transcribed from the public-domain typeset by **Allen Garvin**
(Mutopia Project, Mutopia-2017/01/19-75; LilyPond, sourced from the
Bach-Gesellschaft edition; the typeset's own header places it in the
public domain), as listed in the Scores section of the IMSLP work
page. Both source files are saved in `analysis/score-src/`
(`anna-magdalena-04.ly`, `anna-magdalena-04.mid`), and the
machine-readable transcription parsed from the typeset's own MIDI
render — every note cross-checked against the LilyPond source text
bar by bar — is `analysis/minuet_bwv_anh114_transcription.json`
(source URLs recorded inside it). URLs:
IMSLP work page — https://imslp.org/wiki/Minuet_in_G_major,_BWV_Anh.114_(Pezold,_Christian) ·
LilyPond — https://www.mutopiaproject.org/ftp/BachJS/BWVAnh114/anna-magdalena-04/anna-magdalena-04.ly ·
MIDI — https://www.mutopiaproject.org/ftp/BachJS/BWVAnh114/anna-magdalena-04/anna-magdalena-04.mid

**Ornament accounting (the only deviations, all recorded in the
transcription's `ornamentsNotEncoded`):** the bar-8 grace note (B4,
which the source MIDI realizes by stealing 0.112 beats from bar 7's
final G4) is not encoded as a melody note, and bar 7's G4 keeps its
written 0.5 beats; the mordents (bars 3, 5, 11, 13) and the prall
(bar 30) are articulation symbols, not pitched events; the treble
staff's final cadence chord tones (B3, D4 under bar 32's G4) are
accompaniment, not melody. Every other pitched note of both staves
is accounted for.

**Arrangement.** A section with its repeat, then B once, ♩ = 120 in
3/4 — 146 beats including the two one-beat fill slots, about 73 s at
tempo. The melody rotates by 4-bar phrases; no voice sings twice in a
row, including across the joints:

| Pass | Bars | Voice |
|---|---|---|
| A | 1–4 | cardinal |
| A | 5–8 | song sparrow |
| A | 9–12 | hermit thrush |
| A | 13–16 | eastern towhee |
| — | fill at the repeat joint | song sparrow |
| A (repeat) | 1–4 | Carolina wren |
| A (repeat) | 5–8 | cardinal |
| A (repeat) | 9–12 | song sparrow |
| A (repeat) | 13–16 | eastern towhee |
| B | 17–20 | cardinal |
| B | 21–24 | hermit thrush |
| — | fill at the midpoint cadence | Carolina wren |
| B | 25–28 | Carolina wren |
| B | 29–32 | eastern towhee |

Phrase counts: cardinal 3, towhee 3, sparrow 2, thrush 2, wren 2 —
all 190 performed melody notes (A = 64, sung twice; B = 62).

**Register offsets** (constant per voice; rendered pitch = written
pitch × offset, so every interval inside a phrase is exact):

| Voice | Offset | Rendered melody range |
|---|---|---|
| cardinal | ×4 (+2 octaves) | 1,480–3,951 Hz |
| hermit thrush | ×5 | 1,960–3,920 Hz |
| Carolina wren | ×5 | 1,850–3,920 Hz |
| song sparrow | ×6 | 2,220–4,704 Hz |
| eastern towhee | ×8 (+3 octaves) | 2,349–4,699 Hz |

The written melody spans D4–B5 (293–988 Hz); each offset parks its
phrases in the voice's measured band, with the low pedal notes of the
quiet A-strain phrases dipping modestly below a voice's core band
(e.g. the cardinal's repeated-phrase G4s at 1,480 Hz) — stated here
rather than hidden by a non-constant offset.

**Bass — the owl.** One note per bar on beat 1: the score bass
staff's first note of the bar (bar 1 takes the opening chord's root,
G3), at written pitch (×1) — except that any note below 190 Hz is
raised one octave, pitch class unchanged, so every hoot sits in the
owl's band. The folds are bars 18 (F#3→F#4), 19 (E3→E4), 29
(D3→D4), 30 (E3→E4). Rendered bass range 196–370 Hz, 48 notes. The
hoot is the owl's lead template (P3) at template duration — a
grounded pulse per bar, per the arrangement's floor.

**Fills (exactly two, never over the melody).** Each occupies its own
inserted one-beat slot between sections, so no melody note sounds
under it. Fill 1 (repeat joint): the song sparrow's measured figure
material — types L h M L h M spaced by its measured transition
periods (L→h 0.082 s, h→M 0.055 s, M→L 0.096 s, stated in beats at
the song's 0.5 s beat). Fill 2 (B midpoint, after bar 24's cadence):
the Carolina wren's fast chip types S U D S U at 80 ms spacing. Fill
notes render at their templates' natural pitches.

**How song notes render — and how that differs from the keyboard.**
Each song note calls the voice's own engine exactly as `keyNote`
does: `v.play(lead, when, {dur: template durMed, freqScale:
targetFreq / template start, gainScale: 1 − morph})`, plus the
saw/square `synthNote` layer at the same target pitch when morph >
0.01. The thrush's tremolo, every voice's contour, breath curve, and
the morph's log-lerp toward the A-major pentatonic grid all come
along unchanged — the song is played BY the keyboard path, not by a
second renderer. The differences are in scheduling only: (1) a 30 ms
lookahead scheduler (0.35 s horizon, the voiceTick pattern) instead
of one immediate note per tap, so TEMPO and MORPH changes land live
mid-song; (2) onsets are score-exact, but note *bodies* keep the bank
law — template duration, morph-lerped toward the grid — rather than
the written note length, the same law the chorus sings by (a written
half note and an eighth at the same pitch differ in when the NEXT
note falls, not in body length); (3) the progress readout is driven
by epoch-guarded timeouts aligned to note times, the wireScreen
pattern, and the birds on the wire animate from the same per-note
callbacks the chorus uses, because `fireNote` fires inside the play
functions themselves. Audio law untouched: one capped breath path
per voice, gain envelopes only, no per-note wiring changes, master
compressor ceiling.

### Verification (2026-11-12, all in `analysis/`)

- **Syntax:** extracted page script passes `node --check`.
- **Free-play regression — unchanged:** `verify_syrinx6_audit.js`
  **63 checks, 0 failures** (bank↔lab 0 mismatches on all six voices;
  bank↔JSON 0 mismatches; static breath-path audit clean) and
  `verify_syrinx6_harness.js` **70 checks, 0 failures** — the suite
  file itself was not modified.
- **Score audit (`verify_song_score.js`): 26 checks, 0 failures.**
  All 190 performed melody notes match the transcription exactly
  (pitch, duration, onset, bar, register-scaled frequency); phrase
  rotation matches the arrangement map; the 48 owl bass notes land on
  bar starts with the source's pitch class in every bar and the fold
  rule where applied; fills occur exactly twice, in their slots, with
  the measured material; total performance length 146 beats.
- **Song harness (`verify_song_harness.js`, sharing the stub loader
  in `stub_loader.js`): 64 checks, 0 failures.** PLAY blocked in free
  play; SING/CHORUS/keyboard blocked in song mode via API and real
  button listeners; progress readout verified verbatim mid-song
  ("A · bar 2 — CARDINAL sings"); STOP mid-song and a mid-song mode
  switch both leave nothing scheduled; full renders at master morph
  0 / 0.5 / 1 each schedule the full 249 events (190 melody + 48 bass
  + 11 fill) with exactly one animation callback per note and all six
  voices heard; breath caps respected for every voice throughout.

Whether it *sounds* like six birds performing Petzold is, as with
every voice in this bank, Jimmy's ear-gate — nothing above claims
otherwise.

## FULLNESS — harmony, bass movement, body, width + room (2026-11-12)

A master **FULLNESS** knob joins the master knob grid. It is one knob
driving four layers that fade in together, each scaled by the knob
value F:

- **F = 0 is the pre-FULLNESS bank, exactly.** Same song events render
  (249), no body sources are created, the room wet gain is exactly 0,
  and every other layer gain is 0 or the layer event is skipped whole.
  This is the A/B baseline and the regression anchor (asserted in the
  song harness, below).
- The knob defaults to 0. The **first** time SONG mode is entered, if
  the user has never touched the knob (pointer/wheel on it, or the
  API), it is set to **0.5** — the demo default Jimmy approved — so the
  demo song arrives full. After that it is the user's; free play never
  moves it, and re-entering song mode does not re-apply the default.

### Layer 1 — HARMONY (song mode only)

A second bird sings chord tones under the melody: the chord's **third
on beat 2, its fifth on beat 3** of every bar, at gain
**0.35 × F × (1 − morph)** against the melody's own (1 − morph) — always
under the tune. No harmony in the two fill slots (the slots sit outside
the bars). Harmony notes are ordinary `v.play` renders through the
singing voice's own engine, so they fire the same per-note animation
callbacks — the harmony bird visibly sings on the wire. The progress
readout still tracks the melody line only.

**Voices.** A fixed pool — towhee, sparrow, wren — rotates phrase by
phrase; the compiler skips the phrase's own melody singer, so the
harmony voice never equals the melody voice in the same phrase, and
the owl never harmonizes. As compiled for the Minuet (32 notes each):

| Pass | Bars | Melody | Harmony |
|---|---|---|---|
| A | 1–4 | cardinal | towhee |
| A | 5–8 | sparrow | wren |
| A | 9–12 | thrush | towhee |
| A | 13–16 | towhee | sparrow |
| A (repeat) | 1–4 | wren | towhee |
| A (repeat) | 5–8 | cardinal | sparrow |
| A (repeat) | 9–12 | sparrow | wren |
| A (repeat) | 13–16 | towhee | sparrow |
| B | 17–20 | cardinal | wren |
| B | 21–24 | thrush | towhee |
| B | 25–28 | wren | sparrow |
| B | 29–32 | towhee | wren |

**Register.** Each harmony tone renders at **half the voice's melody
register multiplier** (cardinal ×2, thrush ×2.5, wren ×2.5, sparrow ×3,
towhee ×4) — one octave below where that voice sings the tune, constant
per voice, so the third→fifth pattern's interval is exact. Rendered
harmony spans ≈ 494–1,976 Hz, below every melody phrase and above the
owl's bass.

**The chords are data.** `song.chords` carries one chord name per bar
per section; `CHORD_TONES` (engine-level) spells each chord's third and
fifth (G: B3/D4 · C: E4/G4 · D: F#4/A4 · Em: G4/B4 · Am: C4/E4 ·
A: C#4/E4). `compileSong` compiles harmony events only when the song
defines `chords` — a future song brings its own chart, no new code.

**Derivation of the Minuet chart** — from the source score itself
(`analysis/score-src/anna-magdalena-04.ly`, the same Garvin/Mutopia
typeset the score audit runs on; bass = its lower staff, melody = its
upper staff). Rule: the chord in force **on beats 2–3**, where the
harmony voice sings, read from the bass notes sounding there against
the melody notes sounding there.

| Bar | Bass (source) | Melody evidence | Chord |
|---|---|---|---|
| 1 | G (with B–D chord above), A passing | D, G, B, C over G | **G** |
| 2 | B whole bar | D G G — B is G's third | **G** |
| 3 | C whole bar | E, C chord tones; F# passing | **C** |
| 4 | B whole bar | G — B is G's third | **G** |
| 5 | A whole bar | C = the minor third over A | **Am** |
| 6 | G whole bar | B C B A G | **G** |
| 7 | D (beat 1), B, G | beat 1 is D major (F# = its third) resolving to G for beats 2–3 | **G** |
| 8 | D whole bar (+ C B A descent) | A = D's fifth, whole bar | **D** |
| 9 | B, A | = bar 1 line; B is G's third | **G** |
| 10 | G B G | D G G | **G** |
| 11 | C whole bar | = bar 3 line | **C** |
| 12 | B, then C B A G run | G; B is G's third | **G** |
| 13 | A, F# passing | = bar 5 line | **Am** |
| 14 | G, B | = bar 6 line | **G** |
| 15 | C passing, then D D | A B A G F# over a D pedal = D's 5–6–5–4(sus)–3 | **D** |
| 16 | G G | G whole bar | **G** |
| 17 | G whole bar | B G A B G (B = third) | **G** |
| 18 | F# whole bar | A D E F# D — F# is D's third (first inversion) | **D** |
| 19 | E G E | G = the minor third over E | **Em** |
| 20 | A A | C# = A's major third | **A** |
| 21 | A whole bar (dominant pedal) | scale A–F#; C# (third) and E (fifth) land on beats 2–3 | **A** |
| 22 | B, D, C# (sequence) | F# over D on beat 2 = D's third; the bar is governed by D | **D** |
| 23 | D F# A arpeggio | F# A (third, fifth); C# is the sequence's leading tone | **D** |
| 24 | D D, C# at the end | D whole bar; C# leads into bar 25 | **D** |
| 25 | B whole bar (lower voice), D beats 2–3 | B + D + melody G = G in first inversion | **G** |
| 26 | C whole bar (lower voice) | E (third), G (fifth), F# passing | **C** |
| 27 | B A G descent | D (beat 1, over B = G first inversion) to G root on beat 3; A/C mid-bar is the passing step | **G** |
| 28 | D half note, rest | A on beat 3 = D's fifth; F# in the melody = its third | **D** |
| 29 | D whole bar (lower voice) | ascending D-major scale (D F# A) | **D** |
| 30 | E, G, F# (passing bar) | beat 1 C-color over E; beat 2 G over G; beat 3 resolves as D7 color into bar 31 | **G** |
| 31 | G B D arpeggio | B D G; F# passing to the final bar | **G** |
| 32 | G D G | G + the treble cadence chord tones B3, D4 | **G** |

Chart as data — A: `G G C G Am G G D G G C G Am G D G` ·
B: `G D Em A A D D D G C G D D G G G`.

### Layer 2 — BASS MOVEMENT (song mode only)

The owl answers its own beat-1 hoot on **beat 3** of every bar, at
**0.6 × F × (1 − morph)**: odd bars sing the bar chord's **fifth**,
placed in the octave above the beat-1 note; even bars sing the **root
an octave up**, capped at 500 Hz — where the cap bites (bars 18, 24,
28, 30) the chord fifth answers instead, keeping the hoot in the owl's
band. Same P3 hoot recipe and register rules as the beat-1 bass.
Examples as compiled: bar 1 → D4 294 Hz (fifth), bar 2 → B4 494 Hz
(root 8va), bar 7 → D5 587 Hz (the fifth displaced an octave because
beat 1 already sits on D4), bar 24 → A4 440 Hz (fifth, by the cap).

### Layer 3 — BODY (both modes)

Inside the note builders, so SING, keyboard, chorus and song thicken
identically. At F > 0 each rendered note gains, in its own chain:

- a **detuned double**: a sine tracing the note's own frequency curve
  at **+5 cents**, gain envelope = the note's amp template × peak ×
  **0.25 × F**;
- **harmonic enrichment**: the existing measured 2nd-harmonic layer's
  gain scales by **(1 + F)** — at F = 0 the factor is 1 and no body
  source exists, so the baseline is bit-exact.

The synth layer (`synthNote`, the keyboard/song morph path) gets the
same treatment: a triangle double at **−6 cents** through the same
lowpass, 0.25 × F of the layer's gain, and it now accepts the song
layer's gain factor so harmony/bass-movement synth layers stay under
the melody at high morph too.

**Per-voice difference — the thrush.** Its body double enters at
`head`, *after* the measured tremolo series gain, so the shimmer shapes
the body exactly as it shapes the carrier (the other voices have no
series gain; their doubles enter at the note's pan). It matters most
for the thrush: its measured harm2 is near zero (a near-pure tone), so
the enrichment term does almost nothing for it — the detuned double
carries its thickening.

**The breath path is not touched** — no new breath nodes, no per-note
breath changes; the harness's breath caps at FULLNESS 1 are
numerically identical to the pre-FULLNESS run (below).

### Layer 4 — WIDTH + ROOM (both modes)

- **Width:** each voice chain gains a fixed StereoPanner wired once at
  chain construction (init-time structure), at the bird's wire
  position: cardinal **−0.7**, owl **−0.35**, thrush **−0.12**,
  wren **+0.15**, sparrow **+0.4**, towhee **+0.7**. (The per-note
  ± panAmt sway from the measured two-voice syrinx types is unchanged,
  inside the note chain as before.) The SPACE delay send now taps after
  the pan, so echoes keep the voice's position.
- **Room:** a master-level send — mix bus → generated-impulse
  convolver → wet gain → the compressor input (so the limiter still
  glues the wet signal; the dry path is unchanged). The impulse is
  synthesized in code at init (1.6 s stereo noise, decay ∝ (1−t)^2.6);
  no external files. Wet gain = **F × 0.35**, exactly 0 at F = 0.
  Hosts without a convolver node factory get no room send (guarded) —
  every other layer still applies.

### Event counts (Minuet, as compiled and as rendered)

| FULLNESS | Melody | Bass | Fills | Harmony | Bass movement | Total rendered | Body sources |
|---|---|---|---|---|---|---|---|
| 0 | 190 | 48 | 11 | — (skipped) | — (skipped) | **249** | 0 |
| 0.5 | 190 | 48 | 11 | 96 | 48 | **393** | 393 |
| 1 | 190 | 48 | 11 | 96 | 48 | **393** | 393 |

(Layer events are present in the compiled list at every F — the score
audit's kind-filtered checks are unaffected — but the renderer skips
them whole at F ≤ 0.001. Body sources count one per rendered note at
morph 0; at higher morphs the synth layer adds its own body per note.)

### Verification (2026-11-12, all in `analysis/`)

- **Free-play regression — suites unmodified:** `verify_syrinx6_audit.js`
  **65 checks, 0 failures** (the 63 pre-FULLNESS checks plus 2 new DOM
  checks the audit derives itself for the `knobFull` / `valFull` ids)
  and `verify_syrinx6_harness.js` **70 checks, 0 failures**. The page
  guards its convolver creation, so the free-play harness's stub (no
  convolver factory) runs the bank exactly as before.
- **Score audit — unmodified:** `verify_song_score.js` **26 checks,
  0 failures.** All 190 melody notes, the 48 bass notes, the fills and
  the 146-beat shape are untouched; the new event kinds are outside its
  filters.
- **Song harness — extended in place:** `verify_song_harness.js`
  **124 checks, 0 failures** (the original 64 assertions preserved —
  the baseline renders now run with FULLNESS explicitly pinned to 0,
  which is what those assertions always measured — plus 60 new):
  - auto-default: first SONG entry sets the untouched knob to 0.5;
    wet gain exactly 0 at F = 0;
  - compiled layers: 96 harmony + 48 bass-movement events; every
    harmony pitch a member of its bar's chart chord; exactly 2 harmony
    notes in every performed bar and 1 bass-movement note; harmony
    voice never the melody voice, pool rotation uses all three voices;
    harmony at the half-register; no harmony in the fill slots; bass
    movement above the beat-1 note within its octave, as root or fifth;
  - renders at F = 0 / 0.5 / 1: 249 / 393 / 393 notes with one
    animation callback each; body sources 0 at F = 0, one per note
    above; harmony callbacks at gainScale 0.35 × F, bass movement at
    0.6 × F, base events at 1 (harmony gain < melody gain asserted);
    room wet = F × 0.35; progress readout and STOP behavior unchanged,
    including a STOP at F = 1 leaving nothing scheduled;
  - pan positions asserted per voice from the built chains;
  - free play at F = 1: keyboard (all six voices, morph 0 and 1),
    SING and chorus schedule body layers without errors;
  - **breath caps at FULLNESS 1 identical to the pre-FULLNESS run**
    (worst: owl 0.02232 vs cap 0.02300; towhee 0.02220 / 0.03362) — the
    breath path is provably untouched.
- The song suites' shared stub (`stub_loader.js`) gained a
  `createConvolver` fake so the room send is exercisable headlessly;
  the free-play suites were not touched.
- Extracted script passes `node --check`.

Whether FULLNESS at 0.5 actually sounds like a fuller ensemble of
birds — and whether 0.5 is the right demo default — is Jimmy's
ear-gate, as with everything in this bank.

## Known limitations (updated)

- The heron keyboard note from the original build no longer applies — the
  thrush is fully keyboard-playable like the other tonal voices. The other
  original limitations (shared analyser/spectrogram, TEMPO at chorus start,
  STOP tail behavior) stand unchanged.
- The thrush's ear-gate is Jimmy's, as with every voice: this swap is
  verified by constants, graph wiring, and scheduling only. Whether the
  flute phrases and their tremolo read as a hermit thrush is for his ears;
  the SVG likeness is for his eyes.

## SCHEDULER EXCEPTION SAFETY (2026-11-12, after a real-browser report)

**Field report:** on the hosted port, song playback stuck on the first
note — the opening note repeated instead of the sequence advancing. The
hosted page is a separate port, but this file's song scheduler shared
the design, so the canonical file was audited against the failure mode.

**Finding — the flaw was real here.** `songTick()` rendered the pending
event and only THEN advanced the index (`renderSongNote(...)` followed
by `st.idx++`), with no exception guard anywhere in the chain
(`songTick` → `renderSongNote` → `v.play` / `synthNote`). Consequences,
traced end to end:

- If a render throws, the exception escapes the tick; a browser does
  not cancel a `setInterval` for a throwing callback, so the next tick
  (30 ms later) finds the same index, the same event still inside the
  lookahead window, and renders it again — forever. The finish check
  is never reached.
- Where the throw lands decides the symptom: inside `v.play` before
  the oscillators start → a silent freeze (the screen already lit the
  bird, because `fireNote` runs at the top of the play engines);
  after `v.play` returns — e.g. in `synthNote`, which runs whenever
  the effective morph is above 0.01 — the note has fully sounded, so
  the SAME note audibly re-fires every 30 ms. That is the reported
  symptom, note for note.
- The stub graph structurally cannot produce any of these throws:
  its `FakeParam.setValueCurveAtTime` accepts any curve (no finiteness
  validation), and its fake context always provides every node
  constructor. Real hosts differ on both axes — `setValueCurveAtTime`
  throws `NotSupportedError` for non-finite curve values, and
  `createStereoPanner` (called per note, unguarded, in both play
  engines, and once per voice at chain build) is absent on older
  iOS Safari. The convolver, by contrast, was already guarded.
- Proven in the stub by poisoning one voice's `play()` to throw: on
  the pre-fix code the exception propagated straight out of `songTick`
  (stack: play → renderSongNote → songTick) and the song could never
  pass that voice's first event.

**Fix (minimal, scheduler-level).** In `songTick`, the index now
advances BEFORE the render, and the render is wrapped in try/catch:
a note that cannot render in the current host is skipped exactly
once — never repeated, never stalling the sequence — and the progress
readout is only posted for an event that actually rendered. In a
non-throwing host the behavior is bit-identical: same events, same
onsets, same gains.

**Audited and found sound (no change):** time semantics — advancement
is index-based against `actx.currentTime`, so a suspended/interrupted
context freezes both clock and scheduler together and playback resumes
on the right beat, with past onsets clamped; no `visibilitychange`
handling is needed for correctness. Re-entrancy — `startSong` early-
returns while a song is live, and `stopAll()` (called by every mode
switch) runs `stopSong()`, so double PLAY taps and mode flip-flops
cannot stack schedulers. (Observation, left as-is: `voiceTick` advances
its index after `v.play` in the same pattern; SING was outside this
fix's scope.)

**Verification:** all suites pass — free-play audit 65/65 and harness
70/70 (unmodified), score audit 26/26 (unmodified), song harness
extended 124 → 134 with a new poison-render case: with the sparrow's
`play()` throwing on all 38 of its events, the song completes, each
poisoned event is attempted exactly once, and the other five voices'
callback counts are exact (211 = 249 − 38). No sound claims — this
section is about the sequence never being able to stick again.
