"""
# Integration tests

These test both the `part` module and the `language`, `syntax`, `grammar`, and `lex` modules.
"""

import math

import nose.tools as test
from shapely import geometry

import part
import language
from language import syntax
from pretty import pprint

def test_int():
    result = language.run_string('1')
    test.eq_(result.value, 1)

def test_float():
    result = language.run_string('0.1')
    test.eq_(result.value, 0.1)
    result = language.run_string('.1')
    test.eq_(result.value, 0.1)
    result = language.run_string('1.')
    test.eq_(type(result.value), float)
    test.eq_(result.value, 1)

def test_string():
    result = language.run_string('"foo"')
    test.eq_(result.value, "foo")

def test_let():
    result = language.run_string('let x = 1; x')
    test.eq_(result.value, 1)

def test_nested_call():
    result = language.run_string("""
let g = function(j) { (0).j() };
let f = function(h) {
    g(h)
};
f(function(x) { x + 1 })
""")
    test.eq_(result.value, 1)

def test_import():
    result = language.run_string('import "examples/prelude.caddy"; math::pi')
    test.eq_(result.value, math.pi)

def test_box():
    result = language.run_string("box(1, 2)")
    test.ok_(isinstance(result, part.Box), f"Expected the result to be a box, not a {type(result)}.")
    test.eq_(result.width, 1, f"Expected a width of 1, not {result.width}.")
    test.eq_(result.height, 2, f"Expected a height of 2, not {result.height}.")
    test.eq_(result.center, geometry.Point(0, 0), f"Expected a center of (0, 0), not {result.center}.")

def test_box_scale():
    result = language.run_string("box(10, 16).scale(V2(.5, .25))")
    test.ok_(isinstance(result, part.Box), f"Expected the result to be a box, not a {type(result)}.")
    test.eq_(result.width, 5.0, f"Expected a width of 5.0, not {result.width}.")
    test.eq_(result.height, 4.0, f"Expected a height of 4.0, not {result.height}.")
    test.eq_(result.center, geometry.Point(0, 0), f"Expected a center of (0, 0), not {result.center}.")

def test_box_rotate():
    # TODO: need a way of testing this better; since this is just a parallelepiped we can probably just assert equality
    # using the wkt format.
    result = language.run_string("box(10, 16).rotate(math::pi / 3)")
    test.ok_(isinstance(result, part.Polygon), f"Expected the result to be a polygon, not a {type(result)}.")

def test_box_translate():
    result = language.run_string("box(2, 3).translate(V2(-2, 1))")
    test.ok_(isinstance(result, part.Box), f"Expected the result to be a box, not a {type(result)}.")
    test.eq_(result.width, 2, f"Expected a width of 2, not {result.width}.")
    test.eq_(result.height, 3, f"Expected a height of 3, not {result.height}.")
    test.eq_(result.center, geometry.Point(-2, 1), f"Expected a center of (-2, 1), not {result.center}.")

def test_circle():
    result = language.run_string("circle(1)")
    test.ok_(isinstance(result, part.Circle), f"Expected the result to be a circle, not a {type(result)}.")
    test.eq_(result.radius, 1, f"Expected a radius of 1, not {result.radius}.")
    test.eq_(result.center, geometry.Point(0, 0), f"Expected a center of (0, 0), not {result.center}.")

def test_circle_scale_eq():
    result = language.run_string("circle(4).scale(V2(2, 2))")
    test.ok_(isinstance(result, part.Circle), f"Expected the result to be a circle, not a {type(result)}.")
    test.eq_(result.radius, 8, f"Expected a radius of 8, not {result.radius}.")
    test.eq_(result.center, geometry.Point(0, 0), f"Expected a center of (0, 0), not {result.center}.")

def test_circle_scale_neq():
    # TODO: need a way of testing this better.
    result = language.run_string("circle(4).scale(V2(1, 2))")
    test.ok_(isinstance(result, part.Polygon), f"Expected the result to be a polygon, not a {type(result)}.")

def test_circle_translate():
    result = language.run_string("circle(2).translate(V2(-1, 2))")
    test.ok_(isinstance(result, part.Circle), f"Expected the result to be a circle, not a {type(result)}.")
    test.eq_(result.radius, 2, f"Expected a radius of 2, not {result.radius}.")
    test.eq_(result.center, geometry.Point(-1, 2), f"Expected a center of (-1, 2), not {result.center}.")

def test_functions_are_values():
    result = language.run_string('let f = function(x, g) { x + g(x) }; f(1, function(y) { y + 1 })')
    test.eq_(result.value, 3)

def test_nested_names():
    result = language.run_string('''
let f = function(f, g) {
    function(x, y, z) {
        if z == 0 then f(x) else g(y)
    }
};
let g = function(q) { 0 };
let h = function(p) { 1 };
[f(g, h)(1, 2, 3)]
''')
    test.eq_(result, syntax.Array([syntax.Number(1)]))

def test_this():
    result = language.run_string('''
let f = function(x) { if x == 5 then x else this(x + 1) };
f(0)
''')
    test.eq_(result.value, 5)

def test_map():
    header = 'import "examples/prelude.caddy"; let plus1 = function(x) { x + 1 }; '
    result = language.run_string(header + '[].map(plus1)')
    test.eq_(result.value, [])
    result = language.run_string(header + 'map([1], plus1)')
    test.eq_(result, syntax.Array([syntax.Number(2)]))
    result = language.run_string(header + '[3, 6].map(plus1)')
    test.eq_([e.value for e in result.value], [4, 7])
    result = language.run_string(header + '[1, 2, 3, 4, 5].map(plus1)')
    test.eq_([e.value for e in result.value], [2, 3, 4, 5, 6])

def test_foldr():
    header = 'import "examples/prelude.caddy"; let add = function(x, y) { x + y }; '
    result = language.run_string(header + 'add.foldr(7, [])')
    test.eq_(result.value, 7)
    result = language.run_string(header + 'add.foldr(7, [1])')
    test.eq_(result.value, 8)
    result = language.run_string(header + 'add.foldr(0, [1, 2, 3, 4, 5])')
    test.eq_(result.value, 15)

def test_style_fill():
    result = language.run_string('import "examples/prelude.caddy"; circle(1).style("fill", color::from_name("yellow"))')
    test.eq_(result.style._fill, part.Color.from_name("yellow"))

def test_style_width():
    result = language.run_string('import "examples/prelude.caddy"; circle(1).style("stroke-width", 100)')
    test.eq_(result.style._stroke.width.value, 100)

