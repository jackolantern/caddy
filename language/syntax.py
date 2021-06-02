import sys
import types
import numpy as np
from pretty import pprint, pretty

class Block:
    def __init__(self, statements, expression):
        self.expression = expression
        self.statements = statements

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text("{")
        with p.group(4):
            p.breakable()
            for s in self.statements:
                p.pretty(s)
                p.breakable()
            p.pretty(self.expression)
        p.breakable()
        p.text("}")

class Reference:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def copy(self):
        return Reference(self.name, self.value)

    def run(self):
        value = self.value
        while isinstance(value, Reference):
            if value == self.value:
                raise Exception(f"Cyclic reference detected ({self.name}).")
            value = self.value
        return value.run()

    def substitute(self, pairs, threshold):
        return Reference(self.name, self.value.substitute(pairs, threshold))

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        if p.verbose:
            p.pretty(self.value)
        else:
            p.text(self.name)

class UnaryOperation:
    def __init__(self, op, expression):
        self.op = op
        self.expression = expression

    def substitute(self, pairs, threshold):
        return UnaryOperation(self.op, self.expression.substitute(pairs, threshold))

    def run(self):
        value = self.expression.run()
        if self.op == "+":
            return value
        elif self.op == "-":
            return -value
        elif self.op == "~":
            return ~value
        elif self.op == "!":
            return not value

class BinaryOperation:
    def __init__(self, op, lhs, rhs):
        self.op = op
        self.lhs = lhs
        self.rhs = rhs

    def run(self):
        lhs = self.lhs.run()
        rhs = self.rhs.run()
        if self.op == "+":
            return lhs + rhs
        elif self.op == "-":
            return lhs - rhs
        elif self.op == "*":
            return lhs * rhs
        elif self.op == "/":
            return lhs / rhs
        elif self.op == "^":
            return lhs ** rhs
        elif self.op == "%":
            return lhs % rhs
        elif self.op == "==":
            return Bool(lhs == rhs)
        elif self.op == "<":
            return Bool(lhs < rhs)
        elif self.op == ">":
            return Bool(lhs > rhs)
        elif self.op == "<=":
            return Bool(lhs <= rhs)
        elif self.op == ">=":
            return Bool(lhs >= rhs)

    def substitute(self, pairs, threshold):
        return BinaryOperation(
            self.op,
            self.lhs.substitute(pairs, threshold),
            self.rhs.substitute(pairs, threshold))

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        with p.group(2, "(", ")"):
            p.pretty(self.lhs)
            p.text(" ")
            p.text(self.op)
            p.text(" ")
            p.pretty(self.rhs)

class Value:
    def __init__(self, value):
        super().__init__()
        self.value = value

    def run(self):
        return self

    def substitute(self, pairs, threshold):
        return self

    def __eq__(self, other):
        return self.value == other.value

    def __ne__(self, other):
        return self.value != other.value

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.pretty(self.value)

class Bound:
    def __init__(self, name, index):
        self.name = name
        self.index = index

    def run(self):
        return self

    def substitute(self, pairs, threshold):
        if self.index < threshold:
            return self
        index = self.index - threshold
        (name, value) = pairs[index]
        return value

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        if p.verbose:
            p.text(f"<{self.name} : {self.index}>")
        else:
            p.text(self.name)

class Variable:
    def __init__(self, name):
        self.name = name
        # TODO: no.
        self.value = self

    def run(self):
        return self

    def substitute(self, pairs, threshold):
        return self

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        if p.verbose:
            p.text("var:")
            p.text(self.name)
        else:
            p.text(self.name)

class Bool(Value):
    def __eq__(self, other):
        if isinstance(other, Bool):
            return Bool(self.value == other.value)
        return Bool(False)

    def __ne__(self, other):
        if isinstance(other, Bool):
            return Bool(self.value != other.value)
        return Bool(False)

def Number(value):
    if isinstance(value, (int, np.int64)):
        return Int(value)
    elif isinstance(value, (float, np.float32, np.float64)):
        return Float(value)
    else:
        raise Exception(f"Expected either an integer or a float, but '{value}' has type '{type(value)}'")

class Int(Value):
    def __neg__(self):
        return Int(-self.value)

    def __mod__(self, other):
        if isinstance(other, Float):
            return Float(self.value % other.value)
        elif isinstance(other, Int):
            return Int(self.value % other.value)
        else:
            raise Exception(f"Addition not defined between 'int' and '{type(other).name}'.")

    def __pow__(self, other):
        if isinstance(other, Float):
            return Float(self.value ** other.value)
        elif isinstance(other, Int):
            return Int(self.value ** other.value)
        else:
            raise Exception(f"Addition not defined between 'int' and '{type(other).name}'.")

    def __add__(self, other):
        if isinstance(other, Float):
            return Float(self.value + other.value)
        elif isinstance(other, Int):
            return Int(self.value + other.value)
        else:
            raise Exception(f"Addition not defined between 'int' and '{type(other).name}'.")

    def __sub__(self, other):
        if isinstance(other, Float):
            return Float(self.value - other.value)
        elif isinstance(other, Int):
            return Int(self.value - other.value)
        else:
            raise Exception(f"Subtraction not defined between 'int' and '{type(other).name}'.")

    def __mul__(self, other):
        if isinstance(other, Float):
            return Float(self.value * other.value)
        elif isinstance(other, Int):
            return Int(self.value * other.value)
        else:
            raise Exception(f"Multiplication not defined between 'float' and '{type(other)}'.")

    def __truediv__(self, other):
        return Float(float(self.value) / float(other.value))

    def assign_to(self, target_type):
        if target_type == Int:
            return self
        elif target_type == Float:
            return Float(float(self.value))
        else:
            return None

class Float(Value):
    def __neg__(self):
        return Float(-self.value)

    def __pow__(self, other):
        if isinstance(other, (Int, Float)):
            return Float(self.value ** other.value)
        else:
            raise Exception(f"Addition not defined between 'int' and '{type(other).name}'.")

    def __mod__(self, other):
        if isinstance(other, (Int, Float)):
            return Float(self.value % other.value)
        else:
            raise Exception(f"Addition not defined between 'int' and '{type(other).name}'.")

    def __add__(self, other):
        if isinstance(other, Float):
            return Float(self.value + other.value)
        elif isinstance(other, Int):
            return Float(self.value + float(other.value))
        else:
            raise Exception(f"Addition not defined between 'float' and '{type(other).name}'.")

    def __sub__(self, other):
        if isinstance(other, Float):
            return Float(self.value - other.value)
        elif isinstance(other, Int):
            return Float(self.value - float(other.value))
        else:
            raise Exception(f"Subtraction not defined between 'float' and '{type(other).name}'.")

    def __mul__(self, other):
        if isinstance(other, Float):
            return Float(self.value * other.value)
        elif isinstance(other, Int):
            return Float(self.value * float(other.value))
        else:
            raise Exception(f"Multiplication not defined between 'float' and '{type(other)}'.")

    def __truediv__(self, other):
        if isinstance(other, Float):
            return Float(self.value / other.value)
        elif isinstance(other, Int):
            return Float(self.value / float(other.value))
        else:
            raise Exception(f"Division not defined between 'float' and '{type(other)}'.")

class String(Value):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

    def __add__(self, other):
        if not isinstance(other, String):
            raise Exception("Concatenation not defined between string and '{type(other)}'.")
        return String(self.value + other.value)

class IfThenElse:
    def __init__(self, test, true, false):
        self.test = test
        self.true = true
        self.false = false

    def run(self):
        test = self.test.run()
        if isinstance(test, Bool):
            if test.value:
                return self.true.run()
            return self.false.run()
        raise Exception("Expected a bool.")

    def substitute(self, pairs, threshold):
        test = self.test.substitute(pairs, threshold)
        true = self.true.substitute(pairs, threshold)
        false = self.false.substitute(pairs, threshold)
        return IfThenElse(test, true, false)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text("if ")
        p.pretty(self.test)
        p.breakable()
        p.text("then ")
        p.pretty(self.true)
        p.breakable()
        p.text("else ")
        p.pretty(self.false)

class FunctionDef:
    def __init__(self, parameters, body):
        self.body = body
        self.parameters = parameters

    def is_builtin(self):
        t = type(self.body)
        return t in (types.FunctionType, types.MethodType) or t.__name__ == 'builtin_function_or_method'

    def _repr_pretty_(self, p, cycle):
        p.text("function(")
        for idx, param in enumerate(self.parameters):
            p.text(param.name)
            if param.typ:
                p.text(" : ")
                p.pretty(param.typ)
            if idx < len(self.parameters) - 1:
                p.text(", ")
        p.text(") ")
        p.text("{")
        with p.group(4):
            p.breakable()
            p.pretty(self.body)
        p.breakable()
        p.text("}")

class FunctionRef(FunctionDef):
    def run(self):
        return self

    def call(self, arguments):
        an = len(arguments)
        pn = len(self.parameters)
        if an != pn:
            raise Exception(f"The function takes {pn} arguments, not {an}.")
        pairs = [("this", self)] + list(zip([p.name for p in self.parameters], arguments))
        body = self.body.substitute(pairs, 0)
        return body.run()

    def substitute(self, pairs, threshold):
        if self.is_builtin():
            return self
        return FunctionRef(self.parameters, self.body.substitute(pairs, threshold + len(self.parameters) + 1))

class Parameter:
    def __init__(self, name, typ):
        self.typ = typ
        self.name = name

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text(self.name)
        p.text(" : ")
        if self.typ:
            p.pretty(self.typ)
        else:
            p.text('Any')

class Call:
    def __init__(self, expression, arguments):
        self.arguments = arguments
        self.expression = expression

    def run(self):
        expression = self.expression
        while not isinstance(expression, FunctionRef):
            previous = expression
            expression = expression.run()
            if expression == previous:
                pprint(expression, verbose=True)
                raise Exception(f"Expected a function, not a '{type(expression)}'.")
        result = expression.call(self.arguments)
        return result.run()

    def substitute(self, pairs, threshold):
        arguments = [arg.substitute(pairs, threshold) for arg in self.arguments]
        expression = self.expression.substitute(pairs, threshold)
        return Call(expression, arguments)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.pretty(self.expression)
        p.text("(")
        for idx, arg in enumerate(self.arguments):
            if idx:
                p.text(", ")
            p.pretty(arg)
        p.text(")")

class Lookup:
    def __init__(self, expression, var):
        self.var = var
        self.expression = expression

    def run(self):
        ns = self.expression.run()
        definition = ns.lookup(self.var.name)
        return definition.value.run()

    def substitute(self, pairs, threshold):
        return Lookup(self.expression.substitute(pairs, threshold), self.var)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        if isinstance(self.expression, (Bound, Variable, Reference)):
            p.text(self.expression.name)
        else:
            p.pretty(self.expression)
        p.text("::")
        p.text(self.var.name)

class Namespace:
    def __init__(self, definitions):
        self.definitions = definitions

    def lookup(self, name):
        for d in self.definitions:
            if d.name == name:
                return d
        raise Exception(f"The namespace does not define a symbol named '{name}'.")

    def run(self):
        return self

    def substitute(self, pairs, threshold):
        return Namespace([d.substitute(pairs, threshold) for d in self.definitions])

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text("namespace {")
        with p.group(4):
            p.breakable()
            for d in self.definitions:
                p.pretty(d)
                p.breakable()
        p.breakable()
        p.text("}")

class NamespaceDefinition:
    def __init__(self, name, value):
        self.name = name
        self.value = value

    def substitute(self, pairs, threshold):
        return NamespaceDefinition(self.name, self.value.substitute(pairs, threshold))

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text(self.name)
        p.text(" = ")
        p.pretty(self.value)
        p.text(";")

class Import:
    def __init__(self, path, program):
        self.path = path
        self.program = program

class Bang:
    def __init__(self, expression):
        self.expression = expression

    def run(self):
        value = self.expression.run()
        return value

    def bang(self):
        value = self.expression.run()
        pprint(value)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text("!")
        p.pretty(self.expression)

class Assignment:
    def __init__(self, name, expression):
        self.name = name
        self.expression = expression

    def _repr_pretty_(self, p, cycle):
        p.text("let ")
        p.text(self.name)
        p.text(" = ")
        p.pretty(self.expression)
        p.text(";")

class Index:
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs

    def run(self):
        lhs = self.lhs.run()
        rhs = self.rhs.run()
        return lhs.value[rhs.value]

    def substitute(self, pairs, threshold):
        lhs = self.lhs.substitute(pairs, threshold)
        rhs = self.rhs.substitute(pairs, threshold)
        return Index(lhs, rhs)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.pretty(self.lhs)
        p.text("[")
        p.pretty(self.rhs)
        p.text("]")


class Array(Value):
    def __init__(self, value):
        super().__init__(value)
        assert(isinstance(value, list))

    def __add__(self, other):
        if not isinstance(other, Array):
            raise Exception(f"Concatenation not defined between array and '{type(other)}'.")
        return Array(self.value + other.value)

    def run(self):
        return Array([e.run() for e in self.value])

    def substitute(self, pairs, threshold):
        return Array([e.substitute(pairs, threshold) for e in self.value])

    def _repr_pretty_(self, p, cycle):
        with p.group(4, f"[", "]"):
            for idx, item in enumerate(self.value):
                if idx:
                    p.text(", ")
                p.pretty(item)

