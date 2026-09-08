from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
old = '''            # Allow interim y>=32 while wrapping hazard; final merge wants y>=34.
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
'''
new = '''            if nxt[1] < 32:
                print(f"    collapse skip pad{pad} nxt{nxt} too north")
                continue
            # Collapse INTENTIONALLY merges into a keeper — only avoid freeze15.
            if near_any(nxt, freeze15, cheb=5):
                print(f"    collapse skip pad{pad} nxt{nxt} near freeze")
                continue
            dest = nxt
            print(f"    collapse pick pad{pad} nxt{nxt}")
            break
'''
if old not in t:
    raise SystemExit('missing')
p.write_text(t.replace(old, new, 1), encoding='utf-8')
print('merge-into-keeper ok')
