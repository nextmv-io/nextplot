import dataclasses
import enum

import polyline


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


class PositionGroup:
    """
    Defines a group of positions and is used to append additional info to it.
    """

    def __init__(self, positions: list[Position]):
        self.positions = positions

    def __str__(self):
        return ",".join([str(p) for p in self.positions])


class PointGroup:
    """
    Defines one point group and is used to append additional info to it.
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
        self.polyline = None

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
        if self.polyline is not None:
            return self.polyline
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


def decode_polyline(encoded: str) -> list[Position]:
    """Decode a polyline5 encoded string into a list of coordinates."""
    return [Position(lat=lat, lon=lon, desc="") for lat, lon in polyline.decode(encoded, precision=5)]


def decode_polyline6(encoded: str) -> list[Position]:
    """Decode a polyline6 encoded string into a list of coordinates."""
    return [Position(lat=lat, lon=lon, desc="") for lat, lon in polyline.decode(encoded, precision=6)]


def decode_geojson(geojson: dict) -> list[Position]:
    """Decode a geojson object into a list of coordinates."""
    if "geometry" in geojson and "coordinates" in geojson["geometry"]:
        coords = geojson["geometry"]["coordinates"]
        if geojson["geometry"]["type"] == "LineString":
            return [Position(lat=lat, lon=lon, desc="") for lon, lat in coords]
        elif geojson["geometry"]["type"] == "MultiLineString":
            return [Position(lat=lat, lon=lon, desc="") for lon, lat in coords[0]]


class PolylineEncoding(enum.Enum):
    """
    Distinguishes the different polyline encodings.
    """

    polyline = "polyline"
    polyline6 = "polyline6"
    geojson = "geojson"

    def __str__(self):
        return self.value

    def decode(self, encoded):
        if self == PolylineEncoding.polyline:
            return decode_polyline(encoded)
        elif self == PolylineEncoding.polyline6:
            return decode_polyline6(encoded)
        elif self == PolylineEncoding.geojson:
            return decode_geojson(encoded)
        else:
            raise Exception(f"Unsupported polyline encoding: {self}")
