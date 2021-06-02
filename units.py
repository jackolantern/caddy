class Unit:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f"{self.value} {self.symbol}"

class Meter(Unit):
    name = "meter"
    symbol = "m"

class Centimeter(Unit):
    name = "centimeter"
    symbol = "cm"

class Millimeter(Unit):
    name = "millimeter"
    symbol = "mm"

