import json
from collections.abc import Callable

import folium
import numpy as np
import plotly.graph_objects as go
import scipy.spatial
from folium import plugins

from . import common, types

# ==================== This file contains cluster plotting code (mode: 'cluster')


# ==================== Cluster mode argument definition


def arguments(parser):
    """
    Defines arguments specific to cluster plotting.
    """
    parser.add_argument(
        "--input_cluster",
        type=str,
        nargs="?",
        default="",
        help="path to the cluster file to plot",
    )
    parser.add_argument(
        "--jpath_cluster",
        type=str,
        nargs="?",
        default="state.clusters[*].points",
        help="JSON path to the cluster elements (XPATH like,"
        + " see https://goessner.net/articles/JsonPath/,"
        + ' example: "state.clusters[*].points")',
    )
    parser.add_argument(
        "--input_pos",
        type=str,
        nargs="?",
        default="",
        help="path to file containing the positions, if not supplied by cluster file",
    )
    parser.add_argument(
        "--jpath_pos",
        type=str,
        nargs="?",
        default="",
        help="JSON path to the positions, if cluster elements are stored as indices",
    )
    parser.add_argument(
        "--no_points",
        action="store_true",
        help="indicates whether to omit plotting the actual points in addition to the convex hull",
    )
    parser.add_argument(
        "--weight_points",
        type=float,
        nargs="?",
        default=1,
        help="point size (<1 decreases, >1 increases)",
    )


# ==================== Cluster plotting specific functionality


def convex_hull(points):
    """
    Calculates the convex hull for the given points and
    returns it as a sorted list of points.
    """

    if len(points) <= 2:
        return [(p.lon, p.lat) for p in points]

    np_points = np.array([(p.lon, p.lat) for p in points])
    hull = scipy.spatial.ConvexHull(np_points)
    simplices = hull.vertices.tolist()

    return [(points[s].lon, points[s].lat) for s in simplices]


def parse(
    input_cluster: str,
    jpath_cluster: str,
    input_pos: str,
    jpath_pos: str,
    jpath_x: str,
    jpath_y: str,
) -> tuple[list[list[types.Position]], list[list[types.Position]]]:
    """
    Parses the cluster data from the file(s).
    """
    # Load json data
    content_cluster, content_points = common.load_data(input_cluster, input_pos)

    # Extract clusters
    points = common.extract_position_groups(
        content_cluster,
        jpath_cluster,
        content_points,
        jpath_pos,
        jpath_x,
        jpath_y,
    )

    return points


def plot(
    input_cluster: str,
    jpath_cluster: str,
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
    no_points: bool,
    weight_points: float,
    custom_map_tile: list[str],
    plotly_theme: str,
):
    """
    Plots clusters based on the given arguments.
    Interprets args, reads .json, collects some stats,
    plots a .png and plots an interactive .html map.
    """

    # Determine base filename
    base_name = "plot"  # Default for STDIN
    if input_cluster:
        base_name = input_cluster

    # Parse data
    points = parse(
        input_cluster,
        jpath_cluster,
        input_pos,
        jpath_pos,
        jpath_x,
        jpath_y,
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

    # Determine bbox
    bbox = common.bounding_box(points)

    # Wrap in clusters
    clusters = [types.Cluster(p) for p in points]  # Wrap it
    if len(clusters) <= 0:
        print(f"no clusters could be extracted at the given path: {jpath_cluster}")
        return

    measure = common.haversine if world_coords else common.euclidean

    # Process clusters
    for cluster in clusters:
        # Collect some statistics of the cluster
        cluster.size = len(cluster.points)
        cluster.diameter = 0
        if len(cluster.points) > 0:
            centroid_x = sum([p.lon for p in cluster.points]) / len(cluster.points)
            centroid_y = sum([p.lat for p in cluster.points]) / len(cluster.points)
            cluster.centroid = (centroid_x, centroid_y)

        distances_from_centroid = [measure(p, cluster.centroid) for p in cluster.points]
        cluster.sum_of_distances_from_centroid = sum(distances_from_centroid)
        cluster.max_distance_from_centroid = max(distances_from_centroid, default=0)
        cluster.wcss = sum([measure(p, cluster.centroid) ** 2 for p in cluster.points])

        for i in range(len(cluster.points)):
            for j in range(len(cluster.points)):
                if i == j:
                    continue
                distance = measure(
                    cluster.points[i],
                    cluster.points[j],
                )
                if distance > cluster.diameter:
                    cluster.diameter = distance

    # Determine convex hulls
    for cluster in clusters:
        cluster.hull = convex_hull(cluster.points)

    # Dump some stats
    statistics(clusters, measure, stats_file)

    # Prepares colors for the groups
    common.prepare_colors(clusters, colors, sort_color)

    # Make simple plot of clusters
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

    # Plot clusters
    for i, cluster in enumerate(clusters):
        if len(cluster.points) <= 0:
            continue
        # Calculate hull of cluster
        hull_points = np.array(cluster.hull)
        # Repeat the first point at the end to close the polygon
        hull_points = np.append(hull_points, hull_points[0, :].reshape(1, 2), axis=0)
        # Plot hull
        fig.add_trace(
            go.Scatter(
                x=hull_points[:, 0],
                y=hull_points[:, 1],
                mode="lines",
                line={"color": cluster.color.hex, "width": 2},
                name=f"Cluster {i+1}",
                fill="toself",
            )
        )

    # Plot points
    if not no_points:
        for i, cluster in enumerate(clusters):
            if len(cluster.points) <= 0:
                continue
            # Plot points
            fig.add_trace(
                go.Scatter(
                    x=[p.lon for p in cluster.points],
                    y=[p.lat for p in cluster.points],
                    mode="markers",
                    marker={
                        "size": weight_points * 5,
                        "color": cluster.color.hex,
                    },
                    name=f"Cluster {i+1}",
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

    # Plot the clusters themselves
    for i, cluster in enumerate(clusters):
        if len(cluster.points) <= 0:
            continue
        layer_name = f"Cluster {i+1}"
        plot_groups[i] = folium.FeatureGroup(name=layer_name)
        group_names[plot_groups[i]] = layer_name
        text = (
            "<p>"
            + f"Cluster: {i} / {len(clusters)}</br>"
            + f"Cluster points: {cluster.size}</br>"
            + f"Cluster diameter: {cluster.diameter:.2f} km "
            + f"({common.km_to_miles(cluster.diameter):.2f} miles)</br>"
            + "</p>"
        )
        plot_map_cluster(plot_groups[i], cluster, text)

    # Plot the individual points
    if not no_points:
        for i, cluster in enumerate(clusters):
            for point in cluster.points:
                d = point.desc.replace("\n", "<br/>").replace(r"`", r"\`")
                text = (
                    f"<p>Location (lon/lat): {point[0]}, {point[1]}</p" + f"JSON:</br><pre><code>{d}</code></pre></br>"
                )
                plot_map_point(
                    plot_groups[i],
                    point,
                    text,
                    weight_points,
                    cluster.color.hex,
                )

    # Add all grouped parts to the map
    for k in plot_groups:
        plot_groups[k].add_to(m)

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
                "label": "Clusters",
                "select_all_checkbox": True,
                "collapsed": True,
                "children": [{"label": group_names[v], "layer": v} for v in plot_groups.values()],
            }
        ],
    }

    # Add control for all layers and write file
    plugins.TreeLayerControl(base_tree=base_tree, overlay_tree=overlay_tree).add_to(m)

    # Fit map to bounds
    m.fit_bounds([[bbox.min_y, bbox.min_x], [bbox.max_y, bbox.max_x]])

    # Save map
    m.save(map_file)


def plot_map_point(map, point, text, weight, color):
    """
    Plots a point on the given map.
    """
    popup_text = folium.Html(text, script=True)
    popup = folium.Popup(popup_text, max_width=450, sticky=True)
    marker = folium.Circle(
        (point[1], point[0]),  # folium operates on lat/lon
        color=color,
        popup=popup,
        radius=15 * weight,
        fill=True,
        fillOpacity=1.0,
    )
    marker.options["fillOpacity"] = 1.0
    marker.add_to(map)


def plot_map_cluster(
    map: object,
    cluster: object,
    text: str,
):
    """
    Plots a cluster on the given map.
    """
    popup_text = folium.Html(text, script=True)
    popup = folium.Popup(popup_text, max_width=450, sticky=True)
    mod_hull = [(y, x) for (x, y) in cluster.hull]  # folium operates on lat/lon
    polygon = folium.Polygon(
        mod_hull,
        color=cluster.color.hex,
        fill=True,
        popup=popup,
    )
    polygon.add_to(map)


def statistics(
    clusters: list[types.Cluster],
    measure: Callable[[types.Position, types.Position], float],
    stats_file: str,
):
    """
    Outlines some route statistics. Statistics are written to file, if provided.
    """
    # Collect statistics
    sizes, diameters = [r.size for r in clusters], [r.diameter for r in clusters]
    sum_of_max_distances = sum([c.max_distance_from_centroid for c in clusters])
    max_distance = max([c.max_distance_from_centroid for c in clusters])
    sum_of_distances = sum([c.sum_of_distances_from_centroid for c in clusters])
    wcss = sum([c.wcss for c in clusters])
    bad_assignments = 0
    for c in clusters:
        for p in c.points:
            distance_to_centroid = measure(c.centroid, p)
            distances_to_other_centroids = np.array(
                [[measure(c2.centroid, p) for c2 in clusters if hasattr(c2, "centroid")]]
            )
            if len(distances_to_other_centroids[distance_to_centroid > distances_to_other_centroids]):
                bad_assignments += 1

    stats = [
        types.Stat("npoints", "Total points", sum([len(c.points) for c in clusters])),
        types.Stat("nclusters", "Cluster count", len(clusters)),
        types.Stat("clust_size_max", "Cluster size (max)", max(sizes)),
        types.Stat("clust_size_min", "Cluster size (min)", min(sizes)),
        types.Stat("clust_size_avg", "Cluster size (avg)", sum(sizes) / float(len(clusters))),
        types.Stat(
            "cluster_size_var",
            "Cluster size (variance)",
            np.var(np.array([len(c.points) for c in clusters])),
        ),
        types.Stat("clust_diam_max", "Cluster diameter (max)", max(diameters)),
        types.Stat("clust_diam_min", "Cluster diameter (min)", min(diameters)),
        types.Stat(
            "clust_diam_avg",
            "Cluster diameter (avg)",
            sum(diameters) / float(len(clusters)),
        ),
        types.Stat(
            "sum_max_distances",
            "Sum of max distances from centroid",
            sum_of_max_distances,
        ),
        types.Stat("distance_from_centroid_max", "Max distance from centroid", max_distance),
        types.Stat(
            "distance_from_centroid_sum",
            "Sum of distances from centroid",
            sum_of_distances,
        ),
        types.Stat("wcss", "Sum of squares from centroid", wcss),
        types.Stat("bad_assignments", "Bad assignments", bad_assignments),
    ]

    # Log statistics
    print("Cluster stats")
    for stat in stats:
        print(f"{stat.desc}: {stat.val:.2f}")

    # Write statistics to file
    if stats_file:
        stats_table = {}
        for stat in stats:
            stats_table[stat.name] = stat.val
        with open(stats_file, "w+") as f:
            json.dump(stats_table, f)
