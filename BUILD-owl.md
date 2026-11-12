# Bird-synth engine — Great Horned Owl build notes (bank bird #2)

**Deliverable:** `owl.html` — one Great Horned Owl in a browser page, same engine and
page architecture as the cardinal build.
**Status:** built and machine-verified (syntax, constants, generator logic, breath-path
audit). Whether it *sounds* like a Great Horned Owl is Jimmy's ear-gate, not claimed here.

## Method

1. **Reference.** XC11638 (Xeno-canto, grade A, Nathan Pieplow, Boulder CO, 2007-03-16
   05:30, CC BY-NC-ND 2.5, no background species) — Jimmy's pick. No recording audio is
   used in the page; the synth re-creates measured contours with oscillators. The ND
   license is treated as in the rest of the engine: measurements only, attribution in
   the page, nothing redistributed.
2. **Measurement** (`analysis/measure_owl.py`, data in
   `analysis/great-horned-owl-measurements.json`). Owl retune of the v1 pipeline:
   STFT (4096-pt Hann, 256 hop → 10.8 Hz bins, 5.8 ms steps) dominant-peak pitch track
   in 150–900 Hz; hoot segmentation on the 150–900 Hz band Hilbert envelope.
   **Threshold adaptation, measured not guessed:** this file's in-band floor sits high
   (envelope median −30 dB, p95 −25 dB between series — broad low-frequency night noise
   wandering 200–290 Hz) while hoot peaks reach p95 −2 dB. The v1 cardinal thresholds
   (−24/−31 dB) lie inside that floor and never close: the first pass fused the entire
   file into a single 35 s "hoot" tracking the noise at 248 Hz. Final thresholds:
   onset −12 / offset −17 dB (body), −16/−21 (sensitive pass, which added nothing).
   Within each hoot, pitch/harmonic statistics use only frames with band envelope
   ≥ −22 dB so edge frames don't track the floor noise.
3. **Result:** exactly **8 hoots — two series of four**, matching the vetting (series at
   1.1–3.7 s and 31.1–33.7 s). The two performances are near-identical: per-position
   durations agree within 5 ms, transition periods within 3 ms.

## Measured hoot table (per series position; n = 2 each)

| Pos | Duration s, med (range) | f start → end Hz | f med Hz | Peak amp (rel) | 2nd harm. | 3rd harm. |
|---|---|---|---|---|---|---|
| P1 — the knock | 0.144 (0.142–0.147) | 323 → 318 | 323 | 0.474 | 0.030 | 0.014 |
| P2 | 0.377 (0.375–0.379) | 323 → 323 | 323 | 0.787 | 0.021 | 0.004 |
| P3 — the long one | 0.465 (0.463–0.466) | 323 → 307 | 318 | 0.803 | 0.025 | 0.004 |
| P4 — the closer | 0.397 (0.392–0.402) | 323 → 312 | 323 | 0.891 | 0.019 | 0.004 |

Contours are 16-point median templates (in the measurements JSON and the page). The
fundamental sits on one STFT bin (323.0 Hz) for almost every frame of every hoot; P3
is the only hoot that moves, sagging to ~301 Hz at its tail. Amplitude builds across
the series: the knock is at ~half weight, the closer is the loudest hoot.

**Series grammar (measured):** one form only — P1 P2 P3 P4. Onset-to-onset periods:
P1→P2 0.340 s (0.339–0.342), P2→P3 1.052 s (the long breath; gap 0.675 s),
P3→P4 0.752 s (0.752–0.753). Series span 2.54–2.55 s. Pause between series: 27.465 s,
observed exactly once (n = 1).

**Contamination scan (v2 battery):** 0.25 s-window RMS, 40–500 Hz and broadband.
Baselines −30.8 / −29.8 dB; the only swells (≥ +7 dB sustained ≥ 1.5 s) are
[1.25–4.0 s, +16.7 dB] and [31.25–34.0 s, +17.3 dB] in the low band (broadband nearly
identical) — precisely the two hoot series. For this bird the owl *is* the
low-frequency source; the 27 s between series is flat in both bands.
**Verdict: none found** — no rumble, no unexplained swell, no span excluded.

## How the model maps to the syrinx

- **One voice.** The hoots never overlap and share one pitch; all four positions render
  from a single voice (pan +0.18, the engine's "right" position — design choice;
  nothing in the recording fixes a stereo placement). Per hoot: sine fundamental on
  the measured 16-point contour + 2nd and 3rd harmonic sines at the measured ratios,
  amplitude from the measured 16-point envelope template.
- **Breath / air.** One fixed path, built once at init: looped noise → 650 Hz bandpass
  → a single gain → master. Shaping happens **only** on that gain: per hoot, a curve
  from the hoot's own amplitude template × peak, capped at **BREATH_REL = 0.05** of the
  note's peak gain, endpoints forced to 0 — fully closed between hoots and through
  the 27.5 s pause. No node is created, connected or disconnected per note. This is
  the cardinal-v1 failure designed out (there, a fresh parallel tap per note stacked
  until the noise buried the bird). The breath is deliberately faint: these hoots
  measure as near-pure tone, total harmonic content under ~4.5%.
- **Resonant chain (trachea/beak).** Retuned for this bird: 520 Hz bandpass (Q 0.5) +
  +2.5 dB peaking at 700 Hz + 2.6 kHz lowpass — it sits around the measured
  fundamental and harmonics. The cardinal's 2.5/3.4 kHz chain would have attenuated
  a 323 Hz hoot severely, so the chain follows the bird, as the syrinx would.
- **Master chain** ends in a DynamicsCompressor (threshold −18 dB, ratio 6) as a
  safety limiter, per the engine invariants.

## The morph (Bird ⇄ Electronic), m ∈ [0, 1]

Identical semantics to the cardinal: pitch log-lerps toward the nearest A-major-
pentatonic tone (323 Hz sits ~35 cents flat of E4, a pentatonic tone, so morphing
mostly *tunes* this bird before it transforms it); durations and onset periods
interpolate to the 112 BPM 16th-note grid (gridDur / grid periods derived by the
engine's rounding rule, `analysis/gen_meas_owl.py`); sawtooth layer ×0.30·m through
an opening lowpass and FM deviation ×1.5·m fade in; breath falls to 0.4×; at
m ≥ 0.5 the generated series plan is cached and loops; the series pause interpolates
from the measured 27.465 s to 4.286 s (8 beats). Applied at schedule time — the
slider is live while singing, including mid-pause.

## Verification performed (`analysis/verify_owl.py`)

- Page script extracted → `node --check`: **pass**.
- **Constant cross-check:** every measured value embedded in the page (4 positions ×
  contour + amplitude templates, durations, start/end Hz, 2nd/3rd harmonic ratios,
  instance counts, derived peaks and grid durations; all transition min/med/max and
  grid periods; the series-pause triple) compared programmatically against
  `great-horned-owl-measurements.json`, with peaks and grid values **recomputed from
  the JSON by the documented rules**, not copied from the generator: **188 values,
  all match.**
- **Generator logic tests (node, headless, using the page's own plan function):**
  2000 generated series — every one is exactly P1, P2, P3, P4 in order with strictly
  increasing bird- and grid-side offsets; spans 2.540–2.544 s vs the measured
  2.536/2.549 s performances. Morph is identity at m = 0 (morphFreq(323) = 323) and
  quantize() lands on the A-major-pentatonic set for every template landmark
  frequency (301.5–323 Hz).
- **Static breath-path audit (regex over the final script):** exactly **1** noise
  source creation, **1** `noiseSrc.connect`, **1** `breathGain.connect`, **1**
  DynamicsCompressor; **0** connect/disconnect calls touching the breath chain inside
  `playNote` (its 12 connect calls are the per-hoot voice nodes — pan, gains,
  oscillators — which is the engine's normal voice construction); **0**
  `disconnect()` calls anywhere in the script; breath curve endpoints forced to 0
  and peak factor is BREATH_REL = 0.05; breath gain initialized to 0.

## Known limitations and simplifications

- **n = 2.** Every position template is the median of two performances, and the
  inter-series pause rests on a single observation. The two series agree so tightly
  (≤ 5 ms, ≤ 3 ms) that the medians are close to either performance — but a third
  series could still surprise the grammar (real birds vary series length; this file
  shows none of it).
- **Pitch resolution is one STFT bin (10.8 Hz).** The fundamental reads 323.0 Hz
  almost everywhere partly because adjacent bins are 312.2/334. Actual fine pitch
  movement inside a bin's width is invisible to this measurement; the contour
  templates inherit that quantization. P3's sag (323 → ~302 Hz) spans 2 bins and
  is solidly measured.
- Amp templates are the median band envelopes of two hoots and carry the recording's
  in-band floor noise (floor only ~23 dB below hoot peaks): they ripple mid-hoot
  (e.g. P2 dips to 0.18 at 3/16) in ways that are part measurement, part noise.
  Used as measured, per engine discipline — the same treatment the cardinal got.
  Templates also start/end at the segmentation threshold (−12/−17 dB rel. peak),
  not at zero, so rendered hoots begin and end at the measured envelope values,
  as in the cardinal build.
- Note durations are drawn independently from measured ranges while plan offsets
  follow the period draws, so a long-drawn hoot can eat into the following gap
  (periods and durations covary in the real bird; here they don't). The effect is
  small: period ranges are ≤ 3 ms wide and duration ranges ≤ 5 ms wide.
- Design choices that are **not** measurements: resonance frequencies/gains, the
  650 Hz breath bandpass and 0.05 breath cap (the invariant ceiling; the hoots'
  near-purity is the measurement behind keeping it at the floor), the single
  voice's stereo position, per-position peak gains (0.46-scaled from measured
  relative peaks, engine rule), the 112 BPM grid, the A-major-pentatonic target
  scale, gridSeriesPause 4.286 s, saw/FM amounts, and the morph's loop-lock
  threshold.
- The Sing scheduler keeps the measured 27.465 s pause at the bird end. That is
  the species' real patience and it is kept on purpose; the morph slider shortens
  it toward the grid.
- Not verified: the sound itself. No headless browser/audio on this VM — the
  ear-gate is Jimmy's, by design.
