import dataclasses
import enum


class ColorProfile(enum.Enum):
    auto = "auto"
    cloud = "cloud"
    rainbow = "rainbow"

    def __str__(self):
        return self.value


class Stat:
    """
    Defines a summary stat describing the solution.
    """

    def __init__(self, name, desc, stat):
        self.desc = desc
        self.name = name
        self.val = stat


@dataclasses.dataclass
class BoundingBox:
    """
    Represents a bounding box.
    """

    min_x: float
    max_x: float
    min_y: float
    max_y: float

    def __post_init__(self):
        self.width = self.max_x - self.min_x
        self.height = self.max_y - self.min_y

    def __str__(self):
        return f"BoundingBox(min_x={self.min_x}, max_x={self.max_x}, " + f"min_y={self.min_y}, max_y={self.max_y})"


@dataclasses.dataclass
class Position:
    lon: float
    lat: float
    desc: str
    distance: float = 0

    def __getitem__(self, key):
        if key == 0:
            return self.lon
        elif key == 1:
            return self.lat
        else:
            raise Exception(f'Unrecognized key "{key}", use 0 for lon and 1 for lat')

    def __str__(self) -> str:
        return f"Pos({self.lon},{self.lat})"

    @staticmethod
    def equal(p1, p2) -> bool:
        """
        Compares the two points for equality.
        """
        return p1.lon == p2.lon and p1.lat == p2.lat

    def clone(self):
        """
        Creates a clone of this position.
        """
        return Position(self.lon, self.lat, self.desc, self.distance)


class Point:
    """
    Defines one point and is used to append additional info to it.
    """

    def __init__(self, points):
        self.points = points

    def __str__(self):
        return ",".join(self.point[0]) if len(self.point) > 0 else "empty"


class Cluster:
    """
    Defines one cluster and is used to append additional info to it.
    """

    def __init__(self, cluster):
        self.points = cluster

    def __str__(self):
        return f"len: {len(self.points)}"


class Route:
    """
    Defines one route and is used to append additional info for it.
    """

    def __init__(self, points: list[Position]):
        self.points = points
        self.legs = None
        self.leg_costs = 0

    def to_points(self, omit_start: bool, omit_end: bool) -> list[Position]:
        """
        Returns all points of the route.
        """
        ps = []
        start = 1 if omit_start else 0
        stop = len(self.points) - 1 if omit_end else len(self.points)
        for i in range(start, stop):
            ps.append(self.points[i])
        return ps

    def to_polyline(self, omit_start: bool, omit_end: bool) -> list[Position]:
        """
        Returns the full polyline that can be used for plotting.
        """
        line = []
        start = 1 if omit_start else 0
        stop = len(self.points) - 1 if omit_end else len(self.points)
        if self.legs is not None:
            for i in range(start, stop - 1):
                line.extend(self.legs[i])
        else:
            for i in range(start, stop):
                line.append(self.points[i])
        return line

    def __str__(self):
        return f"len: {len(self.points)}"


class RouteDirectionIndicator(enum.Enum):
    """
    Distinguishes the different route direction indicators.
    """

    none = "none"
    arrow = "arrow"
    animation = "animation"

    def __str__(self):
        return self.value
