# Bird-synth engine — Eastern Towhee build notes

**Deliverable:** `eastern-towhee.html` — one Eastern Towhee in a browser page.
**Status:** built and machine-verified (syntax, constants, generator logic, breath-path
audit). Whether it *sounds* like an Eastern Towhee is Jimmy's ear-gate, not claimed here.

## Source summary

XC1015083 (Xeno-canto) — Stanislas Wroza, La Haute-Yamaska (near Shefford), Estrie,
Québec, Canada, 2025-06-07 06:30 · song · WAV PCM 16-bit stereo 48 kHz, 86.6 s.
Chosen from 12 candidates examined (full vetting trail in
`samples/eastern-towhee/SOURCES.md`). The species listing carries no background-species
[also] marker for this recording. One access note: on build night every xeno-canto
recording page was bot-gated (Anubis) from this host, so the recording-page grade and
license could not be read that night; Mordecai verified both on the live page on
2026-11-12 — **grade A · Creative Commons Attribution-NonCommercial-ShareAlike 4.0
(CC BY-NC-SA 4.0) · background species none** — and SOURCES.md now records them as
verified. Candidate facts (recordist/date/location/type) come from the search-index
copies of XC's own listings.

## Vetting numbers

- Gap contrast (0.25 s window RMS, full band): gap floor p10 **−70.4 dB** vs phrase
  level p90 **−18.3 dB** — ~52 dB of separation (cardinal keepers measured −41 to
  −48 dB floors; this file is quieter).
- Spectrogram eye-check (ffmpeg showspectrumpic, full file + zoomed songs): near-black
  floor; 14 loud songs in the textbook two-part form standing far off the floor.
- Rumble scan (cardinal method): 60–500 Hz baseline **−76.9 dB, zero swells** in the
  whole file. Broadband swells coincide exactly with the loud song spans — the bird's
  own energy. No span excluded, no note contaminated.
- A distant countersinging towhee sings 3 faint songs (band peak ≤ −15 dB); they are
  excluded from every template by the loud-song threshold.

## Measured phrase table (XC1015083, 14 loud songs)

| Type | n | Duration s, med (range) | Start Hz | End Hz | Peak Hz | 2nd harm. |
|---|---|---|---|---|---|---|
| I1 — first intro | 14 | 0.178 (0.158–0.205) | 3691 | 2379 | — | 0.013 |
| I2 — second intro | 14 | 0.213 (0.192–0.236) | 2672 | 2625 | — | 0.010 |
| TRILL — whole | 14 | 0.600 (0.483–0.653) | 4219 | 4078 | — | 0.007 |
| TN — single trill note | 114 | 0.039 (0.009–0.062) | 4688 | 4125 | — | 0.006 |

(f_peak/f_min per type are in the measurements JSON; the table shows the landmarks
the page's trace uses.)

**Grammar (measured):** every one of the 14 songs is exactly **2 intros + 1 trill**.
Intro gap I1→I2: 0.150 s (0.106–0.176). Intro→trill gap: 0.077 s (0.054–0.098).
**Trill: 8 notes median (6–10) at 14.0 notes/s median (12.0–18.0)**, measured by
onset-to-onset rate inside each trill; envelope autocorrelation independently shows
a strong ~83 ms periodicity (≈12/s, the paired-pulse component of the trill).
Song duration 1.10–1.27 s; pauses between loud songs 4.99 s median (4.00–7.33).
Second-harmonic energy ≤ 1.3% everywhere — the song is essentially a pure fundamental.

**Method:** STFT (1024-pt Hann, 128 hop) dominant-peak pitch track in 1.3–9.5 kHz;
song segmentation on the 1.5–9 kHz band Hilbert envelope; fine segmentation splits
intros from the trill; trill notes segmented inside the trill on a 1 ms envelope at
40% of trill peak. Templates are 16-point medians across instances. Script:
`analysis/measure_eastern_towhee.py`; data: `analysis/eastern-towhee-measurements.json`.

## What the page does

- **Sing** performs the measured grammar on a scheduler: I1 → I2 → trill (6–10 notes
  of the measured trill-note template at the drawn rate), drawn gaps, drawn inter-song
  pause, looping until stopped.
- **Cards** play each element alone: the full song, I1, I2, and the trill (with its
  measured rate readout: 14.0 notes/s, range 12.0–18.0).
- **Synthesis:** per-note oscillators follow the measured 16-point pitch + amplitude
  templates (`setValueCurveAtTime`), fundamental + 2nd harmonic at the measured ratio.
- **Morph (Bird⇄Electronic), m ∈ [0,1]:** one continuous interpolation at schedule
  time — pitch log-lerps toward an A-major-pentatonic grid; timing pulls toward a
  112 BPM grid (trill grid period = beat/8 = 66.96 ms ≈ 14.9 notes/s, close to the
  measured 14.0); timbre adds sawtooth (×0.30·m) + FM edge (×1.5·m); at m ≥ 0.5 the
  song pattern locks and loops.
- **Audio invariants (v1 failure law):** breath is ONE fixed path — looped noise →
  bandpass → a single `breathGain` → master — connected once at init (script line 270)
  and shaped only by that gain's per-note envelopes; endpoints forced to 0 (silence
  between notes and in pauses); peak capped at `BREATH_REL = 0.05` of the note's peak.
  No per-note connect/disconnect anywhere. The master chain ends in a
  DynamicsCompressor configured as a limiter (threshold −12 dB, ratio 20, knee 0).

## Verification performed

- Page script extracted → `node --check`: **pass**.
- **Constant cross-check:** every measured value embedded in the page (4 element types
  × contour + amplitude templates, durations, start/end Hz, harmonic ratios, peak
  amplitudes, instance counts; grammar gaps, pause, trill note counts and rates)
  compared programmatically against `eastern-towhee-measurements.json`:
  **165/165 match**.
- **Generator logic tests (node, headless):** 2000 generated songs — every song has
  exactly 2 intros; I1→I2 gaps all within 0.106–0.176 s; intro→trill gaps all within
  0.054–0.098 s; trill notes per song 6–10; drawn trill rates 11.96–18.02 /s;
  **0 envelope failures**. Morph is identity at m = 0 (`morphFreq(2671.9) === 2671.9`)
  and quantize() lands on the A-major-pentatonic grid at m = 1. Song spans from the
  generator run 1.008–1.282 s vs measured 1.102–1.270 s (see limitations).
- **Static breath-path audit:** exactly one noise→breath-gain path (one connect line:
  `noiseSrc.connect(nf); nf.connect(breathGain); breathGain.connect(master)` in
  initAudio only); the only other breathGain touch is the per-note
  `breathGain.gain.setValueCurveAtTime` envelope; `disconnect` appears zero times as
  a call (once in a comment); `BREATH_REL = 0.05` cap present; limiter present
  (DynamicsCompressor, ratio 20).
- Not verified: the sound itself. No headless browser/audio on this VM — the
  ear-gate is Jimmy's, by design.

## Known limitations and simplifications

- **Grade and license verified** (live XC page, 2026-11-12; bot-gated on build
  night, above): grade A, CC BY-NC-SA 4.0, no background species. SOURCES.md
  records the same.
- Templates are medians of median-filtered peak tracks; the 46.9 Hz STFT bin size
  quantizes every contour point, and fast sweep detail below ~5 ms is smoothed.
- I1's template tail (points 12–15 dip to ~1.9–2.4 kHz then recover) sits at amplitude
  ≤ 0.19 and may be tracker ambiguity at the note's quiet tail; kept as measured.
- Trill-note durations from the 40%-of-peak threshold segmentation (median 0.039 s,
  min 0.009 s) understate the notes' full extent; the trill's paired-pulse structure
  (autocorrelation ~83 ms) is reported but not separately modeled — the synth renders
  single notes at the drawn rate.
- The generator holds intro durations at their medians while drawing gaps and trill
  parameters, so generated song spans (1.008–1.282 s) can undershoot the measured
  minimum song duration (1.102 s) by ~0.09 s; every gap, count and rate individually
  stays inside its measured envelope.
- Design choices that are **not** measurements: resonance frequencies/gains, breath
  level, stereo pans, the 0.9 peak-gain scale, the 112 BPM grid, the
  A-major-pentatonic target scale, saw/FM amounts, and the morph's loop-lock threshold.
- Dialect: the model is the Québec bird (northern edge of the range). XC840196
  (Ontario) is kept in SOURCES.md as the unmodeled dialect check.
