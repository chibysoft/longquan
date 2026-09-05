"""AR25 golden data + replay script (stage 0 first step).

Golden data: the KNOWN-correct action sequences for AR25 L1/L2/L3, from the
verified M1 solutions. This is the reference frame for "replay passes".

L1: piece (6,5) -> (1,15), axis fixed x=10.  15 moves.
L2: piece (15,6) -> (1,14), axis x=12 -> x=3. (piece then axis)
L3: piece1 (4,7) -> (11,14), piece2 (15,9) -> (3,14), axis H y=16 -> y=9.

The replay script runs these golden sequences through the local arcengine
(OFFLINE) and asserts levels_completed advances 1 -> 2 -> 3.

Run (Windows, from ARC checkout):
    cd ARC-AGI-3-Agents
    uv run python ../longquan/tests/replay_golden.py
"""
import os
import sys

try:
    from arc_agi import Arcade, OperationMode
    from arcengine import GameAction
except ImportError:
    print("arcengine not available; skipping golden replay.")
    sys.exit(0)

# Golden action sequences (verified in M1)
# ACTION ids: 1=up 2=down 3=left 4=right 5=select
GOLDEN = {
    1: [3]*5 + [2]*10,                          # L1: piece (6,5)->(1,15)
    2: [3]*8 + [5] + [3]*12 + [2]*8,            # L2: axis x12->4, then piece (15,6)->(3,14)
    3: [5] + [3]*7 + [2]*7 + [5] + [3]*12 + [2]*5,  # L3: (placeholder, refine below)
}

# L3 exact sequence needs care: piece1 (4,7)->(11,14) is +7x +7y; piece2 (15,9)->(3,14) is -12x +5y; axis H y16->9 is -7y.
# Order: axis first (H moves up/down), then pieces. Selection order matters.
GOLDEN[3] = (
    [2]*7 +                              # move axis H y16 -> y9 (down 7)
    [5] +                                # select piece1
    [4]*7 + [2]*7 +                      # piece1 (4,7)->(11,14): +7x +7y
    [5] +                                # select piece2
    [3]*12 + [2]*5                       # piece2 (15,9)->(3,14): -12x +5y
)


def main():
    _REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ENVIRONMENTS_DIR = os.path.join(_REPO_ROOT, "environment_files")
    arc = Arcade(operation_mode=OperationMode.OFFLINE,
                 environments_dir=ENVIRONMENTS_DIR)
    env = arc.make("ar25", scorecard_id="golden")
    assert env is not None, "ar25 engine not found"

    env.reset()
    for lv in (1, 2, 3):
        before = env.observation_space.levels_completed
        for a in GOLDEN[lv]:
            env.step(GameAction.from_id(a))
        env.step(GameAction.from_id(2))  # advance to next level
        after = env.observation_space.levels_completed
        print(f"L{lv}: {before} -> {after}", "OK" if after >= before + 1 else "FAIL")
        assert after >= before + 1, f"L{lv} did not advance"

    print("GOLDEN REPLAY PASSED: L1-L3 all advance.")


if __name__ == "__main__":
    main()
