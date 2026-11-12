# Song Sparrow — reference sample (bird-synth)

Collected 2026-11-11 from Xeno-canto for the bird-synth engine: a modeling reference
(the audio analog of a reference photo — the model is tuned against this, never trained on hype).

Access note: on 2026-11-11 the Xeno-canto recording/listing pages were bot-gated
(Anubis "Access Denied") to both the browser fetcher and curl, and the species
listings are bot-gated to curl — the same wall the cardinal round recorded.
Candidate IDs were found with web search; each candidate's page facts below were
recovered from the search-indexed copy of its recording page where that copy
exists. Downloads themselves worked fine via `curl -L https://xeno-canto.org/<id>/download`.
Paper grades do NOT decide fitness (cardinal lesson): the spectrogram eye-check
and the measured gap contrast below are the deciders.

## Primary reference — the keeper

### XC1005250 — PRIMARY REFERENCE (the one)
- Recordist: Ryan Douglas · Damascus, Montgomery County, Maryland, US · 2025-06-08 06:30
- Type: song · 0:40 · **WAV** (PCM 32-bit, mono, 48 kHz, as downloaded) · peak −3.0 dBFS, RMS −27.2 dBFS
- License (verbatim from the recording page): **Creative Commons Attribution-ShareAlike 4.0**
- Background species (per recording page): **none**
- XC grade: **A** — not extractable on build night (the recording page itself was
  bot-gated via every route available, browser fetch and curl both returning the
  Anubis denial); verified on the live recording page 2026-11-12. The page's
  license, background, type and file specs above were recovered from the
  search-indexed copy of that page. The keeper decision rested on the measured
  numbers below, per the standing rule that paper grades do not decide fitness.
- Spectrogram verdict (`XC1005250-spec.png`): four loud, stereotyped songs at
  ~1–3 s, ~10–12.5 s, ~21–23.5 s and ~33.5–36.5 s stand far off the floor; a
  continuous low-level ambient wash (~−50 dB in the song band) is present between
  songs but sits ~27 dB under the phrases and does not touch pitch tracks.
- Measured vetting (0.25 s full-band RMS windows, peak-normalized):
  - **Gap floor (p10): −45.2 dB RMS** — inside tonight's keeper band (−41 to −48 dB)
  - **Phrase level (p90): −17.9 dB RMS** → **contrast 27.3 dB**
  - Aircraft/rumble scan (per-second <500 Hz energy share + the cardinal swell scan):
    low-band share median 0.024, max 0.158, no second above 0.5; the formal swell scan
    (60–500 Hz, 1 s-smoothed, +7 dB over median sustained ≥1.5 s) found **zero
    low-frequency swells** (baseline −53.6 dB). The four broadband swells coincide
    exactly with the four songs while the low band stays at baseline — the bird's
    own energy, not rumble. **No span excluded, no note contaminated.**

## Candidates measured and rejected

### XC1015039 — measured cleanest, rejected on documentation
- Recordist: Stanislas Wroza · La Haute-Yamaska (near Shefford), Estrie, Québec, Canada · 2025-06-07 06:30
- Type: song · 0:23 · download served WAV (16-bit stereo, 48 kHz)
- Measured: gap floor **−67.5 dB RMS**, phrase −19.1 dB, contrast 48.4 dB; no low-band swell.
- Spectrogram verdict: near-black floor, but the songs vary wildly in level — two
  loud songs and many much fainter elements; the extreme floor suggests a gated/
  processed file, and the faint material is not demonstrably one solo bird.
- Rejected because: its recording page's license and background-species fields could
  not be recovered through the bot gate (no indexed copy of the individual page
  surfaced), so it fails the documented-source requirement despite the numbers.
  If a future pass can verify its page, it is worth a second look.

### XC189286 — strong numbers, rejected on documentation + background flag
- Recordist: Paul Driver · Lower Moreland (near Huntingdon Valley), Montgomery, Pennsylvania, US · 2014-07-31 07:11
- Type: song · 0:45 · MP3 128 kbps, 44.1 kHz (as downloaded)
- Measured: gap floor **−49.7 dB RMS**, phrase −16.8 dB, contrast 32.9 dB; no low-band swell.
- Spectrogram verdict: four loud stereotyped songs stand well off a dark song-band
  floor; a red low-band wash sits below ~1.5 kHz and faint songs (a distant second
  bird) appear between the loud ones.
- Rejected because: the species listing flags background species (`[also]`) for this
  recording, and its individual page's license/background fields could not be
  recovered through the bot gate. XC1005250 documents "background: none" and wins.

### XC79632 — rejected on measurement
- Recordist: Mike Nelson · Cove Lake State Park, Caryville, Tennessee, US · 2011-06-01 11:35
- Type: song · 1:55 · MP3 128 kbps, 44.1 kHz · listing flags background species (`[also]`)
- Measured: gap floor **−33.8 dB RMS**, phrase −21.2 dB, contrast only **12.6 dB** —
  far outside the keeper band; low-band share median 0.153 (the noisiest floor of the set).
- Spectrogram verdict: regular songs, but they sit in a continuous red low-frequency
  wash that never darkens. Not a modeling reference.

## Reference set, final
- Pitch/phrasing/structure model: **XC1005250** (Ryan Douglas, Damascus MD) — the only
  candidate that is simultaneously WAV, eastern US, page-documented background-free,
  page-documented licensed, and measured inside the keeper gap-floor band.
