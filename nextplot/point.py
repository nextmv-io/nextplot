import json
import sys
from collections.abc import Callable

import folium
import plotly.graph_objects as go
from folium import plugins

from . import common, types

# ==================== This file contains plain point plotting code (mode: 'point')


# ==================== Point mode argument definition


def arguments(parser):
    """
    Defines arguments specific to point plotting.
    """
    parser.add_argument(
        "--input_point",
        type=str,
        nargs="?",
        default="",
        help="path to the point file to plot",
    )
    parser.add_argument(
        "--jpath_point",
        type=str,
        nargs="?",
        default="state.clusters[*].points",
        help="JSON path to the point elements (XPATH like,"
        + " see https://goessner.net/articles/JsonPath/,"
        + ' example: "state.clusters[*].points")',
    )
    parser.add_argument(
        "--input_pos",
        type=str,
        nargs="?",
        default="",
        help="path to file containing the positions, if not supplied by point file",
    )
    parser.add_argument(
        "--jpath_pos",
        type=str,
        nargs="?",
        default="",
        help="JSON path to the positions, if point elements are stored as indices",
    )
    parser.add_argument(
        "--weight_points",
        type=float,
        nargs="?",
        default=1,
        help="point size (<1 decreases, >1 increases)",
    )


# ==================== Point plotting specific functionality


def parse(
    input_point: str,
    jpath_point: str,
    input_pos: str,
    jpath_pos: str,
    jpath_x: str,
    jpath_y: str,
) -> tuple[list[list[types.Position]], list[list[types.Position]]]:
    """
    Parses the point data from the file(s).
    """
    # Load json data
    content_point, content_coordinate = common.load_data(input_point, input_pos)

    # Extract points
    positions = common.extract_position_groups(
        content_point,
        jpath_point,
        content_coordinate,
        jpath_pos,
        jpath_x,
        jpath_y,
    )

    return positions


def plot(
    input_point: str,
    jpath_point: str,
    input_pos: str,
    jpath_pos: str,
    jpath_x: str,
    jpath_y: str,
    swap: bool,
    coords: str,
    output_image: str,
    output_plot: str,
    output_map: str,
    stats_file: str,
    colors: str,
    sort_color: bool,
    weight_points: float,
    custom_map_tile: list[str],
    plotly_theme: str,
):
    """
    Plots points based on the given arguments.
    Interprets args, reads .json, collects some stats,
    plots a .png and plots an interactive .html map.
    """

    # Determine base filename
    base_name = "plot"  # Default for STDIN
    if input_point:
        base_name = input_point

    # Parse data
    positions = parse(
        input_point,
        jpath_point,
        input_pos,
        jpath_pos,
        jpath_x,
        jpath_y,
    )

    # Quit on no points
    if len(positions) <= 0:
        print("no points found in given file(s) using given filter(s)")
        return

    # Conduct some checks
    positions, world_coords, dataerror = common.preprocess_coordinates(positions, swap, coords)
    if dataerror:
        print(dataerror)
        return

    # Determine bbox
    bbox = common.bounding_box(positions)

    # Wrap in meta object
    points = [types.Point(p) for p in positions]  # Wrap it
    if len(points) <= 0:
        print(f"no points could be extracted at the given path: {jpath_point}")
        return

    measure = common.haversine if world_coords else common.euclidean

    # Enumerate point groups
    for i in range(len(points)):
        points[i].group = i + 1

    # Prepares colors for the points
    common.prepare_colors(points, colors, sort_color)

    # Dump some stats
    statistics(points, measure, stats_file)

    # Make simple plot of points
    aspect_ratio = (bbox.height) / (bbox.width) if bbox.width > 0 else 1

    # Init plot
    fig = go.Figure(
        layout=go.Layout(
            xaxis_title="lon" if world_coords else "x",
            yaxis_title="lat" if world_coords else "y",
            template=plotly_theme,
            margin={"l": 20, "r": 20, "b": 20, "t": 20, "pad": 4},
            font={"size": 18},
            showlegend=False,
        )
    )

    # Plot points
    for i, pg in enumerate(points):
        if len(pg.points) <= 0:
            continue
        # Plot points
        fig.add_trace(
            go.Scatter(
                x=[p.lon for p in pg.points],
                y=[p.lat for p in pg.points],
                mode="markers",
                marker={
                    "size": weight_points * 5,
                    "color": pg.color.hex,
                },
                name=f"Group {i+1}",
            )
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

    # Make map plot of routes
    map_file = output_map
    if not map_file:
        map_file = base_name + ".map.html"
        print(f"Plotting map to {map_file}")
    m, base_tree = common.create_map(
        (bbox.max_x + bbox.min_x) / 2.0,
        (bbox.max_y + bbox.min_y) / 2.0,
        custom_map_tile,
    )
    plot_groups = {}
    group_names = {}

    for i, ps in enumerate(points):
        if len(ps.points) <= 0:
            continue
        layer_name = f"Point group {i+1}"
        plot_groups[i] = folium.FeatureGroup(name=layer_name)
        group_names[plot_groups[i]] = layer_name
        for point in ps.points:
            d = point.desc.replace("\n", "<br/>").replace(r"`", r"\`")
            popup_text = folium.Html(
                "<p>"
                + f"Location (lon/lat): {point[0]}, {point[1]}</br>"
                + f"Group: {ps.group}</br>"
                + f"Group size: {len(ps.points)}</br>"
                + "</p>"
                + f"JSON:</br><pre><code>{d}</code></pre></br>",
                script=True,
            )
            popup = folium.Popup(popup_text, max_width=450, sticky=True)
            marker = folium.Circle(
                (point[1], point[0]),  # folium operates on lat/lon
                color=ps.color.hex,
                popup=popup,
                radius=15 * weight_points,
                fill=True,
                fillOpacity=1.0,
            )
            marker.options["fillOpacity"] = 1.0
            marker.add_to(plot_groups[i])

    # Add all grouped parts to the map
    for g in plot_groups:
        plot_groups[g].add_to(m)

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
        "children": [
            {
                "label": "Point groups",
                "select_all_checkbox": True,
                "collapsed": True,
                "children": [{"label": group_names[v], "layer": v} for v in plot_groups.values()],
            }
        ],
    }

    # Add control for all layers and write file
    plugins.TreeLayerControl(base_tree=base_tree, overlay_tree=overlay_tree).add_to(m)

    # Fit bounds
    m.fit_bounds([[bbox.min_y, bbox.min_x], [bbox.max_y, bbox.max_x]])

    # Save map
    m.save(map_file)


def statistics(
    groups: list[list[types.Position]],
    measure: Callable[[types.Position, types.Position], float],
    stats_file: str,
):
    """
    Outlines some route statistics. Statistics are written to file, if provided.
    """
    # Collect statistics
    all_points = [item for sublist in groups for item in sublist.points]
    max, min, agg, avg = 0.0, sys.float_info.max, 0.0, 0.0
    dist_count = 0
    for i1, p1 in enumerate(all_points):
        for i2, p2 in enumerate(all_points):
            if i2 < i1:
                continue
            dist_count += 1
            dist = measure(p1, p2)
            agg += dist
            if max < dist:
                max = dist
            if min > dist:
                min = dist
    if min == sys.float_info.max:
        min = 0.0
    if dist_count > 0:
        avg = agg / dist_count

    stats = [
        types.Stat("npoints", "Total points", len(all_points)),
        types.Stat("distance_min", "Distance (min)", min),
        types.Stat("distance_max", "Distance (max)", max),
        types.Stat("distance_avg", "Distance (avg)", avg),
    ]

    # Log statistics
    print("Point stats")
    for stat in stats:
        print(f"{stat.desc}: {stat.val:.2f}")

    # Write statistics to file
    if stats_file:
        stats_table = {}
        for stat in stats:
            stats_table[stat.name] = stat.val
        with open(stats_file, "w+") as f:
            json.dump(stats_table, f)
