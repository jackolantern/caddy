import os
import sys
import math

import colour
import numpy as np
from shapely import geometry

import draw
import part
import language.syntax as syntax
import language.environment as env

class BuiltinFunction(syntax.FunctionRef):
    def __init__(self, function, ret=None, params=None):
        self.ret = ret
        names = params if params else function.__code__.co_varnames[:function.__code__.co_argcount]
        super().__init__([syntax.Parameter(name, None) for name in names], function)

    def copy(self):
        return BuiltinFunction(self.parameters, self.body)

    def call(self, arguments):
        args = [arg.run() for arg in arguments]
        args = [arg.value if isinstance(arg, syntax.Value) else arg for arg in args]
        return self.ret(self.body(*args)) if self.ret else self.body(*args)

    def shift(self, n):
        return self

def rgb(r, g, b):
    c = colour.Color(colour.rgb2hex((r, g, b)))
    return part.Color(c.red, c.green, c.blue)

def style(shape, name, value):
    shape = shape.copy()
    shape.add_style_property(name, value)
    return shape

def hull(shape):
    return part.Polygon(shape.compute().convex_hull, part.Style())

def bounds(shape):
    return shape.bounds()

def remove(lhs, rhs):
    return lhs.remove(rhs)

def radius(shape):
    return syntax.Number(shape.radius)

def width(shape):
    minx, miny, maxx, maxy = shape.compute().bounds
    return syntax.Number(maxx - minx)

def height(shape):
    minx, miny, maxx, maxy = shape.compute().bounds
    return syntax.Number(maxy - miny)

def polygon(points):
    return part.Polygon(
        geometry.Polygon([(p.value[0], p.value[1]) for p in points]), part.Style())

def concat(lhs, rhs):
    return syntax.Array(lhs + rhs)

def translate(shape, vector):
    return shape.translate(vector.value)

def make_global_env():
    basic_types = {
        "int": syntax.Int,
        "float": syntax.Float,
    }
    env = syntax.Environment(basic_types, make_global_block())
    return env

def map_wrapper(lst, f):
    return syntax.Array(list(map(lambda v: syntax.Call(f, [v]), lst)))

def map_wrapper2(lst, f):
    # TODO: enforce exactly two items in the list.
    return syntax.Array(list(map(lambda v: syntax.Call(f, [v.value[0], v.value[1]]), lst)))

def app(lst, f):
    return syntax.Array(list(map(lambda v: syntax.Call(f, v.value), lst)))

def zip_wrapper(lhs, rhs):
    result = [syntax.Array(list(z)) for z in zip(lhs, rhs)]
    return syntax.Array(result)

def make_range(start, stop, step):
    return syntax.Array([syntax.Number(e) for e in list(np.arange(start, stop, step))])

def tail(lst):
    return syntax.Array(lst[1:])

def math_def(name, ret, *params):
    params = list(params)
    return syntax.NamespaceDefinition(name, BuiltinFunction(getattr(math, name), ret, params))

def make_global_scope():
    scope = env.Scope(None)
    scope.add_symbol("extern", syntax.Namespace([
        syntax.NamespaceDefinition("tail", BuiltinFunction(tail)),
        syntax.NamespaceDefinition("color_rgb", BuiltinFunction(rgb)),
        syntax.NamespaceDefinition("color_name", BuiltinFunction(
            part.Color.from_name, params=["name"])),
        syntax.NamespaceDefinition("make_hatch", BuiltinFunction(draw.make_hatch)),
        syntax.NamespaceDefinition("make_cross_hatch", BuiltinFunction(draw.make_cross_hatch)),
    ]))

    default = syntax.Namespace([
        syntax.NamespaceDefinition("math", syntax.Namespace([
            syntax.NamespaceDefinition("pi", syntax.Float(math.pi)),
            math_def("sin", syntax.Float, "x"),
            math_def("cos", syntax.Float, "x"),
            math_def("tan", syntax.Float, "x"),
            math_def("asin", syntax.Float, "x"),
            math_def("acos", syntax.Float, "x"),
            math_def("atan", syntax.Float, "x")
        ])),
        syntax.NamespaceDefinition("style", BuiltinFunction(style)),
        syntax.NamespaceDefinition("len", BuiltinFunction(len, ret=syntax.Int, params=["lst"])),
        syntax.NamespaceDefinition("range", BuiltinFunction(make_range)),
        syntax.NamespaceDefinition("zip", BuiltinFunction(zip_wrapper)),
        #syntax.NamespaceDefinition("map", BuiltinFunction(map_wrapper)),
        syntax.NamespaceDefinition("apply", BuiltinFunction(app)),
        syntax.NamespaceDefinition("concat", BuiltinFunction(concat)),

        syntax.NamespaceDefinition("hull", BuiltinFunction(hull)),
        syntax.NamespaceDefinition("bounds", BuiltinFunction(bounds)),
        syntax.NamespaceDefinition("width", BuiltinFunction(width)),
        syntax.NamespaceDefinition("height", BuiltinFunction(height)),
        syntax.NamespaceDefinition("radius", BuiltinFunction(radius)),
        syntax.NamespaceDefinition("polygon", BuiltinFunction(polygon)),
        syntax.NamespaceDefinition("remove", BuiltinFunction(remove)),

        syntax.NamespaceDefinition("box", BuiltinFunction(
            lambda width, height: part.Box(geometry.Point(0, 0), width, height, part.Style()))),

        syntax.NamespaceDefinition("circle", BuiltinFunction(lambda radius: part.Circle(radius, geometry.Point(0, 0), part.Style()))),

        syntax.NamespaceDefinition("union", BuiltinFunction(lambda shapes: part.Union(shapes, part.Style()))),

        syntax.NamespaceDefinition("disjoint_union", BuiltinFunction(lambda shapes: part.DisjointUnion(shapes, part.Style()))),

        syntax.NamespaceDefinition("intersection", BuiltinFunction(lambda shapes: part.Intersection(shapes, part.Style()))),

        syntax.NamespaceDefinition("scale", BuiltinFunction(lambda shape, vector: shape.scale(vector))),

        syntax.NamespaceDefinition("rotate", BuiltinFunction(lambda shape, angle: shape.rotate(angle))),

        syntax.NamespaceDefinition("translate", BuiltinFunction(lambda shape, vector: shape.translate(vector))),

        syntax.NamespaceDefinition("V2", BuiltinFunction(lambda x, y: syntax.Value(np.array([x, y])))),

        syntax.NamespaceDefinition("V3", BuiltinFunction(lambda x, y, z: syntax.Value(np.array([x, y, z]))))
    ])

    for d in default.definitions:
        scope.add_symbol(d.name, d.value)

    return scope

