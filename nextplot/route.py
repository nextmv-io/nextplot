import json

import folium
import plotly.graph_objects as go
from folium import plugins

from . import common, routingkit, types

# ==================== This file contains route plotting code (mode: 'route')


COLOR_UNASSIGNED = common.get_color(0, 0, 0.5)

# ==================== Pre-configured plot profiles


class RoutePlotProfile:
    """
    Pre-configured plot profiles for routes.
    """

    def __init__(
        self,
        jpath_route: str = "",
        jpath_pos: str = "",
        jpath_x: str = "",
        jpath_y: str = "",
        jpath_unassigned: str = "",
        jpath_unassigned_x: str = "",
        jpath_unassigned_y: str = "",
    ):
        self.jpath_route = jpath_route
        self.jpath_pos = jpath_pos
        self.jpath_x = jpath_x
        self.jpath_y = jpath_y
        self.jpath_unassigned = jpath_unassigned
        self.jpath_unassigned_x = jpath_unassigned_x
        self.jpath_unassigned_y = jpath_unassigned_y

    def __str__(self):
        return (
            "RoutePlotProfile("
            + f"jpath_route={self.jpath_route}, "
            + f"jpath_pos={self.jpath_pos}, "
            + f"jpath_x={self.jpath_x}, "
            + f"jpath_y={self.jpath_y}, "
            + f"jpath_unassigned={self.jpath_unassigned}, "
            + f"jpath_unassigned_x={self.jpath_unassigned_x}, "
            + f"jpath_unassigned_y={self.jpath_unassigned_y})"
        )


# ==================== Route mode argument definition


def arguments(parser):
    """
    Defines arguments specific to route plotting.
    """
    parser.add_argument(
        "--input_route",
        type=str,
        nargs="?",
        default="",
        help="path to the route file to plot",
    )
    parser.add_argument(
        "--jpath_route",
        type=str,
        nargs="?",
        default="state.vehicles[*].route",
        help="JSON path to the route steps (XPATH like,"
        + " see https://goessner.net/articles/JsonPath/,"
        + ' example: "state.drivers[*].path")',
    )
    parser.add_argument(
        "--jpath_unassigned",
        type=str,
        nargs="?",
        default="state.unassigned",
        help="JSON path to the unassigned points. Will plot them separately, if given. "
        + "(e.g. 'state.unassigned'; to skip unassigned points, use empty string: '')",
    )
    parser.add_argument(
        "--jpath_unassigned_x",
        type=str,
        nargs="?",
        default="",
        help="JSON path to to the x-coordinate of the unassigned point. If not given, " + "--jpath_x will be used.",
    )
    parser.add_argument(
        "--jpath_unassigned_y",
        type=str,
        nargs="?",
        default="",
        help="JSON path to to the y-coordinate of the unassigned point. If not given, " + "--jpath_y will be used.",
    )
    parser.add_argument(
        "--input_pos",
        type=str,
        nargs="?",
        default="",
        help="path to file containing the positions, if not supplied by route file",
    )
    parser.add_argument(
        "--jpath_pos",
        type=str,
        nargs="?",
        default="",
        help="JSON path to the positions, if routes are stored as indices",
    )
    parser.add_argument(
        "--omit_start",
        dest="omit_start",
        action="store_true",
        default=False,
        help="indicates whether to omit the first route location",
    )
    parser.add_argument(
        "--omit_end",
        dest="omit_end",
        action="store_true",
        default=False,
        help="indicates whether to omit the first route location",
    )
    parser.add_argument(
        "--omit_short",
        type=int,
        nargs="?",
        default=0,
        help="omit routes with less stops than the given value",
    )
    parser.add_argument(
        "--nextroute",
        dest="nextroute",
        action="store_true",
        default=False,
        help="overrides jpaths for nextroute outputs",
    )
    parser.add_argument(
        "--route_direction",
        type=types.RouteDirectionIndicator,
        choices=list(types.RouteDirectionIndicator),
        default=types.RouteDirectionIndicator.none.value,
        help="specifies how to indicate route direction",
    )
    parser.add_argument(
        "--route_animation_color",
        type=str,
        nargs="?",
        default="FFFFFF",
        help="background color of the route when using direction animation (e.g.: 000000)",
    )
    parser.add_argument(
        "--weight_route",
        type=float,
        nargs="?",
        default=1,
        help="factor for in-/decreasing thickness of the route (e.g.: 1.5 == 50 percent more weight)",
    )
    parser.add_argument(
        "--no_points",
        action="store_true",
        help="indicates whether to omit plotting the points in addition to the route",
    )
    parser.add_argument(
        "--weight_points",
        type=float,
        nargs="?",
        default=1,
        help="point size (<1 decreases, >1 increases)",
    )
    parser.add_argument(
        "--start_end_markers",
        action="store_true",
        help="indicates whether to add start and end markers",
    )
    parser.add_argument(
        "--rk_bin",
        type=str,
        nargs="?",
        default="routingkit",
        help="path to standalone routingkit binary (uses installed 'routingkit' at default).",
    )
    parser.add_argument(
        "--rk_osm",
        type=str,
        nargs="?",
        default=None,
        help=(
            "path to the OpenStreetMap data file."
            + " ch-file will be created next to it (or re-used)."
            + " enables road plotting, if provided"
        ),
    )
    parser.add_argument(
        "--rk_profile",
        type=routingkit.RoutingKitProfile,
        choices=list(routingkit.RoutingKitProfile),
        default=routingkit.RoutingKitProfile.car.value,
        help="specifies the travel profile to be used by routingkit",
    )
    parser.add_argument(
        "--rk_distance",
        action="store_true",
        help="provide routingkit distance information instead of time",
    )


# ==================== Route plotting specific functionality


def parse(
    input_route: str,
    jpath_route: str,
    jpath_unassigned: str,
    jpath_unassigned_x: str,
    jpath_unassigned_y: str,
    input_pos: str,
    jpath_pos: str,
    jpath_x: str,
    jpath_y: str,
) -> tuple[list[list[types.Position]], list[list[types.Position]]]:
    """
    Parses the route data from the file(s).
    """
    # Load json data
    content_route, content_pos = common.load_data(input_route, input_pos)

    # Extract routes
    points = common.extract_position_groups(
        content_route,
        jpath_route,
        content_pos,
        jpath_pos,
        jpath_x,
        jpath_y,
    )

    # Extract unassigned (if given)
    unassigned = []
    if jpath_unassigned:
        unassigned = common.extract_position_groups(
            content_route,
            jpath_unassigned,
            content_pos,
            jpath_pos,
            jpath_unassigned_x if jpath_unassigned_x else jpath_x,
            jpath_unassigned_y if jpath_unassigned_y else jpath_y,
        )

    return points, unassigned


def create_plot(
    routes: list[types.Route],
    unassigned: list[types.Position],
    label_x: str,
    label_y: str,
    plotly_theme: str,
    omit_start: bool,
    omit_end: bool,
    no_points: bool,
    weight_points: float,
    weight_route: float,
) -> go.Figure:
    """
    Plots the given routes on a plotly figure.
    """
    # Init plot
    fig = go.Figure(
        layout=go.Layout(
            xaxis_title=label_x,
            yaxis_title=label_y,
            template=plotly_theme,
            margin={"l": 20, "r": 20, "b": 20, "t": 20, "pad": 4},
            font={"size": 18},
            showlegend=False,
        )
    )

    # Plot the routes
    for i, route in enumerate(routes):
        if len(route.points) <= 0:
            continue
        route_line = route.to_polyline(omit_start, omit_end)
        xs, ys = [p.lon for p in route_line], [p.lat for p in route_line]
        fig.add_trace(
            go.Scatter(
                x=xs,
                y=ys,
                mode="lines",
                line={"color": route.color.hex, "width": weight_route * 3},
                name=f"Route {i+1}",
            )
        )
        if not no_points:
            route_points = route.to_points(omit_start, omit_end)
            fig.add_trace(
                go.Scatter(
                    x=[p.lon for p in route_points],
                    y=[p.lat for p in route_points],
                    mode="markers",
                    marker={"color": route.color.hex, "size": 5 * weight_points},
                    name=f"Route {i+1}",
                )
            )

    # Plot the unassigned points
    unassigned_points = [p for g in unassigned for p in g]
    fig.add_trace(
        go.Scatter(
            x=[p.lon for p in unassigned_points],
            y=[p.lat for p in unassigned_points],
            mode="markers",
            marker={"color": COLOR_UNASSIGNED, "size": 5 * weight_points},
            name="Unassigned",
        )
    )

    # Return figure
    return fig


def create_map(
    routes: list[types.Route],
    unassigned: list[types.Position],
    no_points: bool,
    weight_points: float,
    weight_route: float,
    omit_start: bool,
    omit_end: bool,
    route_direction: types.RouteDirectionIndicator,
    route_animation_color: str,
    start_end_markers: bool,
    custom_map_tile: list[str],
    rk_distance: bool,
) -> folium.Map:
    """
    Plots the given routes on a folium map.
    """
    # Determine bbox
    bbox = common.bounding_box([r.points for r in routes] + unassigned)

    # Make map plot of routes
    m, base_tree = common.create_map(
        (bbox.max_x + bbox.min_x) / 2.0,
        (bbox.max_y + bbox.min_y) / 2.0,
        custom_map_tile,
    )
    route_groups = {}
    route_layer_names = {}
    unassigned_group = folium.FeatureGroup("Unassigned")

    # Plot the routes themselves
    for i, route in enumerate(routes):
        if len(route.points) <= 0:
            continue
        layer_name = f"Route {i+1}"
        route_groups[route] = folium.FeatureGroup(layer_name)
        route_layer_names[route_groups[route]] = layer_name
        plot_map_route(
            route_groups[route],
            route,
            i,
            len(routes),
            weight_route,
            omit_start,
            omit_end,
            route_direction,
            route_animation_color,
            1.0 / 1000.0 if rk_distance else 1.0 / 1000.0,
            "km" if rk_distance else "s",
        )

    # Plot points
    if not no_points:
        for route in routes:
            for p, point in enumerate(route.to_points(omit_start, omit_end)):
                d = point.desc.replace("\n", "<br/>").replace(r"`", r"\`")
                text = (
                    "<p>"
                    + f"Stop: {p+1} / {len(route.points)}</br>"
                    + f"Distance: {point.distance:.2f} km "
                    + f"({common.km_to_miles(point.distance):.2f} miles)</br>"
                    + f"Location (lon/lat): {point[0]}, {point[1]}"
                    + "".join(["&nbsp;" for _ in range(0, 80)])
                    + "</p>"
                    + f"JSON:</br><pre><code>{d}</code></pre></br>"
                )
                plot_map_point(
                    route_groups[route],
                    point,
                    text,
                    weight_points,
                    route.color.hex,
                )
    if start_end_markers:
        for i, route in enumerate(routes):
            points = route.to_points(omit_start, omit_end)
            if len(points) > 0:
                start = points[0]
                d = start.desc.replace("\n", "<br/>").replace(r"`", r"\`")
                text = (
                    "<p>"
                    + f"First stop in route {i+1}</br>"
                    + f"Location (lon/lat): {start[0]}, {start[1]}"
                    + "".join(["&nbsp;" for _ in range(0, 80)])
                    + "</p>"
                    + f"JSON:</br><pre><code>{d}</code></pre></br>"
                )
                plot_map_marker(
                    route_groups[route],
                    start,
                    text,
                    "glyphicon glyphicon-chevron-up",
                    "lightgray",
                )
            if len(points) > 1:
                end = points[-1]
                d = end.desc.replace("\n", "<br/>").replace(r"`", r"\`")
                text = (
                    "<p>"
                    + f"Last stop in route {i+1}</br>"
                    + f"Location (lon/lat): {end[0]}, {end[1]}"
                    + "".join(["&nbsp;" for _ in range(0, 80)])
                    + "</p>"
                    + f"JSON:</br><pre><code>{d}</code></pre></br>"
                )
                plot_map_marker(
                    route_groups[route],
                    end,
                    text,
                    "glyphicon glyphicon-chevron-down",
                    "black",
                )
    for group in unassigned:
        for p, point in enumerate(group):
            d = point.desc.replace("\n", "<br/>").replace(r"`", r"\`")
            text = (
                "<p>"
                + f"Unassigned point: {p+1} / {len(group)}</br>"
                + f"Location (lon/lat): {point[0]}, {point[1]}"
                + "".join(["&nbsp;" for _ in range(0, 80)])
                + "</p>"
                + f"JSON:</br><pre><code>{d}</code></pre></br>"
            )
            plot_map_point(unassigned_group, point, text, weight_points, COLOR_UNASSIGNED)

    # Add all grouped parts to the map
    for k in route_groups:
        route_groups[k].add_to(m)
    if len(unassigned) > 0:
        unassigned_group.add_to(m)

    # Add button to expand the map to fullscreen
    plugins.Fullscreen(
        position="topright",
        title="Expand me",
        title_cancel="Exit me",
    ).add_to(m)

    # Create overlay tree for advanced control of route/unassigned layers
    overlay_tree = {
        "label": "Overlays",
        "select_all_checkbox": "Un/select all",
        "children": [],
    }
    if len(unassigned) > 0:
        overlay_tree["children"].append({"label": "Unassigned", "layer": unassigned_group})
    if len(route_groups) > 0:
        overlay_tree["children"].append(
            {
                "label": "Routes",
                "select_all_checkbox": True,
                "collapsed": True,
                "children": [{"label": route_layer_names[v], "layer": v} for v in route_groups.values()],
            },
        )

    # Add control for all layers and write file
    plugins.TreeLayerControl(base_tree=base_tree, overlay_tree=overlay_tree).add_to(m)

    # Fit map to bounds
    m.fit_bounds([[bbox.min_y, bbox.min_x], [bbox.max_y, bbox.max_x]])

    # Return map
    return m


def plot(
    input_route: str,
    jpath_route: str,
    input_pos: str,
    jpath_pos: str,
    jpath_x: str,
    jpath_y: str,
    jpath_unassigned: str,
    jpath_unassigned_x: str,
    jpath_unassigned_y: str,
    swap: bool,
    coords: str,
    omit_start: bool,
    omit_end: bool,
    omit_short: int,
    route_direction: types.RouteDirectionIndicator,
    output_image: str,
    output_plot: str,
    output_map: str,
    stats_file: str,
    colors: str,
    sort_color: bool,
    weight_route: float,
    weight_points: float,
    no_points: bool,
    start_end_markers: bool,
    rk_osm: str,
    rk_bin: str,
    rk_profile: routingkit.RoutingKitProfile,
    rk_distance: bool,
    route_animation_color: str,
    custom_map_tile: list[str],
    plotly_theme: str,
    nextroute: bool,
):
    """
    Plots routes based on the given arguments.
    Interprets args, reads .json, collects some stats,
    plots a .png and plots an interactive .html map.
    """

    # Determine base filename
    base_name = "plot"  # Default for STDIN
    if input_route:
        base_name = input_route

    # Determine profile
    profile = RoutePlotProfile(
        jpath_route,
        jpath_pos,
        jpath_x,
        jpath_y,
        jpath_unassigned,
        jpath_unassigned_x,
        jpath_unassigned_y,
    )
    if nextroute:
        profile = nextroute_profile()

    # Parse data
    points, unassigned = parse(
        input_route,
        profile.jpath_route,
        profile.jpath_unassigned,
        profile.jpath_unassigned_x,
        profile.jpath_unassigned_y,
        input_pos,
        profile.jpath_pos,
        profile.jpath_x,
        profile.jpath_y,
    )

    # Quit on no points
    if len(points) <= 0:
        print("no points found in given file(s) using given filter(s)")
        return

    # Conduct some checks
    points, world_coords, dataerror = common.preprocess_coordinates(points, swap, coords)
    if dataerror:
        print(dataerror)
        return
    if len(unassigned) > 0:
        unassigned, world_coords, dataerror = common.preprocess_coordinates(unassigned, swap, coords)
        if dataerror:
            print(dataerror)
            return

    # Wrap in routes
    routes = [types.Route(r) for r in points]  # Wrap it
    if len(routes) <= 0:
        print(f"no routes could be extracted at the given path: {jpath_route}")
        return

    # Process routes
    for route in routes:
        # Collect some statistics of the route
        length = 0
        for i in range(1, len(route.points)):
            if world_coords:
                length += common.haversine(
                    route.points[i],
                    route.points[i - 1],
                )
            else:
                length += common.euclidean(
                    route.points[i],
                    route.points[i - 1],
                )
            route.points[i].distance = length
        route.length = length

    # Determine route shapes (if routingkit is available)
    if rk_osm:
        routingkit.query_routes(rk_bin, rk_osm, routes, rk_profile, rk_distance)

    # Dump some stats
    statistics(routes, unassigned, stats_file, world_coords)

    # Determine bbox
    bbox = common.bounding_box([r.points for r in routes])

    # Make simple plot of routes
    aspect_ratio = (bbox.height) / (bbox.width) if bbox.width > 0 else 1

    # Remove short routes
    if omit_short > 0:
        routes = [r for r in routes if len(r.points) > omit_short]

    # Prepares colors for the groups
    common.prepare_colors(routes, colors, sort_color)

    # Create figure
    fig = create_plot(
        routes,
        unassigned,
        "lon" if world_coords else "x",
        "lat" if world_coords else "y",
        plotly_theme,
        omit_start,
        omit_end,
        no_points,
        weight_points,
        weight_route,
    )

    # Save interactive plot
    plot_file = output_plot
    if not plot_file:
        plot_file = base_name + ".plot.html"
        print(f"Plotting interactive plot to {plot_file}")
    fig.write_html(plot_file)

    # Save plot image
    image_file = output_image
    if not image_file:
        image_file = base_name + ".plot.png"
        print(f"Plotting image to {image_file}")
    fig.write_image(
        image_file,
        width=min(common.IMAGE_SIZE, common.IMAGE_SIZE / aspect_ratio),
        height=min(common.IMAGE_SIZE, common.IMAGE_SIZE * aspect_ratio),
    )

    # Skip plotting on map, if no geo-coordinates
    if not world_coords:
        print("No world coordinates, skipping map plotting")
        quit()

    # Create map
    m = create_map(
        routes,
        unassigned,
        no_points,
        weight_points,
        weight_route,
        omit_start,
        omit_end,
        route_direction,
        route_animation_color,
        start_end_markers,
        custom_map_tile,
        rk_distance,
    )

    # Save map
    map_file = output_map
    if not map_file:
        map_file = base_name + ".map.html"
        print(f"Plotting map to {map_file}")
    m.save(map_file)


def nextroute_profile() -> RoutePlotProfile:
    """
    Returns the nextroute profile.
    """
    return RoutePlotProfile(
        jpath_route="solutions[-1].vehicles[*].route",
        jpath_x="stop.location.lon",
        jpath_y="stop.location.lat",
        jpath_unassigned="solutions[-1].unplanned[*]",
        jpath_unassigned_x="location.lon",
        jpath_unassigned_y="location.lat",
    )


def plot_map_point(map, point, text, weight, color):
    """
    Plots a point on the given map.
    """
    popup_text = folium.Html(text, script=True)
    popup = folium.Popup(popup_text, max_width=450, sticky=True)
    marker = folium.CircleMarker(
        (point[1], point[0]),  # folium operates on lat/lon
        color=color,
        popup=popup,
        radius=3 * weight,
        fill=True,
        fillOpacity=1.0,
    )
    marker.options["fillOpacity"] = 1.0
    marker.add_to(map)


def plot_map_marker(map, point, text, icon, color):
    """
    Plots a marker on the given map.
    """
    popup_text = folium.Html(text, script=True)
    popup = folium.Popup(popup_text, max_width=450, sticky=True)
    marker = folium.Marker(
        (point[1], point[0]),  # folium operates on lat/lon
        popup=popup,
        icon=folium.Icon(color=color, icon=icon),
    )
    marker.add_to(map)


def plot_map_route(
    map: object,
    route: types.Route,
    route_idx: int,
    route_count: int,
    weight: float,
    omit_start: bool,
    omit_end: bool,
    direction: types.RouteDirectionIndicator = types.RouteDirectionIndicator.none,
    animation_bg_color: str = "FFFFFF",
    rk_factor: float = None,
    rk_unit: str = None,
):
    """
    Plots a route on the given map.
    """
    rk_text = ""
    if route.legs is not None:
        rk_text = f"Route cost (routingkit): {sum(route.leg_costs) * rk_factor:.2f} {rk_unit}</br>"
    popup_text = folium.Html(
        "<p>"
        + f"Route: {route_idx+1} / {route_count}</br>"
        + f"Route points: {len(route.points)}</br>"
        + f"Route length: {route.length:.2f} km ({common.km_to_miles(route.length):.2f} miles)</br>"
        + rk_text
        + "</p>",
        script=True,
    )
    popup = folium.Popup(popup_text, max_width=450, sticky=True)
    # Prepare polyling of route (folium operates on lat/lon)
    raw_line = [(p.lat, p.lon) for p in route.to_polyline(omit_start, omit_end)]
    if len(raw_line) <= 0:
        return
    if direction == types.RouteDirectionIndicator.none:
        folium.PolyLine(
            raw_line,
            color=route.color.hex,
            popup=popup,
            weight=5 * weight,
        ).add_to(map)
    elif direction == types.RouteDirectionIndicator.arrow:
        polyline = folium.PolyLine(
            raw_line,
            color=route.color.hex,
            popup=popup,
            weight=5,
        )
        polyline.add_to(map)
        plugins.PolyLineTextPath(
            polyline,
            "\u25ba     ",
            repeat=True,
            center=True,
            offset=10.35 * weight,
            attributes={"fill": route.color.hex, "font-size": f"{300*weight}%"},
        ).add_to(map)
    elif direction == types.RouteDirectionIndicator.animation:
        plugins.AntPath(
            locations=raw_line,
            dash_array=[20, 30],
            color=f"#{animation_bg_color}",
            pulse_color=route.color.hex,
            delay=1000,
            popup=popup,
            weight=5 * weight,
            opacity=1,
        ).add_to(map)
    else:
        raise Exception(f"unknown direction indicator {direction}")


def statistics(
    routes: list[types.Route],
    unassigned: list[list[types.Point]],
    stats_file: str,
    world_coords: bool,
):
    """
    Outlines some route statistics. Statistics are written to file, if provided.
    """
    # Collect statistics
    stops = [len(r.points) for r in routes]
    lengths = [r.length for r in routes]
    diameters = []
    for r in routes:
        max_diameter = 0
        for p1 in r.points:
            for p2 in r.points:
                if world_coords:
                    distance = common.haversine(p1, p2)
                else:
                    distance = common.euclidean(p1, p2)
                if distance > max_diameter:
                    max_diameter = distance
        diameters.append(max_diameter)
    stats = [
        types.Stat("nroutes", "Route count", len(routes)),
        types.Stat("nstops_max", "Route stops (max)", max(stops)),
        types.Stat("nstops_min", "Route stops (min)", min(stops)),
        types.Stat("nstops_avg", "Route stops (avg)", sum(stops) / float(len(routes))),
        types.Stat("nstops_total", "Route stops (total)", sum(stops)),
        types.Stat("length_max", "Route length (max)", max(lengths)),
        types.Stat("length_min", "Route length (min)", min(lengths)),
        types.Stat("length_avg", "Route length (avg)", sum(lengths) / float(len(routes))),
        types.Stat("length_total", "Route length (total)", sum(lengths)),
        types.Stat("diameter_max", "Route diameter (max)", max(diameters)),
        types.Stat("diameter_min", "Route diameter (min)", min(diameters)),
        types.Stat("diameter_avg", "Route diameter (avg)", sum(diameters) / float(len(routes))),
        types.Stat("nunassigned", "Unassigned stops", sum([len(g) for g in unassigned])),
    ]

    if all((r.legs is not None) for r in routes):
        costs = [sum(r.leg_costs) for r in routes]
        stats.extend(
            [
                types.Stat("costs_max", "RK costs (max)", max(costs)),
                types.Stat("costs_min", "RK costs (min)", min(costs)),
                types.Stat("costs_avg", "RK costs (avg)", sum(costs) / float(len(routes))),
            ]
        )

    # Log statistics
    print("Route stats")
    for stat in stats:
        print(f"{stat.desc}: {stat.val:.2f}")

    # Write statistics to file
    if stats_file:
        stats_table = {}
        for stat in stats:
            stats_table[stat.name] = stat.val
        with open(stats_file, "w+") as f:
            json.dump(stats_table, f)
