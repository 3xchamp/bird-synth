# Eastern Towhee — reference sample (bird-synth)

Collected 2026-11-11 from Xeno-canto for the bird-synth engine: a modeling reference
(the audio analog of a reference photo — the model is tuned against it).

Access note: on 2026-11-11 every xeno-canto.org recording/species page was bot-gated
(Anubis "Access Denied") from this host, via both the browser fetcher and curl, and
API v2 is retired (v3 needs a personal key). Candidate IDs, recordists, dates,
locations and types below come from the search-index copies of XC's own species
listings; downloads used the recordings' /download endpoints, which are not gated.
Per-recording-page fields that could not be read off the page itself (grade,
license) were flagged as unchecked rather than assumed on build night — the
keeper's grade, license and background have since been verified on the live
page (2026-11-12, below).

## Primary reference — the keeper

### XC1015083 — PRIMARY (modeled)
- Recordist: Stanislas Wroza · La Haute-Yamaska (near Shefford), Estrie, Québec,
  Canada (460 m) · 2025-06-07 06:30
- Type: song · 1:26 · WAV PCM 16-bit stereo 48 kHz (the /download file is WAV
  despite an .mp3 filename in the listing) · peak −0.2 dBFS in the loudest song
- XC grade: **A** (verified on the recording page 2026-11-12) · License:
  **Creative Commons Attribution-NonCommercial-ShareAlike 4.0** (CC BY-NC-SA
  4.0, verified 2026-11-12)
- Background species: **none** (recording page, verified 2026-11-12; the
  species listing for XC1015083 likewise carries **no [also] marker**, though
  its neighbours XC1015084 / XC1015082 do). The spectrogram agrees: one close bird, plus a distant countersinging
  towhee audible in a few gaps — those faint songs (band peak ≤ −15 dB, 3 of 17
  detected) are excluded from every template.
- Spectrogram verdict: near-black floor; 14 loud songs, each the textbook
  two-part towhee form — two intro notes then a loud trill at ~4.1–4.2 kHz —
  standing far off the floor. Phrases dominate by ~52 dB.
- Measured vetting (0.25 s window RMS, full band, peak-normalized):
  gap floor p10 **−70.4 dB** vs phrase level p90 **−18.3 dB** (quietest window
  −72.2 dB). Tonight's cardinal keepers measured −41 to −48 dB gap floors; this
  file is quieter than all of them.
- Rumble / aircraft scan (cardinal method: 0.25 s RMS, 60–500 Hz band, swell =
  1 s-smoothed level > median + 7 dB sustained ≥ 1.5 s): low-band baseline
  **−76.9 dB, zero swells anywhere in the 86.6 s file**. Broadband swells found
  coincide exactly with the 13 loudest song spans — the bird's own 1.5–9 kHz
  energy; the 60–500 Hz band stays at baseline through every one. **No span
  excluded, no note contaminated.**

## Candidates examined and rejected

All gap figures: 0.25 s window RMS p10 (floor) vs window max (phrase), dBFS-peak-normalized.

### XC840196 — runner-up (kept as dialect check, not modeled)
- Manuel Oudard · Norfolk (near Ungers Corner), Haldimand County, Ontario,
  Canada · 2023-05-23 07:00 · song · 0:41 · MP3 44.1 kHz mono
- Listing carries an [also] marker (background species present). Spectrogram:
  clean textbook songs from the close bird, but a uniform hiss floor
  (gap p10 −40.6 dB) and fainter songs of at least one other bird between them.
  Fitness: usable, strictly worse than XC1015083 on floor and background.

### XC83524
- Jelmer Poelstra · Green Lakes, Syracuse, NY, US · 2008-05-08 · song · 0:19 ·
  MP3 320 kbps 44.1 kHz mono · gap p10 −52.8 dB on paper
- Spectrogram verdict: busy low band, overlapping background song through the
  phrases, broadband wash to ~13 kHz. The quiet gaps are real but the phrases
  are not solo. Rejected.

### XC1038305
- Bobby Wilcox · Williamsburg, Hampshire County, Massachusetts, US · 2025-06-19 ·
  song · 0:15 · MP3 192 kbps 48 kHz stereo · gap p10 −46.9 dB
- Spectrogram verdict: the towhee is present at 2–4 kHz, but the frame is
  dominated by repeated loud broadband vertical pulses reaching 13 kHz
  (another sound source close to the mic). Too short and not solo. Rejected.

### XC895156
- Thomas Magarian · GWNF, Bealer's Ferry Pond, Page County, Virginia, US ·
  2024-03-28 · song · 0:48 · WAV IEEE float 48 kHz mono
- Gap floor only −28.3 dB — a loud ambient wash under everything; phrase-to-floor
  contrast ~16 dB. WAV format cannot rescue a dirty floor. Rejected.

### XC546745
- William Whitehead · Scherman Hoffman Wildlife Sanctuary, Bernardsville, NJ,
  US · 2020-04-17 · song · 0:09 · MP3 128 kbps 48 kHz
- Gap floor −25.1 dB and only 9 s long. Rejected on both counts.

### XC691329
- Christopher McPherson · Hollis, Hillsborough County, New Hampshire, US ·
  2021-04-25 · song · 2:12 · MP3 128 kbps 44.1 kHz mono
- Spectrogram: a different, very loud caller repeating identical broadband
  spikes every ~10 s dominates the file; the towhee sits faint underneath.
  Rejected.

### XC179558
- Paul Driver · Lorimer Park, Abington, Montgomery County, Pennsylvania, US ·
  2014-05-25 07:30 · song · 1:51 · MP3 44.1 kHz stereo · gap p10 −44.1 dB
- Spectrogram: a full dawn chorus — continuous overlapping song from several
  species across the whole frame. Not a solo reference. Rejected.

### XC1011576
- Valerie Heemstra · Masonville Township, Delta County, Michigan, US ·
  2025-07-04 · song · 0:34 · MP3 320 kbps 48 kHz mono
- Window RMS sits at ≈ −4 dB end to end with low-band (<500 Hz) energy share
  ≈ 1.00 — the file is dominated by low-frequency noise (wind/handling).
  Rejected without further analysis.

### XC736956
- Shelby M Palmer · Palmer property (near Warrensburg), Johnson County,
  Missouri, US · 2022-07-10 · song · 3:19
- Same failure as XC1011576: median low-band energy share 0.99 — low-frequency
  noise dominates. Rejected.

## Reference set, final
- Model: **XC1015083** (Wroza, Québec) — 14 loud songs measured.
- Dialect check (not modeled): XC840196 (Oudard, Ontario).
