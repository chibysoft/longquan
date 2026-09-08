from pathlib import Path
p = Path(__file__).with_name("r11l_l3_2wp_probe.py")
t = p.read_text(encoding="utf-8")
t = t.replace("def run_probe(dx_list=(6, 8)):", "def run_probe(dx_list=(6, 6, 6, 8)):", 1)
t = t.replace(
    """    for dx in dx_list:
        if step_budget(d["frame"]) < 8:
            break
        if success_gate(info):
            break
        print(f"--- translate dx={dx} ---")
""",
    """    for round_i, dx in enumerate(dx_list):
        if step_budget(d["frame"]) < 8:
            break
        if success_gate(info):
            break
        print(f"--- translate round{round_i} dx={dx} ---")
""",
    1,
)
p.write_text(t, encoding="utf-8")
print("ok")
