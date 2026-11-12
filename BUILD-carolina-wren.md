# Bird-synth engine — Carolina Wren build notes

**Deliverable:** `carolina-wren.html` — one Carolina Wren in a browser page.
**Status:** built and machine-verified (syntax, constants, generator logic, breath-path
audit). Whether it *sounds* like a Carolina Wren is Jimmy's ear-gate, not claimed here.

## Source summary

XC364592 — Brian Murphy, Schenck Forest, Wake County, North Carolina, US,
2017-04-14, song, MP3 320 kbps 44.1 kHz mono, 36.21 s. Chosen over three other
candidates on measured fitness (see `samples/carolina-wren/SOURCES.md` for all
four, with numbers). **Resolved:** the XC grade and license could not be verified on
build night — the recording pages were Anubis bot-gated on 2026-11-11
(browser_open and curl both blocked; API v2 dead). Mordecai verified both on
the live recording page on 2026-11-12: **grade A · Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0) · background
species none**. Recordist/date/location/type/no-background-marker
are corroborated by the search-index listing rows and the file's own ID3 tags.
No recording audio is used in the page; the synth re-creates measured contours
with oscillators.

## Vetting numbers (keeper)

- Gap contrast, 0.25 s full-band RMS windows (peak-normalised): quietest
  **−53.3 dB**, p10 **−52.0 dB**, median −46.8 dB; phrase windows p90 −22.7 dB,
  max −13.4 dB → ~29–39 dB phrase-to-floor separation.
- Rumble scan: 60–500 Hz baseline −54.2 dB; one swell, **28.0–33.5 s (+33.3 dB)**,
  matching loud low bursts in the spectrogram. **28.4–36.21 s excluded** from
  all templates/grammar. No LF swell in 0–28.4 s.
- Spectrogram eye-check: rich harmonic phrases stand far off a quiet floor for
  0–28 s (spec image kept beside the MP3 in `samples/carolina-wren/`).

## Measured phrase table (XC364592, 0–28.4 s only)

Syllables segmented on the 1.5–9 kHz band envelope; pitch = STFT dominant peak
1.2–9.5 kHz; templates = 16-point medians. Method in full in the measurements JSON.

| Type | n | Duration s, med (range) | Start Hz | End Hz | Peak Hz | harm2 | harm3 |
|---|---|---|---|---|---|---|---|
| D — down-chip | 16 | 0.038 (0.028–0.058) | 2627 | 2003 | — (see JSON) | 0.039 | 0.001 |
| U — up-chirp | 18 | 0.051 (0.034–0.073) | 2885 | 3144 | — | 0.009 | 0.001 |
| L — long ringing | 20 | 0.216 (0.131–0.296) | 3144 | 2541 | — | 0.008 | 0.003 |
| S — short high fragment | 16 | 0.035 (0.021–0.091) | 3575 | 4565 | — | 0.007 | 0.002 |

(Full f_peak/f_min stats per type are in the JSON; the table above carries the
medians the page's cards display.)

**Bout grammar (measured):** 6 bouts of **9–13 syllables**; each bout is the
down-chip / up-chirp / long-syllable motif repeated (the six measured syllable
sequences are embedded in the page and the generator replays them verbatim);
onset-to-onset periods drawn per syllable-type transition from the measured
[min, med, max] (11 transitions measured; fallback = overall measured period
stats, derived as min-of-mins / n-weighted medians / max-of-maxes);
pauses between bouts **3.484–3.905 s** (median 3.526 s).

## What the page does

- Header with source attribution (XC id, recordist) and the explicit line that
  no recording audio is used — the sound is synthesized from measurements.
- **Sing** performs the measured bout grammar (above); at morph ≥ 0.5 the first
  generated bout pattern is cached and loops.
- One card per phrase type (D/U/L/S) playing that syllable alone, with its
  measured readouts (Hz range, duration + range, n, harmonic ratios), plus a
  bout card replaying the first measured bout sequence.
- **Bird⇄Electronic morph:** continuous interpolation at schedule time — at
  m=0 identity (measured contours, free timing); pitch log-lerps toward an
  A-major-pentatonic grid; timing pulls toward a 112 BPM grid (16th-note grid
  durations/periods, bout pause to the nearest beat); timbre adds sawtooth
  (×0.30·m through a lowpass opening 4.5→12 kHz) + FM edge (×1.5·m of f0).
- Synthesis per syllable: sine fundamental following the measured 16-point
  pitch template (setValueCurveAtTime), plus 2nd and 3rd harmonic oscillators
  at the measured ratios, all shaped by the measured 16-point amplitude template.
- **Audio invariants (v1 failure law):** breath is ONE fixed path created once
  in initAudio — looped noise → bandpass → the single `breathGain` → master.
  Per-syllable shaping is only a gain envelope on that one node, endpoints
  forced to 0 (silence between syllables and in pauses), peak capped at
  `BREATH_REL = 0.05` of the syllable's peak. No per-note connect/disconnect,
  no parallel taps. The master chain ends in a DynamicsCompressor configured
  as a limiter (threshold −12 dB, ratio 20, knee 0).

## Verification performed

- **node --check** on the extracted page script: **PASS**.
- **Constant cross-check:** every measured value embedded in the page
  (per type: 16 contour + 16 amp + dur med/min/max + fStart + fEnd + harm2 +
  harm3 + n + peak = 41 × 4 types; 11 transitions × min/med/max; bout-pause
  min/med/max; the 6 bout sequences = 70 syllable tokens) compared
  programmatically against `carolina-wren-measurements.json`: **271/271 match**.
- **Generator logic tests (node, headless):** 5,000 generated bouts — **0
  failures**: every bout's syllable sequence is one of the six measured
  sequences, every bout has 9–13 syllables (measured envelope), and every
  onset-to-onset period lands inside its measured transition envelope.
  Quantize() lands on the A-major pentatonic for all landmark frequencies.
- **Static breath-path audit (grep/inspect of the final script):**
  - exactly one noise path: line 520 —
    `noiseSrc.connect(nf); nf.connect(breathGain); breathGain.connect(master);`
    inside initAudio, executed once;
  - `breathGain.connect` occurs exactly **1** time in the file and
    `breathGain.disconnect` **0** times; playNote touches only
    `breathGain.gain.setValueCurveAtTime` (line 598);
  - breath cap constant present: line 491, `const BREATH_REL = 0.05;`
  - limiter present: line 498 `createDynamicsCompressor()`, line 503
    `comp.connect(actx.destination)` — the master chain's last node.
- Not verified: the sound itself. No headless audio on this VM — the ear-gate
  is Jimmy's, by design.

## Known limitations and simplifications

- **Grade/license verified** (live XC page, 2026-11-12; bot-gated on build
  night — see above and SOURCES.md): grade A, CC BY-NC-SA 4.0, no background
  species.
- The L syllable is a composite: its dominant STFT peak alternates between the
  ~3.1 kHz fundamental and its harmonic stack (~4.6–5.6 kHz), so the measured
  "contour" partly tracks harmonic switching, and the harm2/harm3 ratios
  measured *at the dominant peak* come out small (0.008/0.003) even though the
  spectrogram shows a rich stack. The synth uses the measurements as taken;
  the true harmonic balance is richer than the ratios imply.
- S ("short high fragment") is a residual class — brief sweeps that fit neither
  chip rule — not a claimed natural category; n=16, heterogeneous by construction.
- Bout plan spans with median durations run 1.13–1.98 s vs the measured bout
  spans 1.39–1.72 s: transition periods are drawn independently, so extremes
  widen the span (the real bird's periods covary; ours don't). Sequences,
  counts and per-transition periods stay inside the measured envelopes.
- Bout-sequence choice is uniform over the six measured sequences (n=6 bouts
  is too small to weight); bout-pause and period draws are triangular
  [min, med, max] samplers, as in the cardinal build.
- Design choices that are **not** measurements: resonance frequencies/gains,
  breath level (0.05 cap), stereo pans, the 112 BPM grid, the A-major-
  pentatonic target scale, saw/FM amounts, grid-duration rounding to 16ths,
  and the morph's loop-lock threshold (0.5).
- Dialect: the model is one North Carolina bird on one April morning.
