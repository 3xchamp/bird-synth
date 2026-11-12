# Northern Cardinal — reference samples (bird #1)

Collected 2026-11-11 from Xeno-canto for the bird-synth engine: modeling references
(the audio analog of reference photos — the model is tuned against these, never trained on hype).

Access note: the Xeno-canto API v2 is dead and v3 needs a personal API key (free, from an
XC account page). These files came from the recordings' direct file URLs on the species page.
Quality grades / licenses: see per-file lines (grades verified from each recording page).

## Primary references

### XC215874 — VARIETY reference (loud phrases, busy soundscape)
- Recordist: Terry Davis · Bossier Parish, Louisiana, US · 2013-07-03 14:28
- Type: song · 0:53 · MP3 320 kbps, 44.1 kHz stereo · peak −6.3 dB, RMS −30.3 dB
- XC grade: **D** · License: CC BY-NC-SA 4.0
- Page background cast: Northern Mockingbird, House Finch, American Robin, Eurasian
  Collared Dove, House Sparrow (+ cardinal chips). Remarks: "Breeding- territ. Diff song
  type. Urban."
- Spectrogram verdict: darkest noise floor of the set and the loudest, closest cardinal —
  phrases dominate by a wide margin, in several distinct bout types. But the "quiet" gaps
  hold the background cast above, which is why XC grades it D. Use for phrase variety;
  select clean bouts, never model from the gaps.
- Why both verdicts stand: community grade weighs the whole soundscape; the modeling
  verdict weighs the cardinal phrases themselves. For pristine, this is NOT the file —
  the round-2 hunt for a true A-grade, background-free song is the open sample step.

### XC10170 — PHRASE-SHAPE reference (cleanest background of the set)
- Recordist: Paul Jaszczak · Greenville, PA, US · 06:25 (date not shown on species listing)
- Type: song · 0:53 · MP3 64 kbps, 24 kHz · peak −5.0 dB, RMS −16.5 dB
- XC grade: **B** · License: CC BY-NC-ND 2.5 · Page background species: **none**
- Spectrogram verdict: the loudest, clearest whistle contours of the set — huge clean
  downslurred phrases in bouts of 2–3, ideal for extracting pitch trajectories. Steady
  hiss between phrases (older recording) is the only flaw; hiss does not corrupt pitch
  tracks. ND license note: we analyze/model from it and do not publish processed
  versions of the audio itself.

## Rejected as primary references (kept on disk, verdicts recorded)

### XC35943
- Recordist: Stuart Fisher · Cumming, GA, US · 2009-06-03 09:30 · song · 0:22 · 128 kbps 44.1 kHz
- Verdict: phrases visible but the floor is a uniform wash plus a constant tone band —
  poor SNR despite the "clear" filename. peak −1.4 dB, RMS −23.5 dB.
- XC grade: **B** · License: CC BY-NC-ND 2.5 · Background: White-eyed Vireo, Downy
  Woodpecker — matches the wash seen in the spectrogram.

### XC67168
- Recordist: Daniel Lane · Montclair, NJ, US · 1990-05-04 · song · 0:44 · 128 kbps 44.1 kHz mono
- Verdict: tape-era hiss across the whole frame; phrases embedded in the wash, background
  never darkens. peak −7.2 dB, RMS −32.1 dB.
- XC grade: **B** · License: CC BY-NC-SA 3.0 · Background: American Robin, Blue Jay;
  remarks note a suburban neighborhood and three song types.

## Round 2 — the A-grade hunt (2026-11-11, at Jimmy's word: "a grade")

Four recordings confirmed grade **A** on their own pages, song, ZERO background species.
All four CC BY-NC-SA 4.0. Downloaded via the recordings' /download links (listings are
bot-gated to curl; the browser verified each page first).

### XC1093538 — PRIMARY REFERENCE (the one)
- Recordist: Mario Reyes Jr · Lexington, Fayette County, Kentucky, US · 2025-08-27
- Song · 0:35 · WAV (IEEE float, mono, 48 kHz) · peak −3.0 dB, RMS −22.6 dB
- Spectrogram verdict: near-black floor — the background drops to ~silence between bouts.
  Four massive bouts of rapid repeated whistled phrases, huge phrase-to-floor contrast.
  This is what "really clean" looks like; pitch extraction will be trivial against it.

### XC1010609 — LOCAL reference (the hometown bird)
- Recordist: Rory Nefdt · **Lusby, Calvert County, Maryland** · 2025-06-28
- Song · 1:07 · WAV 16-bit stereo 44.1 kHz · peak −17.1 dB, RMS −37.1 dB
- Spectrogram verdict: five spaced bouts, phrases distinct but the bird sits in a soft
  ambient wash and levels are low — modest phrase-to-floor contrast next to XC1093538.
  Kept as the local-dialect check: this is the cardinal population Jimmy actually hears.

### XC1149458 — grade A, but NOT a modeling reference
- Recordist: Pat Goltz · Madera Canyon, Arizona, US · 2020-04-22
- Song · 1:00 · MP3 320 kbps 48 kHz · peak −3.3 dB, RMS −28.4 dB
- Spectrogram verdict: a saturated wall of broadband ambient (canyon water/wind) with the
  cardinal small at the bottom of the frame. The paper stats looked fine because the NOISE
  is loud. Lesson recorded: XC's grade weighs identifiability + no background species;
  our gate weighs phrase-to-floor contrast. Verified by eye, not assumed.

### XC1133842 — snippet
- Recordist: Rory Nefdt · Palm Coast, Florida, US · 2025-11-02 · song · 0:08 · MP3 192 kbps
- Too short to anchor a model; not eye-checked. Kept for completeness.

## Reference set, final
- Pitch/phrasing model: **XC1093538** (A, KY) + XC10170 (B, PA — big downslurs)
- Dialect check: XC1010609 (A, Lusby MD)
- Variety: XC215874 (D, LA — clean bouts only)

## Jimmy's pick — the Gate 1 source (2026-11-11, supplied by Jimmy via Wikimedia Commons)

### XC75501 — NEW PRIMARY (Jimmy's ear overruled the paper grades)
- Recordist: Jonathon Jongsma · Wood Lake, Richfield, Minnesota, US · 2011-04-09 07:24
- Song · 0:35 · OGG Vorbis 44.1 kHz stereo (Jimmy's upload; Commons file) · peak −2.9 dB, RMS −27.1 dB
- XC grade: **B** · License: CC BY-SA 3.0 · Background listed: Red-winged Blackbird, Song
  Sparrow, Canada Goose (all distant smudges between bouts in the spectrogram)
- Measured verdict: the cleanest file of the whole set by the numbers that matter —
  gap windows ≈ −48 dB RMS vs phrase peaks −16 dB (~31 dB separation; the Kentucky A
  measured −41 dB gaps). Five bouts of repeated downslurred whistles, near-silent floor.
- Jimmy's ruling after the Gate 1 page failure: "this one." The model rebuilds from
  XC75501; the Kentucky bird is retired as primary (kept on disk with its measurements).
