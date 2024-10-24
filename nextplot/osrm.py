import dataclasses
import sys
import urllib.parse

import polyline
import requests

from nextplot import common, types

TRAVEL_SPEED = 10  # assuming 10m/s travel speed for missing segments and snapping


@dataclasses.dataclass
class OsrmRouteRequest:
    positions: list[types.Position]


@dataclasses.dataclass
class OsrmRouteResponse:
    paths: list[list[types.Position]]
    distances: list[float]
    durations: list[float]
    zero_distance: bool = False
    no_route: bool = False


def query_route(
    endpoint: str,
    route: OsrmRouteRequest,
) -> OsrmRouteResponse:
    """
    Queries a route from the OSRM server.
    """
    # Encode positions as polyline string to better handle large amounts of positions
    polyline_str = polyline.encode([(p.lat, p.lon) for p in route.positions])

    # Assemble request
    url_base = urllib.parse.urljoin(endpoint, "route/v1/driving/")
    url = urllib.parse.urljoin(url_base, f"polyline({polyline_str})?overview=full&geometries=polyline&steps=true")

    # Query OSRM
    try:
        response = requests.get(url)
        # If no route was found, use as-the-crow-flies fallback
        if response.status_code == 400 and response.json()["code"] == "NoRoute":
            print(
                f"Warning: OSRM was unable to find a route for {[(p.lat, p.lon) for p in route.positions]}"
                + "(lat,lon ordering), using as-the-crow-flies fallback"
            )
            paths, distances, durations = [], [], []
            for f, t in zip(route.positions, route.positions[1:], strict=False):
                paths.append(
                    [types.Position(lon=f.lon, lat=f.lat, desc=None), types.Position(lon=t.lon, lat=t.lat, desc=None)]
                )
                distances.append(common.haversine(f, t))
                durations.append(common.haversine(f, t) / TRAVEL_SPEED)
            return OsrmRouteResponse(paths=paths, distances=distances, durations=durations, no_route=True)
        # Make sure we are not getting an error
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error querying OSRM at {url_base}:", e)
        if response:
            print(response.text)
        sys.exit(1)
    result = response.json()
    if result["code"] != "Ok":
        raise Exception("OSRM returned an error:", result["message"])
    if len(result["routes"]) == 0:
        raise Exception(f"No route found for {route.positions}")

    # Process all legs
    all_zero_distances = True
    legs, distances, durations = [], [], []
    for idx, leg in enumerate(result["routes"][0]["legs"]):
        # Combine all steps into a single path
        path = []
        for step in leg["steps"]:
            path.extend(polyline.decode(step["geometry"]))
        # Remove subsequent identical points
        path = [path[0]] + [p for i, p in enumerate(path[1:], 1) if path[i] != path[i - 1]]
        # Convert to Position objects
        path = [types.Position(lon=lon, lat=lat, desc=None) for lat, lon in path]
        # Add start and end
        path = [route.positions[idx]] + path + [route.positions[idx + 1]]
        # Extract distance and duration
        distance = leg["distance"] / 1000.0  # OSRM return is in meters, convert to km
        duration = leg["duration"]
        # Make sure we are finding any routes
        if distance > 0:
            all_zero_distances = False
        # Add duration for start and end
        start_distance = common.haversine(path[0], route.positions[idx])
        end_distance = common.haversine(path[-1], route.positions[idx + 1])
        distance += start_distance + end_distance
        duration += start_distance / TRAVEL_SPEED + end_distance / TRAVEL_SPEED
        # Append to list
        legs.append(path)
        distances.append(distance)
        durations.append(duration)

    # Warn if number of legs does not match number of positions
    if len(legs) != len(route.positions) - 1:
        print(f"Warning: number of legs ({len(legs)}) does not match number of positions ({len(route.positions)} - 1)")

    # Extract route
    return OsrmRouteResponse(paths=legs, distances=distances, durations=durations, zero_distance=all_zero_distances)


def query_routes(
    endpoint: str,
    routes: list[types.Route],
) -> list[OsrmRouteResponse]:
    """
    Queries multiple routes from the OSRM server.

    param str endpoint: URL of the OSRM server.
    param list[OsrmRouteRequest] routes: List of routes to query.

    return: List of route results.
    """

    # Query all routes
    reqs = [OsrmRouteRequest(positions=route.points) for route in routes]
    zero_distance_routes, no_route_routes = 0, 0
    for r, req in enumerate(reqs):
        result = query_route(endpoint, req)
        routes[r].legs = result.paths
        routes[r].leg_distances = result.distances
        routes[r].leg_durations = result.durations
        if result.zero_distance:
            zero_distance_routes += 1
        if result.no_route:
            no_route_routes += 1
    if zero_distance_routes > 0:
        print(f"Warning: {zero_distance_routes} / {len(routes)} routes have zero distance according to OSRM")
    if no_route_routes > 0:
        print(f"Warning: {no_route_routes} / {len(routes)} routes could not be found by OSRM")
