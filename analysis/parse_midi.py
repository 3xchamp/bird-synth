import json, struct, sys

def read_vlq(data, i):
    v = 0
    while True:
        b = data[i]; i += 1
        v = (v << 7) | (b & 0x7F)
        if not (b & 0x80): return v, i

def parse(path):
    data = open(path,'rb').read()
    assert data[:4] == b'MThd'
    fmt, ntrk, div = struct.unpack('>HHH', data[8:14])
    i = 8 + struct.unpack('>I', data[4:8])[0]
    tracks = []
    for t in range(ntrk):
        assert data[i:i+4] == b'MTrk', (t, data[i:i+4])
        ln = struct.unpack('>I', data[i+4:i+8])[0]
        i += 8
        end = i + ln
        tick = 0; evs = []; running = None; active = {}
        while i < end:
            delta, i = read_vlq(data, i); tick += delta
            b = data[i]
            if b & 0x80: running = b; i += 1
            else: b = running
            typ = b & 0xF0; ch = b & 0x0F
            if b == 0xFF:
                meta = data[i]; i += 1
                ln2, i = read_vlq(data, i)
                payload = data[i:i+ln2]; i += ln2
                if meta == 0x51:
                    evs.append((tick, 'tempo', int.from_bytes(payload,'big')))
                elif meta == 0x03:
                    evs.append((tick, 'trackname', payload.decode('latin1')))
                elif meta == 0x58:
                    evs.append((tick, 'timesig', list(payload)))
                continue
            if b in (0xF0, 0xF7):
                ln2, i = read_vlq(data, i); i += ln2; continue
            if typ in (0xC0, 0xD0):
                i += 1; continue
            d1, d2 = data[i], data[i+1]; i += 2
            if typ == 0x90 and d2 > 0:
                active.setdefault((ch,d1), []).append(tick)
            elif typ == 0x80 or (typ == 0x90 and d2 == 0):
                if (ch,d1) in active and active[(ch,d1)]:
                    on = active[(ch,d1)].pop(0)
                    evs.append((on, 'note', d1, tick-on))
        tracks.append(evs)
        i = end
    return fmt, div, tracks

NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
def nm(m): return NAMES[m % 12] + str(m//12 - 1)

fmt, div, tracks = parse('score-src/anna-magdalena-04.mid')
print('format', fmt, 'division (ticks/quarter)', div, 'tracks', len(tracks))
for ti, evs in enumerate(tracks):
    notes = [e for e in evs if e[1]=='note']
    meta = [e for e in evs if e[1] != 'note']
    print(f'--- track {ti}: {len(notes)} notes, meta: {meta}')
    if notes:
        beats = sorted((e[0]/div, e[2], e[3]/div) for e in notes)
        print('  range: midi', min(b[1] for b in beats), nm(min(b[1] for b in beats)), '..', max(b[1] for b in beats), nm(max(b[1] for b in beats)))
        print('  total beats:', max(b[0]+b[2] for b in beats))

print()
for ti, evs in enumerate(tracks):
    notes = sorted((e[0]/div, e[2], e[3]/div) for e in evs if e[1]=='note')
    if not notes: continue
    print(f'===== track {ti} =====')
    for bar in range(32):
        bn = [n for n in notes if bar*3 <= n[0] < (bar+1)*3]
        s = ' '.join(f'{nm(m)}@{o-bar*3:g}+{d:g}' for o,m,d in bn)
        print(f'bar {bar+1:2d}: {s}')
