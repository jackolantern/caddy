import math
import itertools as it
import cairocffi as cairo
from shapely import geometry

import part

def make_hatch(angle, thickness, fg, bg):
    style = part.Style(fill=bg, stroke=part.Stroke(source=fg, width=part.LineWidth(thickness)))
    surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, (0, 0, 1, 1))
    context = cairo.Context(surface)
    with context:
        style._fill.activate(context)
        context.paint()
        style._stroke.activate(context)
        context.move_to(0.5, 0)
        context.line_to(0.5, 1)
        style.stroke(context)
    pattern = cairo.SurfacePattern(surface)
    pattern.set_extend(cairo.EXTEND_REPEAT)
    return part.Pattern(pattern, angle=angle)

def make_cross_hatch(angle, thickness, fg, bg):
    style = part.Style(fill=bg, stroke=part.Stroke(source=fg, width=part.LineWidth(thickness)))
    surface = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, (0, 0, 1, 1))
    context = cairo.Context(surface)
    with context:
        style._fill.activate(context)
        context.paint()
        style._stroke.activate(context)
        context.move_to(0.5, 0)
        context.line_to(0.5, 1)
        context.move_to(0, 0.5)
        context.line_to(1, 0.5)
        style.stroke(context)
    pattern = cairo.SurfacePattern(surface)
    pattern.set_extend(cairo.EXTEND_REPEAT)
    return part.Pattern(pattern, angle=angle)

def clip(context, polygon):
    for ext in _iter_ext(polygon):
        _polygon_from_coords(context, ext.coords)
    for ring in _iter_int(polygon):
        _polygon_from_coords(context, ring.coords)
    context.clip()

def polygon(context, polygon):
    for ext in _iter_ext(polygon):
        _polygon_from_coords(context, ext.coords)
    for ring in _iter_int(polygon):
        _polygon_from_coords(context, ring.coords)
    #hatch = make_hatch(part.Style(line_width=part.LineWidth(0.1)))
    #context.rotate(math.pi / 4)
    #context.set_source(hatch)

def _iter_ext(shape):
    if isinstance(shape, geometry.MultiPolygon):
        for geom in shape.geoms:
            yield geom.exterior
    else:
        yield shape.exterior

def _iter_int(shape):
    if isinstance(shape, geometry.MultiPolygon):
        for geom in shape.geoms:
            for ring in geom.interiors:
                yield ring
    else:
        for ring in shape.interiors:
            yield ring

def _polygon_from_coords(context, coords):
    coords = list(coords)
    cur = coords.pop()
    context.move_to(*cur)
    while coords:
        cur = coords.pop()
        context.line_to(*cur)
    context.close_path()

def surface(context, surface, source, destination):
    """
    context: cairo.Context
    surface: cairo.Surface
    source: shapely.Point
    destination: Rect
    """
    context.set_source_surface(surface, -source.x, -source.y)
    context.rectangle(destination.x, destination.y, destination.w, destination.h)

