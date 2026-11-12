# Bird-synth engine — Great Blue Heron build notes (bank bird № 3)

**Deliverable:** `heron.html` — one Great Blue Heron in a browser page.
**Status:** built and machine-verified (syntax, constants, generator logic, noise-path
audit). Whether it *sounds* like a heron is Jimmy's ear-gate, not claimed here.

## Method

1. **Reference.** XC698523 (Xeno-canto, grade A, Thomas G. Graves, Morro Bay CA,
   2021-12-26, CC BY-NC-SA 4.0) — Jimmy's pick; a parabolic-dish recording of one bird
   flying overhead "snarling" as it landed. Background: distant Marbled Godwit (not
   modeled). No recording audio is used in the page.
2. **Measurement** (`analysis/measure_heron.py`, data in
   `analysis/great-blue-heron-measurements.json`; system python3 + numpy/scipy, the
   same stack as the cardinal scripts). Segmentation on the 200 Hz–8 kHz Hilbert
   envelope (on −20 dB / off −30 dB rel envelope peak, gaps < 0.18 s merged) found
   **13 bursts**. Per burst: duration, gap/period to next, peak level, 16-point
   amplitude template, energy profile in six bands (200–450, 450–900, 900–1800,
   1800–3200, 3200–5200, 5200–8000 Hz), spectral centroid, and a pitch-tracker
   estimate (STFT peak track, 150–1000 Hz, burst core) that is marked reliable only
   when stable (IQR/median ≤ 0.12) and prominent (≥ 3.5× band median). A sensitive
   second pass (−28 dB) after 13.5 s found no bursts beyond the 13.
3. **Model.** The heron is the engine's noise-end bird, so the voice is *shaped
   breath*: one looped noise source through a fixed six-filter bank whose gains
   follow each type's measured band profile, enveloped by the type's measured
   amplitude template. Where — and only where — the tracker proved a stable tonal
   peak, a low oscillator core rides at that frequency, its power share set by the
   measured share of burst power within ±6% of the peak. Sing generates whole
   performances on the measured arc (approach → overhead peak → calling → settle).

## Measured burst table (XC698523)

| # | Type | Onset s | Dur s | Peak (rel) | Centroid Hz | Tonal peak | Dominant band |
|---|---|---|---|---|---|---|---|
| 0 | K chip | 3.578 | 0.077 | 0.078 | 456 | none proven | 200–450 (0.74) |
| 1 | M croak | 4.670 | 0.263 | 0.137 | 775 | none proven | 900–1800 (0.52) |
| 2 | L snarl | 5.332 | 0.828 | 0.612 | 1032 | **914 Hz ✓** | 900–1800 (0.86) |
| 3 | L snarl | 6.441 | 0.834 | 1.000 | 1027 | **961 Hz ✓** | 900–1800 (0.96) |
| 4 | L snarl | 7.611 | 0.709 | 0.247 | 760 | none proven | 450–900 / 900–1800 |
| 5 | M croak | 8.645 | 0.465 | 0.224 | 710 | **773 Hz ✓** | 450–900 (0.78) |
| 6 | M croak | 9.465 | 0.390 | 0.410 | 973 | **938 Hz ✓** | 900–1800 (0.83) |
| 7 | L snarl | 10.089 | 0.795 | 0.295 | 1118 | none proven | 900–1800 (0.60), broadest |
| 8 | M croak | 11.184 | 0.325 | 0.285 | 913 | **914 Hz ✓** | 900–1800 (0.54) |
| 9 | M croak | 11.760 | 0.396 | 0.390 | 976 | **914 Hz ✓** | 900–1800 (0.71) |
| 10 | M croak | 12.575 | 0.350 | 0.374 | 1248 | **961 Hz ✓** | 900–1800 (0.83) |
| 11 | K chip | 13.747 | 0.061 | 0.164 | 604 | none proven | 200–450 (0.70) |
| 12 | K chip | 14.941 | 0.108 | 0.220 | 912 | **867 Hz ✓** | 450–900 (0.48) |

Gaps between bursts: 0.233–1.134 s (median 0.346). Onset-to-onset periods by type
pair are in the JSON (e.g. L>L 1.109–1.170, M>L 0.623–0.662, M>M 0.576–0.820).

## Burst types (medians)

| Type | n | Dur s, med (range) | Peak med | Centroid Hz | Band profile (200 Hz → 8 kHz) | Tonal peak (proven n) | Peak power share |
|---|---|---|---|---|---|---|---|
| L — Long snarl | 4 | 0.811 (0.709–0.834) | 0.454 | 1029 | .045 / .142 / **.731** / .009 / .000 / .000 | 937.5 Hz (2 of 4) | 0.329 |
| M — Croak | 6 | 0.370 (0.263–0.465) | 0.330 | 943 | .018 / .226 / **.625** / .026 / .000 / .000 | 914.1 Hz (5 of 6) | 0.706 |
| K — Chip | 3 | 0.077 (0.061–0.108) | 0.164 | 604 | **.698** / .203 / .221 / .026 / .000 / .000 | 867.2 Hz (1 of 3) | 0.472 |

Two honest surprises in the data: the croaks are *more* tonal than the snarls (71% of
croak power sits within ±6% of the ~914 Hz peak — the "squawk" has a strong tonal
spine at conversational level, and gets noisier as it gets louder), and essentially
no energy exists above 3.2 kHz in any burst — the top two filter bands are
near-silent because the measurement says so.

## The performance arc (what Sing replays)

One performance exists in the file; Sing treats its shape as the species' script:

- **Approach** (bursts 0–1): a soft chip (0.078) and a soft croak (0.137), ~1 s apart.
- **Overhead** (bursts 2–3): two long snarls at 0.612 and **1.000** — the arc peak,
  the bird directly over the microphone.
- **Calling** (bursts 4–10): seven bursts (L M M L M M M) at 0.224–0.410.
- **Settle** (bursts 11–12): two chips at 0.164 / 0.220, then silence.

The generator draws: approach = the measured pair (45%), a lone croak (30%), or none
(25%); overhead = always two L snarls at the measured peak pattern; calling = 5–7
bursts with L share 2/7 at peaks drawn from [0.224, 0.295, 0.410]; settle = 1–2 chips
from [0.164, 0.192, 0.220]. Periods are drawn per type-pair from the measured
transitions table; the one pair the generator can produce that the file doesn't
contain (L>K) falls back to the pooled measured gaps.

## How the model maps to the syrinx

- **Breath is the instrument.** One white-noise source (looped, created once) feeds
  six fixed bandpass filters (centers 300 / 636 / 1273 / 2400 / 4080 / 6448 Hz —
  geometric means of the measured bands). Each filter has a fixed gain node; per
  burst, those gains are set from the type's measured profile (renormalized;
  contrast exponent rises with morph) and the single shared envelope gain plays the
  type's 16-point amplitude template at the burst's peak. **No node is connected or
  disconnected per burst — there is nothing to stack.** This is the direct negation
  of the cardinal v1 defect (per-note parallel taps on the breath bus), and the
  static audit below proves the shape of the graph.
- **Tonal core.** Where the tracker proved a peak, a sine (plus its measured 2nd
  harmonic, ratio 0.016–0.117) at the type's median peak frequency, amplitude-shaped
  by the same template, carrying √share of the burst's amplitude against the
  noise's √(1−share). The core is a steady tone: the measurement supports a median
  frequency, not a within-burst contour, so none is invented.
- **Resonant chain.** One shared stage (design choice): +3 dB peaking at 1250 Hz
  (inside the measured 0.9–1.8 kHz energy mass) + 8 kHz lowpass.
- **Safety.** Burst envelope peaks are capped at 0.8 × relative peak, master at 0.9,
  and the output ends in a DynamicsCompressor (threshold −18 dB, ratio 6). The
  loudest measured moment (the overhead snarl at rel 1.0) renders at 0.8 — fierce,
  never clipping.
- **Mono in, mono out.** The source is mono; no stereo placement is invented
  (contrast the cardinal's two-voice alternation — a measured behavior of *that*
  recording).

## The morph (Bird ⇄ Electronic), m ∈ [0, 1]

One continuous interpolation, applied at schedule time so the slider is live:

- **Timing:** burst durations and onset periods interpolate from measured values to
  the 112 BPM grid (durations rounded to 16ths with a 2-16th floor; periods to the
  measured pairs' grid values); the inter-performance pause goes to 8 beats.
- **Tonal core:** its frequency log-lerps from the measured peak toward the nearest
  A-major-pentatonic tone; its power share grows from the measured share toward
  0.75; a sawtooth layer (×0.30·m) and FM deviation (×1.5·m of f0) fade in — the
  cardinal page's recipe, kept so the bank morphs coherently.
- **Noise:** band-profile contrast exponent 1 → 1.9 and filter Q 1.3 → 3.4, so the
  squawk visibly tightens into rhythmic, pitched pulses at the electronic end.
- **Looping:** at m ≥ 0.5 the first generated performance is cached and repeats.

## Verification performed

- Page script extracted → `node --check`: **pass**.
- **Constant cross-check** (`analysis/heron_work/verify_heron.js`): every measured
  value embedded in the page — per type: counts, duration medians/ranges, grid
  durations, peak medians, centroids, 6-band profiles, 16-point amplitude
  templates, tonal-peak frequency/share/proven-count/harmonic ratio; all 7
  transition rows; pooled gap stats; the arc values (traced to bursts 0–3, the
  calling peaks, the settle peaks); and all 13 sequence rows — compared
  programmatically against `great-blue-heron-measurements.json`:
  **193 values, all match.**
- **Generator logic tests (node, headless):** 2000 generated performances — every
  one keeps the measured arc structure (0–2 approach bursts ≤ 0.16 peak; exactly
  two overhead L snarls at 0.55–0.72 then 0.92–1.0; 5–7 calling bursts within
  0.224–0.410; 1–2 settle chips within 0.164–0.220; all bird-side periods within
  the measured transition/fallback ranges, all grid periods within the measured
  grid set; spans 4–17 s). Morph is identity at 0; quantize(914.1 Hz) lands on
  880 Hz (A, pitch class 9 ∈ A-major pentatonic).
- **Static noise-path audit:** exactly **1** noise buffer source; exactly 1
  `noiseSrc.connect`, 1 band-gain→noiseGain connect pattern, 1
  `noiseGain.connect(voiceBus)`; **0** `.disconnect(` calls in the entire script;
  0 references connecting noise nodes inside `playBurst` (it only schedules
  `setValueCurveAtTime` on the single envelope gain and `setTargetAtTime` on the
  fixed band gains/Q); exactly 1 DynamicsCompressor, fed by master. **Pass.**
- Not verified: the sound itself. No headless browser/audio on this VM — the
  ear-gate is Jimmy's, by design.

## Known limitations and simplifications

- **One performance.** Everything about the arc's *shape* — phase patterns, the
  approach-pattern probabilities, calling counts 5–7, settle counts 1–2 — is a
  point estimate from a single 19 s performance. The pause between performances
  (6–10 s) is a design choice; the file ends mid-silence and holds no measurement
  of it. Grid pause (8 beats), the pentatonic target, the 112 BPM grid, the
  resonant chain, filter centers/Q, the morph's share target (0.75), contrast and
  Q ramps, saw/FM amounts, and the loop-lock threshold are likewise design choices,
  labeled as such in the page data.
- **Pitch honesty, in detail.** The "tonal peak" is the STFT's dominant peak in
  150–1000 Hz; in a noisy squawk it may be a resonant (formant) peak rather than
  the syrinx fundamental proper — the page calls it a tonal peak, not a fundamental.
  5 of 13 bursts yield no proven track: both quiet approach bursts (#0, #1), the
  two broadband snarls #4 and #7 (#7's tracker jumps between ~350 Hz and its
  harmonics; 2nd-harmonic ratio 1.07), and chip #11. Per-type cores rest on
  L 2/4, M 5/6, K 1/3 proven instances — **the chip's core is the weakest claim in
  the model** (a single 0.108 s instance; the type's median profile is dominated by
  its two pitchless low thumps, which is also why K's centroid, 604 Hz, sits far
  below its tonal peak).
- Segmentation thresholds (−20/−30 dB) set the burst boundaries; the softest
  burst edges live below them, so durations are conservative by ~10–20 ms at the
  tails. The ambient bed (200–500 Hz-dominated water/wind at ≈ −44 dBFS) is
  excluded from the model by design.
- Median band profiles need not sum to 1 (K sums to 1.148); the page renormalizes
  before use — a pure rescale, audited as embedded.
- The rumble scan's max deviation was 7.9 dB against an 8 dB swell criterion —
  close to the line. The deviation is concentrated around the calling section and
  shows no rise-and-fall shape; it tracks the bird's own activity (segmentation
  tails + proximity), not a vehicle. Verdict CLEAN, in agreement with the
  independent vetting in SOURCES.md — but the margin is recorded here honestly.
- The electronic end stretches chips hard: K's grid duration (0.268 s, the 2-16th
  floor) is 3.5× its measured 0.077 s. That is the grid's floor, not a measurement.
- The model is one Morro Bay bird on one December morning. Herons elsewhere —
  including Jimmy's pier bird — will differ; dialect checks are future work.
