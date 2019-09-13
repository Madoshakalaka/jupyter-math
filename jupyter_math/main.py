from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Callable, Iterable, Union, Optional, List

from IPython.display import display as i_display, Math
from IPython.display import Latex
from sympy import latex as sympy_latex, Symbol, FiniteSet
from copy import deepcopy


class Displayable(ABC):
    _power = 1
    _numeric = None

    def real(self):
        if isinstance(self, Definition):
            return self.rs
        else:
            return self

    def display(self) -> None:
        # noinspection PyTypeChecker
        i_display(Latex("\\[" + self._get_displayable_latex() + "\\]"))

    def _substituted(self, lookup: Callable):
        new = deepcopy(self)
        for child in new:
            number = lookup(child)
            if number is not None:
                child.numeric = number ** child._power
        return new

    def _try_get_value(self) -> Optional[float]:
        return self.numeric

    @property
    def numeric(self):
        return self._numeric

    @numeric.setter
    def numeric(self, value):
        self._numeric = value

    def substitute_defs(self, def_var: Union[str, Any], new: Union["Displayable", Any]):
        for child in self:
            if child.is_unresolved_def():

                child: Definition
                if child.same_symbol(def_var):

                    child.resolve(new)

    def is_unresolved_def(self):
        return isinstance(self, Definition) and not self.resolved

    @property
    @abstractmethod
    def children(self) -> Iterable["Displayable"]:
        ...

    def __pow__(self, p):
        new = deepcopy(self)
        new._power = p
        return new

    def __add__(self, expr: Union[Any, "Displayable"]):
        return Binary(self, expr, "+")

    def __mul__(self, expr: Union[Any, "Displayable"]):
        return Binary(self, expr, "*")

    def _get_displayable_latex(self, symbolify_defs=True, **kwargs):
        if kwargs.get("numerify_descendents", False) and self.numeric:
            return str(round(self.numeric, 3))
        if self._power == 1:
            return self.get_default_latex(symbolify_defs, **kwargs)
        else:
            return self._powered_latex(symbolify_defs)

    @abstractmethod
    def get_default_latex(self, symbolify_defs=True, numerify_descendents=False) -> str:
        ...

    def _powered_latex(self, symbolify_defs, **kwargs):
        return rf"{{{self.get_default_latex(symbolify_defs, **kwargs)}}}^{self._power}"

    @classmethod
    def _to_latex(cls, element, symbolify_defs=True, numerify_descendents=False):
        if isinstance(element, Displayable):
            if isinstance(element, Definition):
                return element.def_to_latex(symbolify_defs)

            return element._get_displayable_latex(
                symbolify_defs, numerify_descendents=numerify_descendents
            )
        else:
            return sympy_latex(element)

    def __iter__(self):
        yield self

        for child in self.children:
            yield from child

    def __hash__(self):
        return id(self)

    def __eq__(self, other):
        return self is other


class Binary(Displayable):
    def _try_get_value(self) -> Optional[float]:
        if self.numeric:
            return self.numeric
        else:
            l_v = self._l._try_get_value()
            r_v = self._r._try_get_value()
            if l_v and r_v:
                if self._op == "*":
                    return l_v * r_v
                elif self._op == "+":
                    return l_v + r_v
                else:
                    raise NotImplementedError()

    @property
    def children(self) -> Iterable["Displayable"]:
        return [self._l, self._r]

    def __init__(self, l: Union[Displayable, Any], r: Union[Displayable, Any], op: str):
        self._l = l
        self._r = r
        self._op = op

    def get_default_latex(self, symbolify_defs=True, **kwargs) -> str:
        left = Displayable._to_latex(self._l, symbolify_defs, **kwargs)
        right = Displayable._to_latex(self._r, symbolify_defs, **kwargs)
        if isinstance(self._l, Binary):
            left = "(" + left + ")"
        if isinstance(self._r, Binary):
            right = "(" + right + ")"
        op = self._op
        if self._op == "*":
            op = r"\times"
        return rf"{left} {op} {right}"


class Event(Displayable):
    @property
    def children(self) -> Iterable["Displayable"]:
        return []

    def __init__(self, desc: str):
        self._desc = desc

    def get_default_latex(self, symbolify_defs=True, **kwargs) -> str:
        return "\\text{%s}" % self._desc

    def __hash__(self):
        return self._desc.__hash__()

    def __eq__(self, other):
        if isinstance(other, Event):
            return self._desc == other._desc
        else:
            return False


class EventSet(Displayable):
    @property
    def children(self) -> Iterable["Displayable"]:
        return self._events

    def __init__(self, events: Iterable[Union[Event, Any]]):
        parsed_events = []
        for e in events:
            if not isinstance(e, Event):
                e = Event(e)
            parsed_events.append(e)

        self._events = set(parsed_events)

    def get_default_latex(self, symbolify_defs=True, **kwargs) -> str:
        return (
            "\\{"
            + ",\\;".join(
                (e.get_default_latex(symbolify_defs, **kwargs) for e in self._events)
            )
            + "\\}"
        )

    def __len__(self):
        return len(self._events)

    def __iter__(self) -> Iterable[Event]:
        return self._events.__iter__()


class Intermediate(Enum):
    EXPAND_OUTER_SUM = auto()
    SUBSTITUTE_ALL = auto()
    GET_RESULT = auto()


class Definition(Displayable):
    @property
    def rs(self):
        return self._rs.real()

    def same_symbol(self, target: Union[str, "Definition"]):
        if isinstance(target, Definition):
            target_str = str(target._ls)
        else:
            target_str = str(target)

        return str(self._ls).strip() == target_str.strip()

    @property
    def children(self) -> Iterable["Displayable"]:
        if self._rs:
            return [self._rs]
        else:
            return []

    @property
    def resolved(self):
        return self._resolved

    def resolve(self, new):
        self._rs = new
        self._resolved = True

    def __init__(self, ls, rs: Optional = None, comment: str = ""):

        if isinstance(ls, str):
            ls = Symbol(ls)
        self._ls = ls
        self._rs = rs
        self._comment = comment

        self._resolved = False

    def display(self) -> None:
        # noinspection PyTypeChecker
        i_display(Latex("\\[" + self.def_to_latex(symbolify_defs=False) + "\\]"))

    @property
    def symbol(self):
        return self._ls

    def def_to_latex(self, symbolify_defs=True, **kwargs):
        return self.get_default_latex(symbolify_defs, **kwargs)

    def get_default_latex(self, symbolify_defs=True, **kwargs) -> str:

        if not self._resolved:
            if not symbolify_defs:
                latex_string = f"{Displayable._to_latex(self._ls, False)} = {Displayable._to_latex(self._rs)}"
            else:
                latex_string = f"{Displayable._to_latex(self._ls, False)}"
            if self._comment:
                latex_string += f"\\quad \\text{{{self._comment}}}"
            return latex_string
        else:
            return Displayable._to_latex(self._rs)

    def get_evaluation_latex(self) -> str:
        latex_string = f"{Displayable._to_latex(self._ls, False)} &= {Displayable._to_latex(self._rs)}"
        return latex_string

    def display_evaluation(
        self, lookup: Callable, intermediates: Iterable[Intermediate]
    ):

        line_latex = [
            self.get_evaluation_latex()
            # r"0.4 \times {0.2}^2 + {0.8}^2 + 0.6 \times {0.3}^2 + {0.7}^2",
        ]

        start = r"""\begin{align}

"""
        end = r"""
        
\end{align}
        """

        current_expr = self._rs

        for inter in intermediates:
            if inter is Intermediate.EXPAND_OUTER_SUM and isinstance(
                current_expr, SumOverFiniteSet
            ):
                current_expr = current_expr.expand()
                line_latex.append(Displayable._to_latex(current_expr))
            if inter is Intermediate.SUBSTITUTE_ALL:
                current_expr: Displayable
                current_expr = current_expr._substituted(lookup)

                line_latex.append(
                    Displayable._to_latex(current_expr, numerify_descendents=True)
                )
            if inter is Intermediate.GET_RESULT:
                line_latex.append(str(round(current_expr._try_get_value(), 3)))

        # noinspection PyTypeChecker
        i_display(Math(start + "\\\\ \n &= ".join(line_latex) + end))


class Probability(Displayable):
    def __hash__(self):
        c = self._condition
        if self._condition:
            c = self._condition.real()

        return self._event.real().__hash__() ^ c.__hash__()

    def __eq__(self, other):
        if isinstance(other, Probability):
            c = self._condition
            if self._condition:
                c = self._condition.real()
            other_c = other._condition
            if other_c is not None:
                other_c = other_c.real()
            return other._event.real() == self._event.real() and other_c == c
        else:
            return False

    @property
    def children(self) -> Iterable["Displayable"]:
        res = [self._event]
        if self._condition:
            res.append(self._condition)
        return res

    def __init__(
        self,
        event: Union[Event, str, Definition],
        condition: Union[Event, str, None, Definition] = None,
    ):
        if isinstance(event, str):
            event = Event(event)
        if isinstance(condition, str):
            condition = Event(condition)

        self._event = event
        self._condition = condition

    def get_default_latex(self, symbolify_defs=True, **kwargs):
        expr_0 = self._event

        if self._condition is None:

            return rf"\Pr(\,{Displayable._to_latex(expr_0)}\,)"
        else:

            expr_1 = self._condition

            return rf"\Pr(\,{Displayable._to_latex(expr_0)} \mid {Displayable._to_latex(expr_1)}\,)"


class SumOverFiniteSet(Displayable):
    @property
    def children(self) -> Iterable["Displayable"]:
        return [self._f, self._set]

    def __init__(self, f: Any, event_set: Union[EventSet, Definition], tmp_var: str):
        self._tmp_var = Symbol(tmp_var)
        self._f = f
        self._set = event_set

    def get_default_latex(self, symbolify_defs=True, **kwargs) -> str:
        event_set = self._set
        if isinstance(event_set, Definition):
            event_set = event_set.symbol

        return rf"\sum_{{{Displayable._to_latex(self._tmp_var)} \in {Displayable._to_latex(event_set)}}} {Displayable._to_latex(self._f)}"

    def expand(self) -> Displayable:
        # todo: this
        resolved_set = self._set
        if isinstance(self._set, Definition):
            resolved_set = self._set.rs
        event_set_size = len(resolved_set)
        if event_set_size == 1:
            raise NotImplementedError()
        else:
            aggregate = None

            for event in resolved_set:

                if aggregate is not None:
                    if not isinstance(self._f, Displayable):
                        raise NotImplementedError()
                    else:
                        summand = deepcopy(self._f)
                        summand.substitute_defs(self._tmp_var, event)
                    aggregate = Binary(aggregate, summand, "+")
                else:
                    aggregate = deepcopy(self._f)
                    aggregate.substitute_defs(self._tmp_var, event)
        return aggregate


class TallBrace(Displayable):
    @property
    def children(self) -> Iterable["Displayable"]:
        return self._elements

    def __init__(self, elements: Iterable[Union[Displayable, Any]]):
        self._elements = elements

    def get_default_latex(self, symbolify_defs=True, **kwargs) -> str:
        start = r"""\left\{
                \begin{array}{ll}"""
        end = r"""
                \end{array}
              \right."""

        element_strings = []
        for element in self._elements:
            if isinstance(element, Displayable):
                element_strings.append(
                    element.get_default_latex(symbolify_defs, **kwargs)
                )
            else:
                element_strings.append(sympy_latex(element))

        return start + r"\\".join(element_strings) + end
