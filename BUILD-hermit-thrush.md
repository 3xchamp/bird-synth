# Bird-synth engine — Hermit Thrush build notes

**Deliverable:** `hermit-thrush.html` — one Hermit Thrush in a browser page, the bank
replacement for the Great Blue Heron (which failed Jimmy's ear-gate: "doesn't sound like
a bird"; the other five bank birds passed).
**Status:** built and machine-verified (syntax, constants, generator logic, breath law).
Whether it *sounds* like a hermit thrush is Jimmy's ear-gate, not claimed here.

## Method

1. **Reference.** XC1048898 (Xeno-canto, grade A, AUDEVARD Aurélien, Homer, Kenai
   Peninsula, Alaska, 2022-06-20, CC BY-NC-SA 4.0, background species none) — vetted by
   Mordecai: gap windows ≈ −51.6 dB RMS vs phrase peaks −16.4 dB, nine phrase clusters
   on a near-silent floor. The Wilcox files in the same folder (XC1037508 / XC1037504)
   were **rejected** (broadband striping wall; the bird buried) and were not used.
   No recording audio is used in the page; the synth re-creates measured contours with
   oscillators. The MP3 was decoded to a 48 kHz mono WAV beside it for measurement.
2. **Measurement** (`analysis/measure_hermit_thrush.py`, data in
   `analysis/hermit-thrush-measurements.json`). STFT (1024-pt Hann, 128 hop)
   dominant-peak pitch tracking in 1.3–9.5 kHz; note segmentation on the 1.5–9 kHz band
   Hilbert envelope in two passes — body (−26/−33 dB) plus a sensitive pass
   (−38/−45 dB) whose additions were kept only with median pitch prominence ≥ 8 dB.
   Per note: duration, start/end/median/peak/min frequency, 16-point pitch and amplitude
   templates, 2nd/3rd harmonic ratios, subharmonic ratio. Result: **30 notes, 29
   templated** (one sensitive-pass fragment at 0.16 s has an unreliable contour and is
   recorded as an observation, not templated), typed by stated contour×duration rules
   into W / S / U / D / C / u / d, grouped into **8 songs** at gaps > 1.2 s.
3. **Model.** Same family engine as the Song Sparrow page: each phrase type renders
   from its median measured contour + amplitude templates; Sing replays the eight
   measured song forms verbatim, each note transposed by its own measured frequency
   ratio (see the ladder below); the Bird⇄Electronic slider interpolates pitch, timing
   and timbre continuously.

## Measured phrase table (XC1048898)

| Type | Name | n | Duration s, med (range) | Start → End Hz | 2nd harm. | 3rd harm. | Shimmer rate |
|---|---|---|---|---|---|---|---|
| W | Lead whistle | 3 | 0.279 (0.182–0.455) | 4359 → 4359 | 0.001 | 0.000 | 16.0 Hz (n=2) |
| S | Sustained flute | 7 | 0.362 (0.303–0.519) | 3586 → 3445 | 0.001 | 0.000 | 10.3 Hz |
| U | Up-slur flute | 4 | 0.423 (0.270–0.592) | 3281 → 3773 | 0.002 | 0.000 | 14.4 Hz |
| D | Down-slur flute | 5 | 0.459 (0.306–0.978) | 3844 → 2859 | 0.002 | 0.000 | 9.8 Hz |
| C | Chip | 5 | 0.045 (0.036–0.074) | 5977 → 5953 | 0.000 | 0.000 | — |
| u | Short up-chirp | 3 | 0.110 (0.095–0.128) | 3703 → 4359 | 0.002 | 0.000 | — |
| d | Short down-chirp | 2 | 0.089 (0.082–0.096) | 3258 → 2707 | 0.004 | 0.000 | — |

Two findings against expectation, reported as measured:

- **The harmonics are essentially absent at the tracked tone's multiples** (2nd ≤ 0.004,
  3rd ≈ 0.000 across all types). Frame spectra do show companion partials beside the
  dominant swept tone, but they sit at *inharmonic* offsets (~500 Hz spacing — plausibly
  a second syrinx voice), not at 2×/3×. A single-oscillator-plus-harmonics model cannot
  reproduce them; the page renders the measured ratios (≈ pure swept tones) and this is
  a stated limitation, not a silent smoothing.
- **The shimmer is real and strong.** Every sustained note (dur ≥ 0.25 s, n = 18) carries
  periodic amplitude modulation: envelope FFT peaks at 8.2–21.5 Hz (median 11.1 Hz,
  6–12 dB spectral prominence), envelope depth index (p95−p5)/(p95+p5) 0.59–0.93,
  median 0.80. The phrase notes are pulsed, not steady. The page renders the shimmer as
  a gain LFO in each sustained note's own chain at the per-type median rate, depth =
  0.45 × the measured index (a design scaling: the raw index also absorbs each note's
  attack/decay shape, so it overstates pure AM depth).

**Song forms (measured, replayed verbatim):** `C C S u d u d` · `C u D C U S` · `W U` ·
`D` · `U S D` · `C S S S D` · `W U S` · `W D`. Inter-song pauses 1.39–5.98 s
(median 4.27). Only songs 3, 7 and 8 (index 2, 6, 7) open with a distinct flat lead
whistle (W); song 1's quiet intro complex (~0.3–1.05 s, 15–20 dB below its phrase)
fragmented at segmentation thresholds and is documented as faint material, not typed.

## The pitch ladder (the species grammar that had to be captured)

Base frequency per song = median of its sustained notes' median frequencies, in
performance order:

| Song | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| Base Hz | 3234 | 2766 | 3797 | 4172 | 3750 | 3539 | 3727 | 3867 |
| Ratio to median base | 0.865 | 0.740 | 1.016 | 1.116 | 1.003 | 0.947 | 0.997 | 1.035 |
| Semitones | −2.51 | −5.22 | +0.27 | +1.90 | +0.05 | −0.95 | −0.05 | +0.59 |

Successive levels follow no staircase — each song simply sits at its own height, from
−5.2 to +1.9 semitones around the median base (3738 Hz). Implementation: every note in
every stored form carries `freqScale = its measured f_med / its type template's base`,
so replaying a form reproduces that song's level exactly, note by note. The generator
tests prove no plan ever invents a level (see verification).

## Contamination scan (Jimmy's requirement)

Short-time RMS in 0.25 s windows over the 60–500 Hz band and the full band; a swell =
1 s-smoothed level > file median + 7 dB sustained ≥ 1.5 s. **Result: none found.** The
low band sits at a flat −48.0 dB baseline for all 41.9 s with zero spans above
threshold. The five broadband swells (0.75–2.25, 4.75–7.0, 26.25–29.0, 34.25–35.75,
38.75–40.5 s) coincide with song clusters while the low band stays at baseline through
them — the bird's own energy (the three quieter songs don't cross the broadband
threshold). No span excluded; zero notes contaminated. Faint LF wisps at ~21.5, 29.6,
31.3, 32.3, 36.5, 37.5 s are spectrally dominated by 0.8–1.4 kHz content (mic/wind
floor wobble), never cross the swell threshold, and produced no pitch-prominent
segments.

## The breath (the v1 failure law)

- ONE fixed path, connected once at init: noise → bandpass (2400 Hz, Q 0.7) →
  **breathGain** → master.
- Breath is shaped ONLY by that single gain's per-note envelope (`setValueCurveAtTime`
  in `playNote`), curve = note amp template × note peak × **0.05**, endpoints forced to
  exactly 0 — fully closed between notes and through every pause.
- No node is created, connected or disconnected per note for breath. (The tremolo LFO
  lives in each note's own gain chain — per-note oscillators are the family norm; it
  never touches the breath path.)
- Master chain: gain 0.9 → DynamicsCompressor (−18 dB, ratio 6) → analyser →
  destination, the hard ceiling.

## The morph (Bird ⇄ Electronic), m ∈ [0, 1]

Identical family semantics: pitch log-lerps toward the A-major-pentatonic grid; timing
interpolates from measured transition periods to the 112 BPM grid (32nd-note rounding,
stated per value in the JSON); timbre fades in a saw layer (×0.30·m) and FM
(×1.5·m of f0), breath falls to 0.4× and the shimmer depth fades with (1−m); at
m ≥ 0.5 the first generated song form is cached and loops.

## Verification performed

`analysis/verify_hermit.js` (reproducible): **300 checks, 0 failures.**

- `node --check` on the extracted page script: **pass** (before and after final edits).
- **Constant audit: 263 checks** — every value in the page's MEAS block traced to
  `hermit-thrush-measurements.json` or to a stated derivation rule: per type — name, n,
  duration med/min/max, start/end Hz, harm2, harm3, peakRel, voice, gridDur (32nd-note
  rule, recomputed), contour + amplitude templates, tremRate, tremDepth (0.45× index
  rule); all 14 transition min/med/max + grid values; song-pause triple and grid pause;
  all 8 forms (type sequences **and** every note's freqScale, recomputed as
  f_med / template base with the numpy-median convention); the ladder array; trace
  landmarks. (The audit initially failed 21 freqScale comparisons because the
  verifier's first template-base used an upper-median instead of the numpy median —
  a verifier bug, fixed and re-run; the page never changed.)
- **Static breath-path audit: 12 checks** — on comment-stripped code: `noiseSrc.connect(`
  ×1, `nf.connect(breathGain)` ×1, `breathGain.connect(` ×1, `disconnect(` ×**0** in the
  whole script, `breathBus` ×0, breath-gain shaping site ×1, `breathGain.gain` touched
  in exactly 2 places, BREATH_REL = 0.05 present, endpoints-forced-to-0 pattern present,
  compressor present and wired master → comp → analyser.
- **Generator tests:** 2000 plans from the page's own `makeSongPlan` — every type
  sequence is one of the 8 measured forms, every note's freqScale equals its measured
  form scale exactly (the ladder is reproduced, never invented), every song span inside
  the measured transition+duration envelope; all 8 forms occurred.
- **Functional harness** (stub Web Audio graph, the page's real Sing engine, 480 s of
  fake time): 90 songs / 313 notes scheduled; breath chain identified in the connection
  log as bufsrc → filter → gain with in/out degree 1/1; **exactly one breath curve per
  note**; every curve starts and ends at exactly 0; no curve exceeds its note cap
  (type peak × 0.6 × 0.05); max breath observed **0.0109** vs global cap 0.0125; breath
  exactly 0 at all 89 inter-song pause midpoints; zero `disconnect()` calls; every
  scheduled note identified as a measured (type, ladder-scale) pair; every generated
  song size is a measured form size. Morph semantics re-verified (identity at 0,
  log-lerp midpoint at 0.5, full pentatonic snap at 1).
- Not verified: the sound itself. No headless browser/audio on this VM — the ear-gate
  is Jimmy's, by design.

## Known limitations and simplifications

- **Song count: 8 measured, 9 counted on the spectrogram in SOURCES.md.** The stated
  segmentation (gap rule > 1.2 s) resolves eight groups; the ninth spectrogram cluster
  is song 1's quiet intro complex, which belongs to song 1 by the gap rule. The
  generator uses the eight measured forms.
- **Inharmonic partials are not modeled** (see the phrase-table finding): real phrases
  carry companion partials at non-multiple offsets; the synth renders the dominant
  swept tone + measured (≈0) harmonics + shimmer + breath. If the ear-gate finds the
  result thin, this is the first place to look — a second-voice partial would be new
  modeling, not a parameter tweak, and would need its own measurement pass.
- Templates are medians of median-filtered peak tracks; the 46.9 Hz STFT bin size
  quantizes every contour point, and fast sweep detail below ~5 ms is smoothed.
  Sweeping notes make the dominant-peak track hop between partials at note edges;
  medians absorb most of it, but individual contour points can sit on a companion
  partial for a frame or two.
- Song 4 is a single note and song 3 a single falling flute — those forms rest on one
  performance each, as do all eight forms (n = 1 performance per form; the file holds
  one 42 s bout of singing). Form choice in the generator is uniform over the eight.
- `peak_amp_rel` for the two faint song-1 chips (0.025 / 0.053) is far below the C
  type's median (0.075 is itself the quietest type median); the form replays them at
  the type median gain, so the page's song 1 opens slightly louder than the recording's
  whisper. Recorded here rather than special-cased.
- Design choices that are **not** measurements: resonance frequencies/gains, breath
  level (0.05 law aside), stereo pans (assigned by type height), GAIN_SCALE 0.6, the
  tremolo depth scaling (0.45×), the 112 BPM grid, the A-major-pentatonic target
  scale, saw/FM amounts, and the morph's loop-lock threshold.
- Dialect: the model is one Alaska bird on one June morning. Nothing here speaks for
  the Maryland hermit thrushes of November.
