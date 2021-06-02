import cairocffi as cairo
from shapely import geometry, affinity

import draw
import units

class Rect:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def __repr__(self):
        return f"Rect({self.x}, {self.y}, {self.w}, {self.h})"

    def pan(self, vector):
        return Rect(self.x + vector[0], self.y + vector[1], self.w, self.h)

    def zoom(self, u):
        return Rect(self.x + u, self.y + u, self.w - u, self.h - u)

    def to_qt(self):
        return QtCore.QRect(self.x, self.y, self.w, self.h)

    @classmethod
    def from_center(cls, center, width, height):
        return cls(center.x - width / 2, center.y - height / 2, width, height)

class Settings:
    def __init__(self, blob):
        self.grid = GridSettings(blob.pop('grid', {}))
        self.units = UnitSettings(blob.pop('units', {}))
        self.display = DisplaySettings(blob.pop('display', {}))

class UnitSettings:
    def __init__(self, blob):
        distance = blob.pop('distance', 'cm')
        if distance == 'm':
            self.distance = units.Meter
        elif distance == 'cm':
            self.distance = units.Centimeter
        elif distance == 'mm':
            self.distance = units.Millimeter
        else:
            raise Exception(f"Not a valid distance: '{distance}'.")

class GridSettings:
    def __init__(self, blob):
        self.size = blob.pop('size', 4)
        self.fine = blob.pop('fine', 1)
        self.position = blob.pop('position', 'top')
        assert(len(blob.keys()) == 0)

class DisplaySettings:
    def __init__(self, blob):
        self.z = blob.pop('z', 1)
        self.ppu = blob.pop('ppu', 8)
        self.center = geometry.Point(0, 0)
        self.background = (1.0, 1.0, 1.0)
        assert(len(blob.keys()) == 0)

    def pan(self, vector):
        self.center = affinity.translate(self.center, vector[0], vector[1])

    def zoom(self, u: int):
        ## TODO: This is probably unnec. complicated
        self.z += u
        if self.z == 0:
            if u < 0:
                self.z = -1
            else:
                self.z = 1
        if self.z < 0:
            scale = -1/self.z * self.ppu
            if math.floor(scale) != scale:
                self.z -= u

    def make_context(self, surface, width, height):
        scale = int(max(1, -1/(self.z-1) * self.ppu) if self.z <= 0 else self.z * self.ppu)
        context = cairo.Context(surface)
        context.translate(width / 2.0, height / 2.0)
        context.scale(scale, scale)
        context.set_source_rgb(*self.background)
        context.paint()
        return context

class Grid:
    def __init__(self, settings):
        self.settings = settings

    def draw(self, context, width, height, x, y, z):
        context.set_source_rgb(0.75, 0.75, 0.75)
        if z < 0:
            if z <= -3:
                context.set_line_width(0.065)
            elif z <= -2:
                context.set_line_width(0.05)
            elif z <= -1:
                context.set_line_width(0.025)
            else:
                context.set_line_width(0.1)
        else:
            context.set_line_width(0.025)

        for i in range(-width - x, width + x, self.settings.size):
            context.move_to(i, -height // 2)
            context.line_to(i, height // 2)
            context.stroke()

        for j in range(-height - y, height + y, self.settings.size):
            context.move_to(-width // 2, j)
            context.line_to(width // 2, j)
            context.stroke()

class Draft:
    def __init__(self, settings, shape):
        self.shape = shape
        self.settings = settings
        self.grid = Grid(settings.grid)
        self.recorder = cairo.RecordingSurface(cairo.CONTENT_COLOR_ALPHA, None)
        context = cairo.Context(self.recorder)
        context.set_source_rgb(0.0, 0.0, 0.0)  # Solid color
        context.set_line_width(1)
        shape.draw(context)

    def window(self, center, target_w, target_h):
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, target_w, target_h)
        context = self.settings.display.make_context(surface, target_w, target_h)

        if self.grid.settings.position == 'bottom':
            with context:
                self.grid.draw(context, target_w, target_h, int(center.x), int(center.y), self.settings.display.z)

        with context:
            draw.surface(context, self.recorder, center, Rect.from_center(center, target_w, target_h))
            context.fill()

        if self.grid.settings.position == 'top':
            with context:
                self.grid.draw(context, target_w, target_h, int(center.x), int(center.y), self.settings.display.z)

        return context

