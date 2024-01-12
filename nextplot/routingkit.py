import dataclasses
import enum
import json
import os
import shutil
import subprocess
import sys

from nextplot import common, types

TRAVEL_SPEED = 10  # assuming 10m/s travel speed for missing segments and snapping


class RoutingKitProfile(enum.Enum):
    """
    Distinguishes the different travel profiles usable with routingkit.
    """

    car = "car"
    bike = "bike"
    pedestrian = "pedestrian"

    def __str__(self):
        return self.value


@dataclasses.dataclass
class Trip:
    start: types.Position
    end: types.Position
    connected: bool
    distance: float
    shape: list[types.Position]

    def __str__(self) -> str:
        return f"Trip({self.start},{self.end})"


def check_prerequisites(rk: str, osm: str, profile: RoutingKitProfile, distance: bool):
    if not os.path.isfile(osm):
        print("routingkit osm file specified, but not found")
        quit()
    if not os.path.isfile(rk) and not shutil.which(rk):
        print("routingkit binary not found")
        quit()
    ch = osm + "_" + profile.value + "_" + ("distance" if distance else "duration") + ".ch"
    if os.path.isfile(ch):
        print("Re-using previously generated CH file")
    else:
        print(f"Generating new CH file at {ch}")


def query_routes(
    rk: str,
    osm: str,
    routes: list[types.Route],
    profile: RoutingKitProfile = RoutingKitProfile.car,
    distance: bool = False,
    travel_speed: float = TRAVEL_SPEED,
):
    """
    Queries road-network paths and distance/travel time for a set of routes.
    The information is added to the routes in their path and path_costs fields.
    """

    # Small sanity check and preparation
    check_prerequisites(rk, osm, profile, distance)

    # Prepare query structure
    query_routes = {}
    query_segments = {}
    queries = []
    for route in routes:
        points = route.points
        for q in [(points[i], points[i + 1]) for i in range(len(points) - 1)]:
            queries.append(q)
            query_routes[len(queries) - 1] = route
            query_segments[len(queries) - 1] = q

    # Query routingkit
    paths, costs = query(rk, osm, queries, profile, distance)

    # Clear any previously existing information
    for route in routes:
        route.legs = None
        route.leg_costs = None

    # Add results to routes
    for i, path in enumerate(paths):
        cost = costs[i]
        route = query_routes[i]
        start, end = query_segments[i]

        # Check how to handle
        no_path = len(path) <= 0
        not_moving = types.Position.equal(start, end)

        # If no path was found, assume straight line
        if no_path or not_moving:
            # Path: start -> end
            leg = [start, end]
            # Costs: simply assume straight line
            cost = common.haversine(start, end)
            if not distance:
                cost /= travel_speed
        else:
            # Path: start -> rk path ... -> end
            leg = [start, *path, end]
            # Costs: account for start/end snapping in costs
            start_cost = common.haversine(start, path[0])
            if not distance:
                start_cost /= travel_speed
            end_cost = common.haversine(path[-1], end)
            if not distance:
                end_cost /= travel_speed
            cost += start_cost + end_cost

        # Add leg to route
        if route.legs is None:
            route.legs = [leg]
            route.leg_costs = [cost]
        else:
            route.legs.append(leg)
            route.leg_costs.append(cost)


def query(
    rk: str,
    osm: str,
    queries: list[tuple[types.Position, types.Position]],
    profile: RoutingKitProfile = RoutingKitProfile.car,
    distance: bool = False,
) -> tuple[list[list[types.Position]], list[float]]:
    """
    Queries paths and road distances for a list of given tuples.

    param str rk: Path to routingkit binary.
    param str osm: Path to the OpenStreetMap data file.
    param str queries: All queries as (start,end) position tuples.
    param bool distance: Indicates whether to query distance instead of duration.
    """

    # Prepare query
    rk_tuples = []
    for f, t in queries:
        rk_tuples.append(
            {
                "from": {"lon": f.lon, "lat": f.lat},
                "to": {"lon": t.lon, "lat": t.lat},
            }
        )
    rk_input = {"tuples": rk_tuples}

    # >> Query routingkit
    rk_process = subprocess.Popen(
        [
            rk,
            "-map",
            osm,
            "-measure",
            "distance" if distance else "traveltime",
            "-profile",
            profile.value,
        ],
        stdout=subprocess.PIPE,
        stdin=subprocess.PIPE,
    )
    rk_output = rk_process.communicate(input=json.dumps(rk_input).encode("utf-8"))
    if rk_process.returncode != 0:
        print()
        print("error in routingkit, stopping")
        sys.exit(1)
    result = json.loads(rk_output[0])

    # Collect results
    trips, distances = [], []
    for trip in result["trips"]:
        trips.append([types.Position(wp["lon"], wp["lat"], None) for wp in trip["waypoints"]])
        distances.append(trip["cost"])
    return trips, distances
