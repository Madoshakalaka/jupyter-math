from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import Any, Callable, Iterable, Union, Optional, List

from IPython.display import display as i_display
from IPython.display import Latex
from sympy import latex as sympy_latex, Symbol, FiniteSet
from copy import deepcopy


class Evaluable(ABC):
    @abstractmethod
    def display_evaluation(self, lookup: Callable):
        pass


class Displayable(ABC):
    _power = 1

    def display(self) -> None:
        # noinspection PyTypeChecker
        i_display(Latex("\\[" + self._get_displayable_latex() + "\\]"))

    def __pow__(self, p):
        new = deepcopy(self)
        new._power = p
        return new

    def __add__(self, expr: Union[Any, "Displayable"]):
        return Binary(self, expr, "+")

    def __mul__(self, expr: Union[Any, "Displayable"]):
        return Binary(self, expr, "*")

    def _get_displayable_latex(self, symbolify_defs=True):
        if self._power == 1:
            return self.get_default_latex(symbolify_defs)
        else:
            return self._powered_latex(symbolify_defs)

    @abstractmethod
    def get_default_latex(self, symbolify_defs=True) -> str:
        ...

    def _powered_latex(self, symbolify_defs):
        return rf"{{{self.get_default_latex(symbolify_defs)}}}^{self._power}"

    @classmethod
    def _to_latex(cls, element, symbolify_defs=True):
        if isinstance(element, Displayable):
            if symbolify_defs and isinstance(element, Definition):
                return Displayable._to_latex(element.symbol)

            return element._get_displayable_latex(symbolify_defs)
        else:
            return sympy_latex(element)

    def __iter__(self):
        # finish this with children
        yield self


class Binary(Displayable):
    def __init__(self, l: Union[Displayable, Any], r: Union[Displayable, Any], op: str):
        self._l = l
        self._r = r
        self._op = op

    def get_default_latex(self, symbolify_defs=True) -> str:
        left = Displayable._to_latex(self._l, symbolify_defs)
        right = Displayable._to_latex(self._r, symbolify_defs)
        if isinstance(self._l, Binary):
            left = "(" + left + ")"
        if isinstance(self._r, Binary):
            right = "(" + right + ")"
        op = self._op
        if self._op == "*":
            op = r"\times"
        return rf"{left} {op} {right}"


class Event(Displayable):
    def __init__(self, desc: str):
        self._desc = desc

    def get_default_latex(self, symbolify_defs=True) -> str:
        return "\\text{%s}" % self._desc

    def __hash__(self):
        return self._desc.__hash__()

    def __eq__(self, other):
        if isinstance(other, Event):
            return self._desc == other._desc
        else:
            return False


class EventSet(Displayable):
    def __init__(self, events: Iterable[Union[Event, Any]]):
        parsed_events = []
        for e in events:
            if not isinstance(e, Event):
                e = Event(e)
            parsed_events.append(e)

        self._events = set(parsed_events)

    def get_default_latex(self, symbolify_defs=True) -> str:
        return (
            "\\{"
            + ",\\;".join((e.get_default_latex(symbolify_defs) for e in self._events))
            + "\\}"
        )

    def __len__(self):
        return len(self._events)

    def __iter__(self) -> Iterable[Event]:
        return self._events.__iter__()


class Intermediate(Enum):
    EXPAND_OUTER_SUM = auto()
    SUBSTITUTE_ALL = auto()


class Definition(Displayable):
    def __init__(self, ls, rs: Optional = None, comment: str = ""):

        if isinstance(ls, str):
            ls = Symbol(ls)
        self._ls = ls
        self._rs = rs
        self._comment = comment

    @property
    def symbol(self):
        return self._ls

    def _to_latex(self, element, symbolify_defs=True):
        super(Definition, self)._to_latex(self, symbolify_defs=False)

    def get_default_latex(self, symbolify_defs=True) -> str:
        latex_string = f"{Displayable._to_latex(self._ls, False)} = {Displayable._to_latex(self._rs)}"
        if self._comment:
            latex_string += f"\\quad \\text{{{self._comment}}}"
        return latex_string

    def get_evaluation_latex(self) -> str:
        latex_string = f"{Displayable._to_latex(self._ls, False)} & = {Displayable._to_latex(self._rs)}"
        return latex_string

    def display_evaluation(
        self, lookup: Callable, intermediates: Iterable[Intermediate]
    ):

        line_latex = [self.get_evaluation_latex()]

        start = r"""\begin{equation} \label{eq1}
\begin{split}
"""
        end = r"""\end{split}
\end{equation}
        """

        for inter in intermediates:
            if inter is Intermediate.EXPAND_OUTER_SUM and isinstance(
                self._rs, SumOverFiniteSet
            ):
                self._rs.expand()

        # noinspection PyTypeChecker
        i_display(Latex(start + r"\\ & = ".join(line_latex) + end))


class Probability(Displayable):
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

    def get_default_latex(self, symbolify_defs=True):
        expr_0 = self._event
        if isinstance(self._event, Definition):
            expr_0 = self._event.symbol

        if self._condition is None:

            return rf"\Pr(\,{Displayable._to_latex(expr_0)}\,)"
        else:

            expr_1 = self._condition
            if isinstance(self._condition, Definition):
                expr_1 = self._condition.symbol

            return rf"\Pr(\,{Displayable._to_latex(expr_0)} \mid {Displayable._to_latex(expr_1)}\,)"


class SumOverFiniteSet(Displayable):
    def __init__(self, f: Any, event_set: EventSet, tmp_var: str):
        self._tmp_var = Symbol(tmp_var)
        self._f = f
        self._set = event_set

    def get_default_latex(self, symbolify_defs=True) -> str:
        event_set = self._set
        if isinstance(event_set, Definition):
            event_set = event_set.symbol

        return rf"\sum_{{{Displayable._to_latex(self._tmp_var)} \in {Displayable._to_latex(event_set)}}} {Displayable._to_latex(self._f)}"

    def expand(self) -> Displayable:
        event_set_size = len(self._set)
        if event_set_size == 1:
            raise NotImplementedError()
        else:
            old_event = None
            for event in self._set:
                if old_event is not None:
                    if not isinstance(self._f, Displayable):
                        raise NotImplementedError()
                    else:
                        pass
                old_event = event
            aggregate = Binary()


class TallBrace(Displayable):
    def __init__(self, elements: Iterable[Union[Displayable, Any]]):
        self._elements = elements

    def get_default_latex(self, symbolify_defs=True) -> str:
        start = r"""\left\{
                \begin{array}{ll}"""
        end = r"""
                \end{array}
              \right."""

        element_strings = []
        for element in self._elements:
            if isinstance(element, Displayable):
                element_strings.append(element.get_default_latex(symbolify_defs))
            else:
                element_strings.append(sympy_latex(element))

        return start + r"\\".join(element_strings) + end
