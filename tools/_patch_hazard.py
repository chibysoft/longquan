from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''        ks = sorted(cur_now, key=lambda w: (-w[0], -w[1]))[:2]
        k = min(ks, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
        # Prefer BFS hop toward a corridor pad near keeper (avoid y<34 trap).
        pads = [(k[0], k[1]), (k[0] - 3, 34), (k[0] + 3, 34), (k[0], 34)]
        dest = None
        for pad in pads:
            if not (0 <= pad[0] < 64 and 0 <= pad[1] < 64):
                continue
            if pad[1] < 34:
                continue
            nxt = floor_bfs(g, wp, pad, max_step=8)
            if not nxt or nxt == wp:
                continue
            if nxt[1] < 34:
                continue
            dest = nxt
            break
        if dest is None:
            print(f"    collapse no-path {wp}→{k}")
            continue
'''
new = '''        # Only corridor keepers — shallow straggler must walk around hazard.
        ks = [c for c in cur_now if c[1] >= 34]
        if not ks:
            continue
        k = min(ks, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
        # Shallow @y~24 is north of hazard band; go west/east then south.
        pads = [
            k,
            (14, 36),
            (20, 34),
            (28, 34),
            (24, 34),
            (k[0] - 3, 34),
            (k[0] + 3, 34),
        ]
        dest = None
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
if old not in t:
    raise SystemExit('missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('hazard bypass ok')
