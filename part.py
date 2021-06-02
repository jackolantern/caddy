import math

import colour
import numpy as np
import cairocffi as cairo
from shapely import ops, affinity, geometry

import draw

# TODO: The equality between shapes is a sort of "constructive" or "syntactic" form of equality",
# should there be a means of establishing semantic equality?

class LineCap:
    @classmethod
    def butt(cls):
        return cls(cairo.LINE_CAP_BUTT)

    @classmethod
    def round(cls):
        return cls(cairo.LINE_CAP_ROUND)

    @classmethod
    def square(cls):
        return cls(cairo.LINE_CAP_SQUARE)

    def __eq__(self, other):
        return self.value == other.value

    def __init__(self, value=cairo.LINE_CAP_SQUARE):
        self.value = value

    def activate(self, context):
        context.set_line_cap(self.value)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        if self.value == cairo.LINE_CAP_BUTT:
            p.text("'butt'")
        elif self.value == cairo.LINE_CAP_ROUND:
            p.text("'round'")
        elif self.value == cairo.LINE_CAP_SQUARE:
            p.text("'square'")

class LineDash:
    def __init__(self, value=None):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def activate(self, context):
        if not self.value:
            return
        context.set_dash(self.value)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        if self.value:
            p.pretty(self.value)

class LineWidth:
    def __init__(self, value=1):
        self.value = value

    def __eq__(self, other):
        return self.value == other.value

    def activate(self, context):
        context.set_line_width(self.value)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text(str(self.value))

class Color:
    @classmethod
    def from_name(cls, name):
        color = colour.Color(name)
        return cls(*color.rgb)

    def __init__(self, r, g, b, a=1):
        self.r = r
        self.g = g
        self.b = b
        self.a = a

    def __eq__(self, other):
        return (self.r, self.g, self.b, self.a) == (other.r, other.g, other.b, other.a)

    def run(self):
        return self

    def activate(self, context):
        context.set_source_rgba(self.r, self.g, self.b, self.a)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        p.text(f"Color({self.r}, {self.g}, {self.b})")

class Pattern:
    def __init__(self, pattern, angle=0):
        self.angle = angle
        self.value = pattern

    def __eq__(self, other):
        return self.value == other.value and self.angle == other.angle

    def run(self):
        return self

    def activate(self, context):
        context.rotate(self.angle)
        context.set_source(self.value)

class Stroke:
    def __init__(self, source=Color(0, 0, 0), width=LineWidth(), cap=LineCap(), dash=LineDash()):
        self.source = source
        self.width = width
        self.cap = cap
        self.dash = dash

    def __eq__(self, other):
        return (self.source, self.width, self.cap, self.dash) == (other.source, other.width, other.cap, other.dash)

    def copy(self):
        return Stroke(self.source, self.width, self.cap, self.dash)

    def activate(self, context):
        self.source.activate(context)
        self.width.activate(context)
        self.cap.activate(context)
        self.dash.activate(context)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        props = [self.source, self.width, self.cap, self.dash]
        with p.group(4, 'Stroke(', ' )'):
            p.breakable()
            for idx, item in enumerate(props):
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Style:
    def __init__(self, stroke=None, fill=None):
        self._fill = fill
        self._stroke = stroke or Stroke()

    def __eq__(self, other):
        return (self._stroke == other._stroke and self._fill == other._fill)

    def copy(self):
        return Style(self._stroke.copy() if self._stroke else None, self._fill)

    def with_no_fill(self):
        return Style(self._stroke.copy() if self._stroke else None, None)

    def with_no_stroke(self):
        return Style(None, self._fill)

    def fill(self, context, preserve=False):
        if not self._fill:
            if preserve:
                return
            else:
                context.push_group()
                context.fill()
                context.pop_group()
                return
        with context:
            self._fill.activate(context)
            if preserve:
                context.fill_preserve()
            else:
                context.fill()

    def stroke(self, context, preserve=False):
        if not self._stroke:
            if preserve:
                return
            else:
                context.push_group()
                context.stroke()
                context.pop_group()
                return
        with context:
            self._stroke.activate(context)
            if preserve:
                context.stroke_preserve()
            else:
                context.stroke()

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        props = [self._fill, self._stroke]
        with p.group(4, 'Style(', ' )'):
            p.breakable()
            for idx, item in enumerate(props):
                if idx and idx < len(props):
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Shape:
    def __init__(self, matrix=None):
        self.matrix = np.identity(3) if matrix is None else matrix

    def run(self):
        return self

    def lazy(self, env):
        return self

    def fill(self, matrix, context, preserve=False):
        draw.polygon(context, _transform(self.compute(), self.matrix @ matrix))
        self.style.fill(context, preserve)

    def stroke(self, matrix, context, preserve=False):
        draw.polygon(context, _transform(self.compute(), self.matrix @ matrix))
        self.style.stroke(context, preserve)

    def draw(self, context):
        shape = self.compute()
        draw.polygon(context, shape)
        self.style.fill(context, preserve=True)
        self.style.stroke(context)

    def bounds(self):
        (minx, miny, maxx, maxy) = self.compute().bounds
        w = maxx - minx
        h = maxy - miny
        center = geometry.Point(minx + w / 2.0, miny + h / 2.0)
        return Box(center, w, h, Style())

    def children(self):
        return []

    def add_style_property(self, name, value):
        if name == 'fill':
            value = value.run()
            if not isinstance(value, (Color, Pattern)):
                value = Color.from_name(value)
            self.style._fill = value
        elif name == 'stroke-width':
            self.style._stroke.width = LineWidth(value)

    def scale(self, vector):
        return self.copy(matrix=self.matrix @ _make_scale_matrix(vector))

    def rotate(self, angle):
        return self.copy(matrix=self.matrix @ _make_rotate_matrix(angle))

    def translate(self, vector):
        return self.copy(matrix=self.matrix @ _make_translate_matrix(vector))

    def remove(self, other):
        return Difference(self.copy(), other.copy(), self.style.copy())

class Box(Shape):
    def __init__(self, center, width, height, style, matrix=None):
        super().__init__(matrix)
        self.style = style.copy()
        self.center = center
        self.width = width
        self.height = height

    def __eq__(self, other):
        return ((type(self), self.style, self.center, self.width, self.height) ==
                (type(other), other.style, other.center, other.width, other.height))

    def compute(self):
        x = self.center.x - self.width / 2
        y = self.center.y - self.height / 2
        return geometry.box(x, y, x + self.width, y + self.height)

    def scale(self, vector):
        return Box(self.center, self.width * vector[0], self.height * vector[1], self.style)

    def rotate(self, angle):
        shape = _transform(self.compute(), self.matrix @ _make_rotate_matrix(angle))
        return Polygon(shape, self.style)

    def translate(self, vector):
        x = self.center.x + vector[0]
        y = self.center.y + vector[1]
        return Box(geometry.Point(x, y), self.width, self.height, self.style)

    def copy(self, style=None, matrix=None):
        return Box(self.center, self.width, self.height, style or self.style, self.matrix if matrix is None else matrix)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        props = [self.center, self.width, self.height, self.style]
        with p.group(4, 'Box(', ' )'):
            p.breakable()
            for idx, item in enumerate(props):
                if idx and idx < len(props):
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Circle(Shape):
    def __init__(self, radius, center, style, matrix=None):
        super().__init__(matrix)
        self.style = style.copy()
        self.radius = radius
        self.center = center

    def __eq__(self, other):
        return ((type(self), self.style, self.center, self.radius) ==
                (type(other), other.style, other.center, other.radius))

    def compute(self):
        return _transform(self.center.buffer(self.radius), self.matrix)

    def copy(self, center=None, style=None, matrix=None):
        return Circle(self.radius, self.center if center is None else center, style or self.style, self.matrix if matrix is None else matrix)

    def scale(self, vector):
        if vector[0] == vector[1]:
            return Circle(vector[0] * self.radius, self.center, self.style, self.matrix)
        return Polygon(self.compute(), self.style, self.matrix @ _make_scale_matrix(vector))

    def translate(self, vector):
        x = self.center.x + vector[0]
        y = self.center.y + vector[1]
        return self.copy(center=geometry.Point(x, y))

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        props = [self.radius, self.style]
        with p.group(4, 'Circle(', ' )'):
            p.breakable()
            for idx, item in enumerate(props):
                if idx and idx < len(props):
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Polygon(Shape):
    def __init__(self, geo, style, matrix=None):
        super().__init__(matrix)
        self.style = style.copy()
        self.geo = geo

    def __eq__(self, other):
        return ((type(self), self.style, self.geo, self.matrix) ==
                (type(other), other.style, other.geo, other.matrix))

    def compute(self):
        return _transform(self.geo, self.matrix)

    def copy(self, style=None, matrix=None):
        return Polygon(self.geo, style or self.style, self.matrix if matrix is None else matrix)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        props = [self.geo, self.style]
        with p.group(4, 'Polygon(', ' )'):
            p.breakable()
            for idx, item in enumerate(props):
                if idx and idx < len(props):
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Difference(Shape):
    def __init__(self, lhs, rhs, style, matrix=None):
        super().__init__(matrix)
        self.style = style.copy()
        self.lhs = lhs
        self.rhs = rhs

    def __eq__(self, other):
        return ((type(self), self.style, self.lhs, other.rhs, self.matrix) ==
                (type(other), other.style, other.lhs, other.rhs, other.matrix))

    def copy(self, style=None, matrix=None):
        return Difference(self.lhs.copy(), self.rhs.copy(), style or self.style, self.matrix if matrix is None else matrix)

    def fill(self, matrix, context):
        shape = self.compute()
        with context:
            draw.polygon(context, shape)
            self.style.fill(context)
            draw.clip(context, shape)
            self.lhs.fill(self.matrix @ matrix, context)

    def draw(self, context):
        shape = self.compute()
        with context:
            draw.polygon(context, shape)
            self.style.fill(context)
            draw.clip(context, shape)
            self.lhs.fill(self.matrix, context)
        draw.polygon(context, shape)
        self.style.stroke(context)

    def compute(self):
        return _transform(self.lhs.compute() - self.rhs.compute(), self.matrix)

    def children(self):
        return [self.lhs, self.rhs]

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        props = [self.lhs, self.rhs, self.style]
        with p.group(4, 'Difference(', ' )'):
            p.breakable()
            for idx, item in enumerate(props):
                if idx and idx < len(props):
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Union(Shape):
    def __init__(self, children, style, matrix=None):
        super().__init__(matrix)
        self.style = style.copy()
        self.children = children

    def __eq__(self, other):
        return ((type(self), self.style, self.children, self.matrix) ==
                (type(other), other.style, other.children, other.matrix))

    def fill(self, matrix, context, preserve=False):
        shape = _transform(self.compute(), self.matrix @ matrix)
        with context:
            draw.polygon(context, shape)
            self.style.fill(context)
            for child in self.children:
                child.fill(self.matrix @ matrix, context)

    def draw(self, context):
        shape = self.compute()
        with context:
            draw.polygon(context, shape)
            self.style.fill(context)
            for child in self.children:
                child.fill(self.matrix, context)
            draw.polygon(context, shape)
            self.style.stroke(context)

    def compute(self):
        return _transform(ops.unary_union([child.compute() for child in self.children]), self.matrix)

    def copy(self, style=None, matrix=None):
        return Union([c.copy() for c in self.children], style or self.style, self.matrix if matrix is None else matrix)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        with p.group(4, 'Union([', '])'):
            for idx, item in enumerate(self.children):
                p.breakable()
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class DisjointUnion(Union):
    def __init__(self, children, style, matrix=None):
        super().__init__(children, style, matrix)

    def draw(self, context):
        shape = self.compute()
        with context:
            draw.polygon(context, shape)
            self.style.fill(context)
            for obj in self.children:
                copy = obj.copy()
                copy.draw(context)
            draw.polygon(context, shape)
            self.style.stroke(context)

    def copy(self, style=None, matrix=None):
        return DisjointUnion(list(self.children), style or self.style.copy(), self.matrix if matrix is None else matrix)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        with p.group(4, 'DisjointUnion([', '])'):
            for idx, item in enumerate(self.children):
                p.breakable()
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(item)

class Intersection(Shape):
    def __init__(self, children, style, matrix=None):
        super().__init__(matrix)
        self.style = style.copy()
        self.children = children

    def __eq__(self, other):
        return ((type(self), self.style, self.children, self.matrix) ==
                (type(other), other.style, other.children, other.matrix))

    def fill(self, context):
        shape = self.compute()
        with context:
            draw.polygon(context, shape)
            self.style.fill(context)

    def draw(self, context):
        shape = self.compute()
        with context:
            draw.polygon(context, shape)
            self.style.fill(context, preserve=True)
            self.style.stroke(context)

    def compute(self):
        shape = _transform(self.children[0].compute(), self.matrix)
        for nxt in self.children[1:]:
            shape = shape & _transform(nxt.compute(), self.matrix)
        return shape

    def copy(self, style=None, matrix=None):
        return Intersection(list(self.children), self.style if style is None else style, self.matrix if matrix is None else matrix)

    def _repr_pretty_(self, p, cycle):
        assert(not cycle)
        with p.group(4, 'Intersection([', '])'):
            for idx, item in enumerate(self.children):
                p.breakable()
                if idx:
                    p.text(',')
                    p.breakable()
                p.pretty(item)

def _make_scale_matrix(vector):
    return np.array([
        [vector[0], 0, 0],
        [0, vector[1], 0],
        [0, 0, 1]
    ])

def _make_rotate_matrix(angle):
    return np.array([
        [math.cos(angle), -math.sin(angle), 0],
        [math.sin(angle), math.cos(angle), 0],
        [0, 0, 1]
    ])

def _make_translate_matrix(vector):
    return np.array([[1, 0, vector[0]], [0, 1, vector[1]], [0, 0, 1]])

def _transform(shape, matrix):
    array = [matrix[0][0], matrix[0][1], matrix[1][0], matrix[1][1], matrix[0][2], matrix[1][2]]
    return affinity.affine_transform(shape, array)

