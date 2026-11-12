# SYRINX·6 — the engine's flagship interface (Jimmy's directive, 2026-11-11 ~22:08)

"Make it look good too. Like a proper synth with a display screen showing the
bird(s) singing, animated. Some sliders, buttons, keyboard, knobs. Do it proper."

The six per-bird lab pages (cardinal.html, owl.html, …) stay plain gate instruments.
The BANK page is the instrument: one hardware-style synth, six bird voices.
Build it ONLY from the six verified bird models (their measurements JSONs + page
engines). File: ~/workspace/bird-synth/syrinx6.html

## The chassis
- Hardware panel cosplay done properly: dark brushed chassis, engraved labels,
  corner screws, LED indicators, one accent color (TE-style orange) + the screen glow.
- Layout (desktop-first, must not break on a phone): SCREEN top-center, six channel
  strips below it, keyboard along the bottom, master section right of the screen.

## The screen (the heart)
- A bezel-framed LCD showing **six birds on a wire**, flat-styled in their real
  colors (cardinal red, owl brown/cream, heron blue-grey, wren warm brown, sparrow
  grey-brown, towhee rust/black/white).
- Each bird ANIMATES WHILE IT SINGS: beak opens on note onset (CSS transform driven
  by the engine's per-note scheduler callback), head tilt/bob with phrase rhythm,
  throat patch pulse on hoots/squawks. A bird not singing sits still.
- Screen also carries: a live scrolling spectrogram/waveform strip (AnalyserNode →
  canvas) under the wire, and text readout — active bird(s), current phrase type,
  morph %, BPM. Screen has a subtle phosphor/OLED glow + scanline texture.

## Controls
- **Six channel strips**, one per bird: name plate, SING button (performs that bird's
  measured bout grammar), level FADER (vertical slider), per-bird MORPH knob,
  channel LED that lights while it sings.
- **Master section:** CHORUS button (all six sing their grammars together — the
  conducted dawn chorus), STOP, master MORPH knob, BREATH knob (the single capped
  breath bus level — still under the 0.05 law at bird end; the knob scales 0→cap),
  TEMPO knob (the morph grid BPM, default 112), SPACE knob (a simple feedback-delay
  send — honest, small), master volume.
- **Keyboard:** two octaves along the bottom, playable by mouse/touch AND computer
  keys (A/W/S/E/D… mapping shown on the keys). It plays the SELECTED bird's voice —
  that bird's measured envelope + harmonic recipe + breath at chromatic pitches —
  and crossfades to a straightforward synth voice as morph → 1. Selected channel =
  last clicked strip (highlighted).
- Buttons/knobs/sliders must be real working controls wired to the audio graph —
  no decorative fakes. Knobs: vertical-drag rotary with value readout.

## Audio law (inherited, non-negotiable)
- Every bird voice keeps the v2 invariants: single fixed breath path per voice,
  capped, envelope-only shaping, no per-note connect/disconnect; master ends in a
  DynamicsCompressor limiter.
- Per-note animation callbacks come from the scheduler (schedule-time), never from
  a polling loop.

## Verification
- node --check; every DOM id referenced in JS exists in the HTML (scripted audit);
  all six models' constants re-audited against their measurements JSONs;
  static breath-path audit per voice. Report honestly; the sound gate is Jimmy's ears
  and the look gate is Jimmy's eyes, in the morning.
