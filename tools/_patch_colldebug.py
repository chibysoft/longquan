from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''        dest = None
        for pad in pads:
            if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64):
                continue
            if pad[1] < 34:
                continue
            if near_any(pad, [c for c in ks if c != k], cheb=5) and pad != k:
                # ok to approach k itself for merge
                pass
            nxt = floor_bfs(g, wp, pad, max_step=14)
            if not nxt or nxt == wp:
                continue
            if nxt[1] < 33:
                continue
            # For merge into k, allow cheb<=3 final; else keep sep from other keeper.
            if max(abs(nxt[0] - k[0]), abs(nxt[1] - k[1])) > 3:
                if near_any(nxt, [c for c in cur_now if c != wp], cheb=5):
                    continue
            dest = nxt
            break
        if dest is None:
            print(f"    collapse no-path {wp} toward {k} pads={pads[:4]}")
            continue
'''
new = '''        dest = None
        for pad in pads:
            if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64):
                continue
            if pad[1] < 34:
                continue
            nxt = floor_bfs(g, wp, pad, max_step=14)
            if not nxt or nxt == wp:
                print(f"    collapse skip pad{pad} bfs={nxt}")
                continue
            # Allow interim y>=32 while wrapping hazard; final merge wants y>=34.
            if nxt[1] < 32:
                print(f"    collapse skip pad{pad} nxt{nxt} too north")
                continue
            # Only enforce sep against keepers we are NOT merging into.
            others_sep = [c for c in cur_now if c != wp and c != k]
            if near_any(nxt, others_sep, cheb=5):
                print(f"    collapse skip pad{pad} nxt{nxt} near {others_sep}")
                continue
            dest = nxt
            print(f"    collapse pick pad{pad} nxt{nxt}")
            break
        if dest is None:
            print(f"    collapse no-path {wp} toward {k}")
            continue
'''
if old not in t:
    raise SystemExit('missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('debug collapse ok')
