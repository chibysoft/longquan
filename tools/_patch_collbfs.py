from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''        k = min(ks, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
        # Land at cheb=3 from keeper.
        dest = wp
        for _ in range(8):
            if max(abs(k[0] - dest[0]), abs(k[1] - dest[1])) <= 3:
                break
            dx = 0 if k[0] == dest[0] else (1 if k[0] > dest[0] else -1)
            dy = 0 if k[1] == dest[1] else (1 if k[1] > dest[1] else -1)
            nxt = (dest[0] + dx, dest[1] + dy)
            if not (0 <= nxt[0] < 64 and 0 <= nxt[1] < 64):
                break
            if int(g[nxt[1], nxt[0]]) in (2, 10):
                break
            dest = nxt
        if dest == wp:
            continue
        if dest[1] < 34:
            continue  # never collapse into shallow
'''
new = '''        k = min(ks, key=lambda p: max(abs(p[0] - wp[0]), abs(p[1] - wp[1])))
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
if old not in t:
    raise SystemExit('collapse walk missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('collapse bfs ok')
