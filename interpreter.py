import operator
from dataclasses import dataclass, field
from functools import partial

from lark import Lark, Transformer


@dataclass
class Scope:
    current: dict
    outer: "Scope" = field(default=None)

    def get_value(self, symbol):
        if symbol in self.current:
            return self.current[symbol]
        return self.outer.get_value(symbol)


def cond(scope, *branches):
    for (predicate, action) in branches:
        if evaluate(scope, predicate):
            return evaluate(scope, action)


def lambda_(scope, arg_names, body):
    return lambda *args: evaluate(Scope(dict(zip(arg_names, args)), scope), body)


def let(scope, variables, instructions):
    variables = {name: evaluate(scope, value) for name, value in variables}
    return evaluate(Scope(variables, scope), instructions)


builtins = {
    "atom": lambda obj: type(obj) != list,
    "car": lambda arr: arr[0],
    "cdr": lambda arr: arr[1:],
    "cons": lambda obj, arr: [obj] + arr,
    "eq": operator.eq,
    "quote": lambda _, x: x,
    "cond": cond,
    "lambda": lambda_,
    "let": let,
    "f": False,
    "t": True,
    "nil": [],
    "write-line": print,
    # Basic math operations
    "add": operator.add,
    "sub": operator.sub,
    "mul": operator.mul,
    "div": operator.truediv,
    "gt": operator.gt,
    "lt": operator.lt,
    "ge": operator.ge,
    "le": operator.le,
}


class DropNodes(Transformer):
    def start(self, children):
        return children

    def list(self, elements):
        return elements


parser = Lark(
    """
start: _s_expression*
_s_expression: _atom
            | list
list: "(" _s_expression* ")"
_atom: STRING | INT | FLOAT | SYMBOL
STRING: /".*?"/
SYMBOL: /[^\s()\"]+/

%import common.INT
%import common.FLOAT
%import common.WORD
%import common.WS
%ignore WS
""",
    parser="lalr",
    transformer=DropNodes(),
)


special_forms = ["quote", "cond", "lambda", "let"]
is_symbol = lambda obj: obj.type == "SYMBOL"


def eval_list(scope, head, *tail):
    fst = evaluate(scope, head)
    if head in special_forms:
        return scope.get_value(head)(scope, *tail)

    tail = map(partial(evaluate, scope), tail)
    if callable(fst):
        return fst(*tail)
    return [fst, *tail]


def evaluate(scope, obj):
    if type(obj) == list:
        return eval_list(scope, *obj)
    elif obj.type == "SYMBOL":
        return scope.get_value(obj)
    elif obj.type == "STRING":
        return obj.value[1:-1]
    elif obj.type == "INT":
        return int(obj)
    elif obj.type == "FLOAT":
        return float(obj)


def interpret(code):
    for obj in parser.parse(code):
        evaluate(Scope(builtins), obj)
