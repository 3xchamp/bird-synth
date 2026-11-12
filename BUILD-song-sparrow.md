# Bird-synth — Song Sparrow build notes

**Deliverable:** `song-sparrow.html` — one Song Sparrow in a browser page.
**Status:** built and machine-verified (syntax, constants, generator logic, breath-path audit).
Whether it *sounds* like a Song Sparrow is Jimmy's ear-gate, not claimed here.

## Source summary

- **XC1005250** — Ryan Douglas, Damascus, Montgomery County, Maryland, US, 2025-06-08 06:30.
  Song, WAV (PCM 32-bit mono 48 kHz as downloaded), 40.1 s, peak −3.0 dBFS, RMS −27.2 dBFS.
- License (verbatim from the recording page): **Creative Commons Attribution-ShareAlike 4.0**.
  Background species on the recording page: **none**.
- XC grade: **A** — not extractable on build night (the recording pages were bot-gated
  (Anubis) to both the browser fetcher and curl; the license/background/type/file facts
  above were recovered from the search-indexed copy of the recording page); verified on
  the live recording page 2026-11-12.
  Full sourcing record, including all rejections: `samples/song-sparrow/SOURCES.md`.

## Vetting numbers (the deciders, not the paper grade)

- Gap contrast, 0.25 s full-band RMS windows: **gap floor (p10) −45.2 dB RMS vs phrase
  level (p90) −17.9 dB RMS — 27.3 dB contrast.** The floor sits inside tonight's keeper
  band (−41 to −48 dB, the cardinal keepers' range).
- Spectrogram eye-check (`samples/song-sparrow/XC1005250-spec.png`): four loud stereotyped
  songs stand far off the floor; a continuous low-level ambient wash (~−50 dB in the song
  band) runs between songs but is ~27 dB under the phrases.
- Aircraft/rumble scan: per-second <500 Hz energy share median 0.024, max 0.158, no second
  above 0.5. Formal swell scan (60–500 Hz, 1 s-smoothed, +7 dB over the −53.6 dB baseline
  sustained ≥1.5 s): **zero low-frequency swells**. The four broadband swells coincide
  exactly with the four songs while the low band stays at baseline — the bird's own energy.
  **No span excluded, no note contaminated.**
- Rejected: XC1015039 (gap −67.5 dB, contrast 48.4 dB — cleanest numbers, but its page's
  license/background could not be verified through the bot gate and its songs vary wildly
  in level); XC189286 (gap −49.7 dB, contrast 32.9 dB, but listing flags background species
  and its page facts were likewise unverifiable); XC79632 (gap −33.8 dB, contrast 12.6 dB —
  dirty floor, rejected on measurement).

## Method

Same pipeline family as the cardinal v2 measurement (`analysis/measure_song_sparrow.py`,
data in `analysis/song-sparrow-measurements.json`). STFT (1024-pt Hann, 128 hop) dominant-peak
pitch track in 1.5–9.5 kHz; note segmentation on the 1.8–9 kHz band Hilbert envelope
(onset −24 dB / offset −31 dB rel. file peak, min off-time 12 ms, min note 20 ms).
Result: **63 body notes in 4 songs** (+ 2 isolated flat chips between songs, recorded as
strays). Types assigned by pitch/duration rules plus two documented position rules
(P = pre-intro ticks in song 1 only; E = the flat ~4.45 kHz note right after a terminal).

## Measured phrase table (XC1005250)

| Type | n | Duration s, med (range) | Start Hz | End Hz | Peak Hz | 2nd harm. | Peak amp rel. |
|---|---|---|---|---|---|---|---|
| P — pre-intro tick | 5 | 0.027 (0.021–0.043) | 4875 | 6281 | 6516 | 0.003 | 0.081 |
| I — intro whistle | 8 | 0.190 (0.180–0.207) | 2438 | 2438 | 2461 | 0.035 | 0.139 |
| B — buzz | 4 | 0.508 (0.480–0.528) | 3867 | 3844 | 3914 | 0.008 | 0.352 |
| L — low upslur (trill) | 11 | 0.057 (0.049–0.062) | 2109 | 3000 | 3469 | 0.014 | 0.627 |
| H — high downslur (trill, long) | 5 | 0.104 (0.100–0.107) | 6844 | 5320 | 7547 | 0.002 | 0.802 |
| h — high chirp (trill) | 7 | 0.037 (0.036–0.041) | 6234 | 7594 | 7594 | 0.000 | 0.501 |
| M — mid note (trill) | 7 | 0.050 (0.044–0.056) | 4594 | 4898 | 5719 | 0.003 | 0.486 |
| C — chip (trill) | 7 | 0.029 (0.028–0.044) | 3422 | 2977 | 3422 | 0.009 | 0.513 |
| T — terminal high | 3 | 0.121 (0.109–0.176) | 7594 | 7594 | 7641 | 0.007 | 0.078 |
| E — end note | 2 | 0.049 (0.049–0.049) | 4477 | 4406 | 4500 | 0.008 | 0.608 |
| W — flat chip | 4 | 0.068 (0.034–0.114) | 3586 | 3492 | 3609 | 0.004 | 0.091 |

Contour shapes worth noting: I is dead flat (~2.44 kHz across all 16 points). B is flat
~3.87 kHz for its whole half second. L jumps from ~2.11 kHz to a ~3.47 kHz peak mid-note
and settles at ~2.95 kHz. H's median contour is two-humped (rises to ~7.55 kHz, dips to
~4.59 kHz — the M region — rises again, then falls), which is the visible evidence for
the fused-pair reading below. Second-harmonic energy is ≤ 3.5% everywhere — the song is
essentially pure fundamental, like the cardinal's.

**Song grammar (measured, 4 songs):**
- Song 1 (0.32–3.04 s): `P P P P P I I B L H L H L H C` — pause after 7.16 s
- Song 2 (10.20–12.51 s): `I I B L h M C H L h M C T E` — pause after 8.43 s
- Song 3 (20.94–23.78 s): `I I B C H L h M L h M C T E W` — pause after 9.67 s
- Song 4 (33.45–36.72 s): `I I B L h M L h M L h M L T C W C`
- Every song: exactly 2 intro whistles, exactly 1 buzz, then the trill series, then
  (3 of 4) a terminal resolution. Song durations 2.31–3.28 s; pauses 7.16 / 8.43 / 9.67 s.

**Trill (measured explicitly):** the post-buzz series runs **7–10 notes over ~0.73–0.78 s**
at **11.1 notes/s median (range 8.0–13.0)**. The rate spread is structural, not noise:
song 1 sings the series in the long fused form (L H L H L H C — 7 notes, 8.0/s) while
songs 2–4 split the same gestures into L / h / M / C elements (9–10 notes, 10.9–13.0/s).
The per-note contour inside the trill is therefore not one template but the per-type
templates above (L, H, h, M, C) — the page schedules trill notes from those, at the
measured per-pair onset periods.

## What the page does

- **Sing** performs the measured grammar: it picks one of the four observed song forms
  verbatim (element order is never invented), draws each element's duration from its
  measured [min, med, max], and each onset-to-onset period from the measured transition
  range for that ordered pair; pauses are drawn from the measured [7.16, 8.43, 9.67] s.
- **One card per element type** (plus a full-song card) plays that element alone, with its
  measured readouts (Hz range, duration, n; trill elements also carry the series rate).
- **Synthesis:** per-note oscillators follow the measured 16-point pitch + amplitude
  templates (`setValueCurveAtTime`); fundamental + 2nd harmonic at the measured ratio;
  timing from measured durations/gaps; trill notes scheduled at the measured per-pair periods.
- **Morph (Bird⇄Electronic), identical semantics to the cardinal page:** continuous
  interpolation at schedule time; at m=0 identity (measured contours, free timing);
  pitch log-lerps toward an A-major-pentatonic grid; timing pulls toward a 112 BPM grid;
  timbre adds sawtooth + FM edge as m rises; at m ≥ 0.5 the song pattern locks and loops.
- **Attribution header** states the XC id, recordist and license, and that no recording
  audio is used — the sound is synthesized from measurements.

## Audio invariants (v1 failure law — how this page complies)

- Breath/noise is **one fixed signal path** (looped noise source → bandpass → a single
  `breathGain` → master), connected **once** in `initAudio()` and never reconnected.
- It is shaped **only** by that single gain's scheduled per-note envelopes
  (`breathGain.gain.setValueCurveAtTime` in `playNote` — the only breath touch outside init).
- **No per-note connect()/disconnect()** on the breath path; no parallel taps.
- Breath gain peak ≤ **0.05** relative to note peak 1.0 (`BREATH_REL = 0.05`, applied
  against each note's own peak), endpoints forced to **exactly 0** — breath is closed
  between notes and through every pause.
- The master chain ends in a **DynamicsCompressor configured as a limiter**
  (threshold −12 dB, ratio 20, knee 0, attack 0.003 s, release 0.25 s) before the destination.

## Verification performed

- **Syntax:** page script extracted → `node --check`: **PASS**.
- **Constant cross-check:** every measured value embedded in the page (11 phrase types ×
  contour + amplitude templates, durations, start/end Hz, harmonic ratios, peak amplitudes,
  instance counts; 21 transition period ranges; song-pause range; the 4 observed song forms;
  trill rate/count/span; trace landmarks) compared programmatically against
  `song-sparrow-measurements.json`: **514 values, all match (514/514).**
  Design-only values excluded by construction and listed under Limitations: gridDur and
  grid periods, gridSongPause, GAIN_SCALE, stereo voices, resonance frequencies.
- **Generator logic tests (node, headless, DOM stubbed):** quantize() lands on the
  A-major-pentatonic scale for all test frequencies 1500–8500 Hz; morph is identity at
  m=0 and fully quantized at m=1, with midpoints strictly between. **2000 generated song
  plans: every plan is one of the 4 observed forms** (distribution 468–523 per form),
  every plan has exactly 2 intro whistles and 1 buzz, **every onset-to-onset period lands
  inside its measured transition envelope**, song spans stay inside the measured envelope,
  and the generated **trill rate spans 7.91–13.46 notes/s against the measured
  8.03–13.02** (the small overshoot comes from drawing each period independently;
  the real bird's periods covary — see Limitations).
- **Static breath-path audit (line-level):** exactly one `noiseSrc.connect` and one
  `breathGain.connect`, both on the single init line
  (`noiseSrc.connect(nf); nf.connect(breathGain); breathGain.connect(master);`);
  exactly one `breathGain.gain.setValueCurveAtTime` (in `playNote`); **zero**
  `breathGain.disconnect` / `noiseSrc.disconnect` anywhere; zero breath/noise connect
  calls inside `playNote`; `BREATH_REL = 0.05` cap constant present; limiter
  (DynamicsCompressor, threshold −12, ratio 20) present in the master chain.
- Not verified: the sound itself. No headless browser/audio on this VM — the ear-gate
  is Jimmy's, by design.

## Known limitations and simplifications

- **Four songs, one bird, one morning.** Every probability in the generator is a point
  estimate from n=4 songs; the form choice is uniform over the 4 observed forms because
  nothing finer is supported by the data.
- **H is probably a fused pair.** Its duration (~0.104 s ≈ h + M + a sub-12 ms gap) and
  its two-humped median contour both say the segmentation floor merged a high chirp and
  a mid note. It is templated as measured (a distinct long form), and the alternative
  reading is documented in the measurements JSON — the synth does not silently split it.
- **T's template carries one tracker artifact:** at point 13 the median contour dips to
  ~5016 Hz — one instance (song 4's terminal) shows a mid-note pitch-track dip
  (its f_min reads 3469 Hz). Amplitude there is moderate, so the dip is briefly audible
  in the synth's T; it is kept as measured rather than cleaned by hand.
- **Independent draws:** note durations and onset periods are drawn independently from
  measured ranges while the real bird's covary; a generated trill rate can therefore
  overshoot the measured range slightly (13.46 vs 13.02 notes/s worst case in 2000 plans),
  and a long-drawn note can overlap the next onset by a few ms.
- **PeakRel for T and W is low (0.078 / 0.091)** because their median instances include
  quiet tokens; E (n=2) and P (n=5, one song) rest on small samples.
- The two stray W chips between songs (6.96 s, 24.96 s) are recorded in the JSON as
  observations; W is modeled inside songs only where it was observed there.
- **Design choices that are not measurements** (nothing in a mono close recording could
  supply them): resonance frequencies/gains, breath level (capped at the invariant 0.05),
  stereo pans, GAIN_SCALE (0.55 × measured peakRel), the 112 BPM grid and per-type grid
  durations/periods, the A-major-pentatonic target scale, saw/FM amounts, and the morph's
  loop-lock threshold.
- The XC **grade letter is A**, verified on the live recording page 2026-11-12 (it was
  behind the bot gate on build night; see SOURCES.md) — the keeper decision never
  depended on it.
- Dialect: the model is the Damascus, Maryland bird — Montgomery County, ~50 miles from
  Jimmy's house; Song Sparrow song is famously local, so this is a feature to check
  against the birds Jimmy actually hears, not a defect to hide.
