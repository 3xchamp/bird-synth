# Carolina Wren — reference sample (bird-synth)

Collected 2026-11-11 from Xeno-canto for the bird-synth engine: a modeling reference
(the audio analog of a reference photo — the model is tuned against it).

## Verification limitation (read first)

The XC recording pages could **not** be read on 2026-11-11: `browser_open` on
https://xeno-canto.org/364592 (and the other candidates) returned an Anubis
"Access Denied" bot-gate, a curl fetch of the same pages returned the Anubis
challenge page, and the XC API v2 is dead (v3 needs a personal key). So on
build night the **XC grade and license could not be verified** — not guessed,
not copied from search snippets. That gap was closed on **2026-11-12**, when the
keeper's recording page was read live and verified (grade, license and
background below). The rejected candidates' grade/license were never checked
and don't matter. What *was* verified on build night, from independent
sources that did answer:

- Search-index listing rows for the species page: recordist, date, time, country,
  location, elevation, type, and the presence/absence of the `[also]`
  (background-species) marker for each candidate.
- The downloaded files' own ID3 tags: recordist, location with coordinates,
  date/time, type, and the recordist's remarks (quoted below).
- All acoustic vetting numbers: measured here, from the files themselves.

That live-browser pass over https://xeno-canto.org/364592 was completed on
2026-11-12: **XC grade A · license Creative Commons
Attribution-NonCommercial-ShareAlike 4.0 (CC BY-NC-SA 4.0) · background
species none** — recorded in the keeper entry below. No open items remain on
this source.

## Primary reference — KEPT

### XC364592 — the modeling source
- Recordist: **Brian Murphy** · Schenck Forest, Wake County, North Carolina, US
  (35.8174, -78.7193 per file ID3) · **2017-04-14 11:30** · elev. 130 m
- Type: **song** · bird-seen: yes · playback-used: no (ID3 remarks)
- Background species: **none** (recording page, verified 2026-11-12; the
  species-listing row likewise carries no `[also]` marker)
- XC grade: **A** (verified on the recording page 2026-11-12) · License:
  **Creative Commons Attribution-NonCommercial-ShareAlike 4.0** (CC BY-NC-SA
  4.0, verified 2026-11-12)
- File: MP3 320 kbps, 44.1 kHz mono · 36.21 s · peak −2.9 dBFS
- **Spectrogram eye-check:** five-plus bouts of rich harmonic phrases
  (fundamental ~2–3.3 kHz with stacks to ~7.5 kHz) standing bright yellow/orange
  off a dark purple floor for 0–28 s. From ~28.5 s the picture changes: loud
  low-frequency vertical bursts (a different, low vocalisation) — excluded, below.
- **Measured gap contrast (0.25 s windows, full band, peak-normalised):**
  quietest window **−53.3 dB RMS**, p10 **−52.0 dB**, median −46.8 dB;
  phrase windows p90 **−22.7 dB**, max **−13.4 dB** → ~29–39 dB phrase-to-floor
  separation. The quietest floor of the four candidates, inside tonight's
  keeper range (−41 to −48 dB and better).
- **Aircraft/rumble scan (per-second 60–500 Hz energy + swell detector):**
  LF baseline **−54.2 dB**; exactly one swell — **28.0–33.5 s, +33.3 dB** over
  baseline, matching the low bursts in the spectrogram. **Span 28.4–36.21 s is
  EXCLUDED from all templates and grammar.** No LF swell anywhere in 0–28.4 s;
  broadband rises there coincide with the wren bouts while the LF band stays
  flat, i.e. the energy is the bird, not rumble.
- Model yield from 0–28.4 s: **70 syllables, 6 bouts**, types D 16 / U 18 /
  L 20 / S 16. Measurements: `analysis/carolina-wren-measurements.json`.

## Candidates not kept

### XC511443 — clean backup, not chosen
- Recordist: Bobby Wilcox · West Lucas (near Coralville), Johnson County, Iowa,
  US · 2019-10-07 10:30 · song · "About 10m away in deciduous woodland" (ID3)
- Listing background species: none shown (no `[also]` marker)
- File: MP3 192 kbps, 48 kHz stereo · 36.7 s
- Numbers: gap windows min **−41.8 dB**, p10 −41.3 dB, median −40.3 dB;
  phrase max −11.9 dB (~30 dB separation — keeper-range, but a shallower floor
  than XC364592's −52 dB).
- Spectrogram verdict: beautifully stereotyped — 6 bouts of an identical
  4-syllable phrase — but thinner (fundamental + one harmonic band) and with
  faint constant tone bands at ~6.3 and ~7.0 kHz running through the whole file.
  Not chosen: XC364592 is quieter-floored and harmonically richer, which is
  this species' synthesis problem. Grade/license not checked (rejected candidate).

### XC828451 — REJECTED (background chorus)
- Recordist: Richard E. Webster · Pulltite Campground, Ozark National Scenic
  Riverways, Missouri, US · 2023-05-22 05:19 · dawn song
- Listing background species: **`[also]` marker present** (species not named in
  the snippet)
- File: MP3 320 kbps, 48 kHz · 37.3 s · gap min −43.9 dB, median −30.3 dB
- Spectrogram verdict: the wren sits at 1.7–3.3 kHz while a loud broadband
  chorus fills 5–8.5 kHz through the entire file. Phrases do not stand alone.

### XC316295 — REJECTED (wash + tone)
- Recordist: Sue Riffe · Fakahatchee Strand Preserve SP, Collier County,
  Florida, US · 2016-04-26 18:42 · song · ID3 remark notes a White Ibis taking
  off near the end
- Listing background species: none shown (no `[also]` marker)
- File: MP3 320 kbps, 48 kHz · 49.2 s · gap min −41.7 dB but **median −21.7 dB**
- Spectrogram verdict: a red low-band wash up to ~1.6 kHz across the whole
  file plus a constant ~6.8 kHz tone band; phrases are modest against it.
  The median window level (−21.7 dB) is the tell: there is no quiet floor.
