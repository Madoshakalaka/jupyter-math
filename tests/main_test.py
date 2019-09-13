from jupyter_math.main import (
    Definition,
    SumOverFiniteSet,
    Probability,
    Intermediate,
    EventSet,
)

Def = Definition
Pr = Probability


def test_stuff():
    E_space = Definition("E", EventSet(["raining", "sunny"]))
    x = Def("x")
    prc = Def("G", SumOverFiniteSet(Pr(x) + Pr(x), E_space, "x"))
    # prc.display()
    prc.display_evaluation(lambda x: x, [Intermediate.EXPAND_OUTER_SUM])
