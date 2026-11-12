# Bird-synth engine — Gate 1 build notes

**Deliverable:** `cardinal.html` — one Northern Cardinal in a browser page.
**Status:** built and machine-verified (syntax, constants, generator logic). Whether it
*sounds* like a cardinal is Jimmy's ear-gate, not claimed here.

## Method

1. **Reference.** XC1093538 (Xeno-canto, grade A, Mario Reyes Jr, Lexington KY,
   CC BY-NC-SA 4.0) — chosen in the sample rounds for its near-silent floor and huge
   phrase-to-floor contrast. Phrase shapes cross-checked against XC10170 (grade B,
   Paul Jaszczak, PA, CC BY-NC-ND 2.5). No recording audio is used in the page; the
   synth re-creates measured contours with oscillators.
2. **Measurement** (`analysis/measure_final.py`, data in
   `analysis/cardinal-measurements.json`). STFT (1024-pt Hann, 128 hop) dominant-peak
   pitch tracking in 1.3–9.5 kHz; note segmentation on the 1.5–9 kHz band Hilbert
   envelope (body pass −24/−31 dB; a second sensitive pass recovered 2 quiet lead-in
   notes). Per note: duration, start/end/peak/min frequency, 16-point pitch-contour and
   amplitude templates, second-harmonic ratio. Result: **85 body notes in 4 bouts +
   2 lead-ins**, typed by contour rules into L / H / F / V.
3. **Model.** Each phrase type is rendered from its median measured contour and
   amplitude templates (Web Audio `setValueCurveAtTime`), duration drawn per note from
   the measured range. The Sing engine generates bouts from the measured grammar
   (below). The Bird⇄Electronic slider interpolates pitch, timing and timbre
   continuously.

## Measured phrase table (XC1093538 unless noted)

| Type | n | Duration s, med (range) | Start Hz | End Hz | Peak Hz | 2nd harm. |
|---|---|---|---|---|---|---|
| L — low whistle | 39 | 0.057 (0.047–0.065) | 1922 | 1664 | 1969 | 0.029 |
| H — high downslur | 37 | 0.083 (0.027–0.102) | 3914 | 2156 | 3991 | 0.008 |
| F — fused figure | 5 | 0.117 (0.113–0.134) | 1688 | 2203 | 4027 | 0.012 |
| V — short-fall variant | 4 | 0.101 (0.098–0.101) | 3938 | 3188 | 3964 | 0.007 |
| W — long downslur (XC10170) | 17 | 0.621 (0.533–0.683) | 3820 | 1641 | 4193 | 0.029 |

Contour shapes: L arches gently (1875→1969→1641). H descends gradually
4031→3281 Hz over ~70% of the note, then drops off a cliff to 2156 and holds.
F is the L+H figure with the gap closed (its amplitude template dips to ~0.01
mid-token — the two syllables are still distinct). V falls only to ~3188.
W is the XC10170 bird's slow version of the downslur — same start/end region,
~7.5× the duration.

**Bout grammar (measured):** bouts of 19–23 tokens; 9–11 L+H pairs per bout at a
pair period of 0.288 s (0.273–0.303); gaps L→H 0.094 s (0.086–0.105), H→L 0.053 s
(0.034–0.066); every bout opens with H (one bout with two H spaced 0.62 s);
pauses between bouts 4.87 / 5.71 / 6.05 s; a single soft H lead-in precedes the
bout by ~0.6–0.7 s in 2 of 4 bouts; one bout (of 4) interleaves V for H in later
pairs; one bout closes with a lower H (3211→1945 Hz, ×0.82). Second-harmonic
energy is ≤ 3% everywhere — the whistle is essentially a pure fundamental.

## How the model maps to the syrinx

- **Two voices.** The recording's notes alternate low/high and never overlap —
  one voice at a time. The synth assigns L to the "left" voice and H/V/F/W to the
  "right" (slight stereo separation, ±0.18), each a sine fundamental plus its
  measured 2nd-harmonic component at the measured ratio.
- **Breath / air.** A looped noise source through a 2.4 kHz bandpass, gained per
  note by the note's own measured amplitude template at 0.05 relative level —
  present under every note, never solo. (Level is a design choice; see limits.)
- **Resonant chain (trachea/beak).** Both voices feed one shared stage: a gentle
  bandpass (2.5 kHz) + a +3.5 dB peaking filter (3.4 kHz) + 9.5 kHz lowpass —
  a fixed vocal-tract coloration sitting inside the measured 1.6–4.2 kHz band.

## The morph (Bird ⇄ Electronic), m ∈ [0, 1]

One continuous interpolation, applied at schedule time so the slider is live:

- **Pitch:** each contour point moves in log-frequency from its measured value
  toward the nearest A-major-pentatonic tone (design choice of scale).
- **Timing:** onset offsets and durations interpolate from the measured values
  (sampled per note/bout from measured ranges, jitter ∝ (1−m)) to a 112 BPM grid
  (pair = ½ beat = 0.268 s, notes gated to 16ths, bout pause = 8 beats = 4.29 s).
- **Timbre:** sawtooth layer fades in (×0.30·m through a lowpass opening
  4.5→12 kHz), FM deviation grows (×1.5·m of f0), breath falls to 0.4×.
- **Looping:** at m ≥ 0.5 the first generated bout pattern is cached and repeats —
  the phrases begin to loop, as specified.

## Verification performed

- Page script extracted → `node --check`: **pass** (before and after final edits).
- **Constant cross-check:** every measured value embedded in the page (5 phrase
  types × contour + amplitude templates, durations, start/end Hz, harmonic ratios,
  instance counts; grammar gaps, pair period, bout pauses) compared programmatically
  against `cardinal-measurements.json`: **118 values, all match.**
- **Generator logic tests (node, headless):** quantize() lands on-scale for all
  landmark frequencies; morph is identity at 0 and fully quantized at 1; 2000
  generated bouts all land inside the measured envelopes (19–23 tokens, ≤ 4 fused
  per bout, spans 2.67–3.88 s vs measured 2.7–3.8 s, V-bouts 24% vs the 1-in-4
  observation, F share 5.3% of tokens vs measured 5.9%).
- Not verified: the sound itself. No headless browser/audio on this VM — the
  ear-gate is Jimmy's, by design.

## Known limitations and simplifications

- Templates are medians of median-filtered peak tracks; the 46.9 Hz STFT bin size
  quantizes every contour point, and fast sweep detail below ~5 ms is smoothed.
- H's 0.027 s minimum is a single fragmentary token (kept for traceability; the
  triangular duration sampler rarely approaches it).
- V's template tail (dip to 2156, rise back to ~3188) rests on n = 4 and may
  include tracker ambiguity at low amplitude; its amplitude there is ≤ 0.15, so
  its audible weight is small.
- W's first contour point (4617 Hz) is a one-frame attack transient in the median
  track; the sustained start is ~3820–4000 Hz. Template used as measured.
- Bout-generator probabilities (two-H opener 25%, lead-in 50%, V-bout 25%,
  low closer 25%) are point estimates from **four bouts** — coarse by necessity.
  Fused-token placement is bounded so token counts stay in the measured range.
- Note durations are drawn independently from measured ranges while onsets follow
  the median-based plan, so a long-drawn note can overlap the next onset by
  ≤ ~0.02 s (the real bird's durations and gaps covary; ours don't).
- Design choices that are **not** measurements (nothing in a mono close recording
  could supply them): resonance frequencies/gains, breath level, stereo pans,
  per-type peak gains, the 112 BPM grid, the A-major-pentatonic target scale,
  saw/FM amounts, and the morph's loop-lock threshold.
- Dialect: the model is the Kentucky bird. The Lusby MD reference (XC1010609)
  remains the standing dialect check for a future pass.

## GATE RESULT — 2026-11-11: FAILED Jimmy's ear-gate
Jimmy: "soooo much static i can barely hear the bird." Post-mortem (Mordecai):
- Page defect: the breath bus takes one additional parallel tap connection per note,
  removed only by a setTimeout; at the measured 0.288 s pair period the taps overlap and
  stack, so breath noise gain multiplies during bouts. Fix direction (when authorized):
  one fixed breath path, per-note gain envelope on a single bus, much lower level.
- Reference-file trap: XC1093538.wav is IEEE float; misdecoding players render it as
  static over a faint bird. Proper decode measures gaps ≈ -41 dB RMS vs phrases ≈ -15 dB.
  16-bit WAV + MP3 now sit beside it in samples/cardinal/.
- Status: awaiting Jimmy's ruling — fix pass on the page, or a different modeling source.

---

## Gate 1 v2 — rebuilt from XC75501 (2026-11-11, same night)

Jimmy ruled on both open questions within minutes of the v1 verdict: the new source is a
recording **he picked himself — XC75501** (via Wikimedia Commons) — and the rebuild, including
the breath fix, was authorized on the spot. He added one requirement after learning the retired
Kentucky file hides an airplane pass the v1 pipeline never flagged (he caught it by ear): every
future source gets an explicit rumble scan, result stated even when it's "none found."

**New source.** XC75501 — Northern Cardinal, **Jonathon Jongsma**, Wood Lake, Richfield,
Minnesota, 2011-04-09 · XC grade B · **CC BY-SA 3.0** · OGG Vorbis 44.1 kHz stereo, 35.2 s.
Measured phrase-to-floor contrast: gap windows ≈ −48 dB RMS vs phrase peaks ≈ −16 dB (~31 dB
separation — the cleanest file of the whole candidate set). Five bouts of repeated phrases over
a near-silent floor; the page's listed background species (Red-winged Blackbird, Song Sparrow,
Canada Goose) are faint and fall between bouts, so templates draw on the cardinal bouts only.
Method script: `analysis/measure_xc75501.py`; data: `analysis/cardinal-measurements-xc75501.json`.
The v1 Kentucky measurements file is kept, retired as primary.

**Contamination scan (new, Jimmy's requirement).** Short-time RMS in 0.25 s windows over the
60–500 Hz band and the full band; a swell = 1 s-smoothed level > file median + 7 dB sustained
≥ 1.5 s. **Result: none found.** The low band sits at a flat −53.7 dB baseline for all 35.2 s
(−52 to −56 dB per second, no rise anywhere). The broadband detector does fire on four spans
(0–3.5, 9–11.5, 15.75–19, 24.25–26.5 s), but those spans coincide with cardinal bouts 0–3 and
the low band stays flat through them — the energy is the bird's own 1.5–9 kHz song, not a
vehicle or aircraft. No span excluded; zero notes contaminated. (Contrast with XC1093538, where
Jimmy's ear found the airplane the pipeline missed — the scan exists because of that catch.)

**What this bird actually sings** (41 body notes, 5 bouts, same pipeline as v1). A different
song from the Kentucky bird — no L+H pair figure at all:

| Type | Name | n | Duration (med, range) | Pitch (median start → end) | Notes |
|---|---|---|---|---|---|
| Ua | First upslur | 4 | 0.374 s (0.352–0.401) | 2132 → 3101 Hz | opens every full bout |
| Ub | Second upslur | 4 | 0.466 s (0.463–0.536) | 1830 → 3079 Hz | follows Ua by 0.678 s |
| D | Downslur | 16 | 0.165 s (0.142–0.184) | 2239 → 1626 Hz | the bout's body, every 0.345 s |
| C | High chip | 17 | 0.091 s (0.063–0.128) | 4199 → 1680 Hz | steep plunge; 2 of 17 land near 2.5 kHz |

Second-harmonic level is a whisper in this bird (median ratio 0.002–0.013, vs 0.04–0.09 in the
Kentucky bird) — the page renders it at the measured values. Bout grammar: **form A** (3 of 5)
= Ua Ub + 4–6 D; **form B** (1 of 5) = Ua Ub D + 7 C; **form C** (1 of 5) = 10 C. Inter-bout
pauses 4.73 s median (4.07–5.13). Transitions (onset-to-onset medians): Ua→Ub 0.678, Ub→D 0.564,
D→D 0.345, D→C 0.381, C→C 0.299. One sensitive-pass extra — a soft 0.044 s note at 24.546 s,
inside bout 3 between the two upslurs, prominence 45.5 dB — is recorded in the JSON as an
observation and deliberately **not** templated (n = 1). No lead-in notes exist in this bird;
v1's lead-in behavior is gone with the Kentucky grammar.

**The breath fix (the v1 failure).** v1 ran one looped noise source and connected an additional
parallel tap from the breath bus for every note, removed only by a setTimeout; at cardinal
spacing the taps stacked and noise gain multiplied mid-bout until the bird drowned. v2:
- ONE fixed path, connected once at init: noise → bandpass (2400 Hz, Q 0.7) → **breathGain** → master.
- Breath is shaped ONLY by that single gain's per-note envelope (`setValueCurveAtTime` on
  `breathGain.gain`, scheduled in `playNote`). No node is created, connected or disconnected per note.
- Curve = the note's measured amp template × note peak × **0.05**, endpoints forced to exactly 0 —
  so the breath is fully closed between notes and through every pause, and its peak can never
  exceed 5% of the note it rides under (worst case 0.0194 against the loudest note peak 0.46).
- The master chain keeps v1's DynamicsCompressor (threshold −18 dB, ratio 6) ahead of the
  destination — the hard ceiling — and master gain stays 0.9.

**Static-path audit** (on the comment-stripped script; counts are exact): `noiseSrc.connect(`
×1, `nf.connect(breathGain)` ×1, `breathGain.connect(` ×1, `disconnect(` ×**0** anywhere in the
script, `breathBus` ×0 (v1 bus eliminated), `breathGain.gain.setValueCurveAtTime` ×1 (one shaping
site), `breathGain.gain` touched in exactly 2 places (init = 0, playNote envelope), no `bTap`
nodes. A functional harness (stub Web Audio graph, the page's real Sing engine, 480 s of fake
time) confirms the statics at runtime: 63 bouts / 527 notes generated, **exactly one breath curve
per note**, every curve starts and ends at exactly 0, max breath value observed **0.0194** (cap
0.023 = loudest peak × 0.05), breath exactly 0 at all 62 inter-bout pause midpoints, zero
disconnect() calls, breath node in/out degree 1/1.

**Changed vs v1.** Source and attribution (header + footer rewritten; XC75501 / Jongsma /
CC BY-SA 3.0; "no recording audio is used" kept). Kentucky types L/H/F/V and the W (XC10170)
card retired — one bird, one source. Cards now: the bout (form A) + Ua, Ub, D, C. Bout generator
rewritten to the three measured forms; transition periods are drawn per bout from the measured
[min, med, max] instead of fixed medians. Page `peak` gains are no longer flat design picks:
they are the measured per-type relative note amplitudes, scaled so the loudest type (Ub) = 0.46
(Ua 0.342, Ub 0.46, D 0.282, C 0.207 — the high chips really are quieter). Grid durations/periods
use v1's rule (nearest 16th at 112 BPM, stated per value in the JSON audit). Trace landmarks are
this bird's medians: 1626 · 2326 · 3101 · 4199 Hz. Morph semantics unchanged and re-verified
(identity at 0; log-lerp; full pentatonic snap at 1; geometric midpoint at 0.5).

**Verification** (`analysis/verify_v2.js`, reproducible): `node --check` PASS; **113 checks, 0
failures** — 79 constant-audit comparisons against `cardinal-measurements-xc75501.json` (every
frequency/duration/template value in the page traced to the JSON or to a stated derivation rule),
12 static-path checks, 22 functional-harness checks (bout forms all match measured forms, sizes
within 6–10, only measured transitions used; forms over 63 bouts: A 34, B 12, C 17).

**Honest limits.** Ua/Ub templates are medians of only 4 instances each — that is all the bird
sang; the D→C transition rests on a single observation, and the form probabilities (0.6/0.2/0.2)
are point estimates from 5 bouts. The two voices still alternate and never sound together,
because this bird's notes never overlap — same simplification as v1, and concentration/attention
effects across a bout (the run in bout 2 hands over to chips; bout 4 is chips alone) are captured
only at the level of the three forms. As with v1, no claim is made here about how it sounds.
**Jimmy's ears are the gate.**
