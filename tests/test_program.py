"""Stage 2: Program execute + complexity on synthetic grids."""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from longquan.program import Program, apply_reflect, apply_recolor, complexity


def test_reflect_then_recolor_synthetic():
    """Acceptance: two-op program reflect -> recolor on a synthetic frame."""
    # 5x5 board; color-1 L in the top-left; bg=0.
    src = np.array(
        [
            [1, 1, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 1, 0, 0],
            [0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0],
        ],
        dtype=int,
    )
    # Reflect across vertical line x=2: cell (0,0)->(4,0), (2,0)->(2,0), ...
    prog = Program.from_ops(
        [
            {"op": "reflect", "axis": "V", "coord": 2},
            {"op": "recolor", "mapping": {1: 7}},
        ]
    )
    out = prog.execute(src)

    # Source L remains (recolored 7) plus its mirror.
    assert out[0, 0] == 7 and out[0, 1] == 7 and out[0, 2] == 7
    assert out[1, 2] == 7 and out[2, 2] == 7
    # Mirror of (0,0) across x=2 is (4,0); of (1,0)->(3,0); of (2,0)->(2,0).
    assert out[0, 4] == 7 and out[0, 3] == 7
    # Mirror of (2,1) and (2,2) stay on x=2 column already checked;
    # mirror of vertical stem (2,y) is itself.
    assert int((out == 7).sum()) == 7  # 5 source + 2 new mirror cells
    assert prog.complexity() == complexity(prog.ops)
    assert prog.complexity() == 2 + (1 + 2) + (1 + 3)  # ops + reflect bits + recolor bits


def test_recolor_only():
    g = np.array([[1, 2], [0, 1]], dtype=int)
    out = apply_recolor(g, mapping={1: 9, 2: 8})
    assert out.tolist() == [[9, 8], [0, 9]]


def test_reflect_drops_oob():
    g = np.zeros((3, 3), dtype=int)
    g[0, 0] = 5
    # Mirror across x=0 sends (0,0) to (0,0); across x=-1 would be OOB for (0,0)->(-2,0).
    out = apply_reflect(g, axis="V", coord=-1)
    assert out[0, 0] == 5
    assert int((out == 5).sum()) == 1


def test_translate_then_reflect_roundtrip_json():
    prog = Program.from_ops(
        [
            {"op": "translate", "dx": 1, "dy": 0},
            {"op": "reflect", "axis": "H", "coord": 1},
        ]
    )
    g = np.zeros((3, 3), dtype=int)
    g[1, 0] = 3
    out = prog.execute(g)
    # translate -> (1,1)=3; reflect H coord=1: (1,1)->(1,1)
    assert out[1, 1] == 3
    again = Program.from_json(prog.to_json())
    assert again.to_json() == prog.to_json()
    assert np.array_equal(again.execute(g), out)


def test_copy_offsets():
    g = np.zeros((4, 4), dtype=int)
    g[0, 0] = 2
    prog = Program.from_ops([{"op": "copy", "offsets": [(2, 0), (0, 2)]}])
    out = prog.execute(g)
    assert out[0, 0] == 2 and out[0, 2] == 2 and out[2, 0] == 2
