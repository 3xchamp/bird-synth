# Builds minuet_bwv_anh114_transcription.json from the Mutopia/Garvin MIDI render
# of anna-magdalena-04.ly (Allen Garvin, public domain typeset, source: Bach-Gesellschaft).
# Melody = treble track minus ornaments (grace) and the bar-32 cadence chord tones.
# Bass = first bass-staff event of each bar (lowest pitch at the bar's first onset).
import json, struct

def read_vlq(data, i):
    v = 0
    while True:
        b = data[i]; i += 1
        v = (v << 7) | (b & 0x7F)
        if not (b & 0x80): return v, i

def parse(path):
    data = open(path,'rb').read()
    fmt, ntrk, div = struct.unpack('>HHH', data[8:14])
    i = 8 + struct.unpack('>I', data[4:8])[0]
    tracks = []
    for t in range(ntrk):
        ln = struct.unpack('>I', data[i+4:i+8])[0]; i += 8; end = i + ln
        tick = 0; notes = []; running = None; active = {}
        while i < end:
            delta, i = read_vlq(data, i); tick += delta
            b = data[i]
            if b & 0x80: running = b; i += 1
            else: b = running
            if b == 0xFF:
                i += 1; ln2, i = read_vlq(data, i); i += ln2; running = None; continue
            if b in (0xF0, 0xF7):
                ln2, i = read_vlq(data, i); i += ln2; running = None; continue
            typ = b & 0xF0
            if typ in (0xC0, 0xD0): i += 1; continue
            d1, d2 = data[i], data[i+1]; i += 2
            if typ == 0x90 and d2 > 0: active.setdefault(d1, []).append(tick)
            elif typ == 0x80 or (typ == 0x90 and d2 == 0):
                if active.get(d1):
                    on = active[d1].pop(0)
                    notes.append({'onsetBeats': on/div, 'midi': d1, 'beats': (tick-on)/div})
        tracks.append(sorted(notes, key=lambda n:(n['onsetBeats'], n['midi'])))
        i = end
    return div, tracks

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def nm(m): return NAMES[m % 12] + str(m//12 - 1)
def rnd(x): return round(x, 6)

div, tracks = parse('score-src/anna-magdalena-04.mid')
treble, bass = tracks[1], tracks[2]
assert len(treble) == 129 and len(bass) == 75

melody, ornaments = [], []
for n in treble:
    bar = int(n['onsetBeats'] // 3) + 1
    entry = {'bar': bar, 'onsetBeats': rnd(n['onsetBeats']), 'name': nm(n['midi']), 'midi': n['midi'], 'beats': rnd(n['beats'])}
    if n['beats'] < 0.2:   # the bar-8 grace, rendered by LilyPond at the tail of bar 7
        ornaments.append({**entry, 'kind': 'grace', 'belongsToBar': 8, 'note': 'grace before bar 8 A4; in the source MIDI render it steals time from bar 7 final G4 (0.385417 + 0.111979 beats); the melody list restores that G4 to its written 0.5 beats'})
        if melody and abs(melody[-1]['onsetBeats'] + melody[-1]['beats'] - n['onsetBeats']) < 0.01:
            melody[-1]['beats'] = 0.5
        continue
    if bar == 32 and n['midi'] != 67:  # final cadence chord: keep only the top voice (G4) as melody
        ornaments.append({**entry, 'kind': 'cadence-chord-tone', 'note': 'treble-staff cadence chord tone (accompaniment), not the melody line'})
        continue
    melody.append(entry)
ornaments += [
  {'bar': 3, 'kind': 'mordent', 'on': 'E5', 'note': 'articulation symbol in the LilyPond source; not a separate pitched event'},
  {'bar': 5, 'kind': 'mordent', 'on': 'C5', 'note': 'articulation symbol in the LilyPond source'},
  {'bar': 11, 'kind': 'mordent', 'on': 'C5', 'note': 'articulation symbol in the LilyPond source'},
  {'bar': 13, 'kind': 'mordent', 'on': 'C5', 'note': 'articulation symbol in the LilyPond source'},
  {'bar': 30, 'kind': 'prall', 'on': 'B4', 'note': 'articulation symbol in the LilyPond source'},
]
bass_first = []
for bar in range(1, 33):
    bn = [n for n in bass if abs(n['onsetBeats'] - (bar-1)*3) < 1e-6]
    first = min(bn, key=lambda n: n['midi'])
    bass_first.append({'bar': bar, 'name': nm(first['midi']), 'midi': first['midi']})

out = {
 'piece': 'Minuet in G major, BWV Anh. 114',
 'from': 'Notebook for Anna Magdalena Bach (1725)',
 'composer': 'Christian Petzold',
 'key': 'G major', 'time': '3/4', 'bars': 32, 'structure': 'A (bars 1-16, repeated in performance) + B (bars 17-32)',
 'source': {
   'typeset': 'Allen Garvin, Mutopia Project (Mutopia-2017/01/19-75), typeset with LilyPond from the Bach-Gesellschaft edition; header license: Public Domain',
   'workPage': 'https://imslp.org/wiki/Minuet_in_G_major,_BWV_Anh.114_(Pezold,_Christian)',
   'lilypond': 'https://www.mutopiaproject.org/ftp/BachJS/BWVAnh114/anna-magdalena-04/anna-magdalena-04.ly',
   'midi': 'https://www.mutopiaproject.org/ftp/BachJS/BWVAnh114/anna-magdalena-04/anna-magdalena-04.mid',
   'localCopies': ['analysis/score-src/anna-magdalena-04.ly', 'analysis/score-src/anna-magdalena-04.mid'],
   'method': 'This transcription was parsed from the typeset\'s own MIDI render; every note was cross-checked against the LilyPond source text bar by bar.'
 },
 'melody': melody,
 'bassFirstNotePerBar': bass_first,
 'ornamentsNotEncoded': ornaments,
}
json.dump(out, open('minuet_bwv_anh114_transcription.json','w'), indent=1)
print('melody notes:', len(melody), ' bass bars:', len(bass_first), ' ornaments:', len(ornaments))
for bar in range(1, 33):
    ms = [m for m in melody if m['bar'] == bar]
    print(f"bar {bar:2d} mel: " + ' '.join(f"{m['name']}:{m['beats']:g}" for m in ms) + f"   | bass first: {bass_first[bar-1]['name']}")
