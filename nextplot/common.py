import json
import math
import sys

import colorutils
import folium
import jsonpath_ng

from . import types

# ==================== Shared constants

IMAGE_SIZE = 2000

# ==================== Shared arguments


def generic_arguments(parser):
    """
    Defines arguments common to geographic plotting.
    """
    parser.add_argument(
        "--jpath_x",
        type=str,
        nargs="?",
        default="lon",
        help="relative JSON path to the x-coordinate" + " (if coordinates are stored as [x,y], use empty string: '')",
    )
    parser.add_argument(
        "--jpath_y",
        type=str,
        nargs="?",
        default="lat",
        help="relative JSON path to the y-coordinate" + " (if coordinates are stored as [x,y], use empty string: '')",
    )
    parser.add_argument(
        "--output_image",
        type=str,
        nargs="?",
        default="",
        help="output image path (png-file)",
    )
    parser.add_argument(
        "--output_plot",
        type=str,
        nargs="?",
        default="",
        help="output plot path (html-file)",
    )
    parser.add_argument(
        "--output_map",
        type=str,
        nargs="?",
        default="",
        help="output map path (html-file)",
    )
    parser.add_argument(
        "--swap",
        dest="swap",
        action="store_true",
        default=False,
        help="indicates whether to swap lat/lon",
    )
    parser.add_argument(
        "--coords",
        default="auto",
        const="auto",
        nargs="?",
        choices=["euclidean", "haversine", "auto"],
        help="automatically determine coordinate nature" + " or enforce euclidean or haversine (default: %(default)s)",
    )
    parser.add_argument(
        "--sort_color",
        dest="sort_color",
        action="store_true",
        default=False,
        help="indicates whether to sort colors",
    )
    parser.add_argument(
        "--colors",
        type=str,
        nargs="?",
        default="auto",
        help="color profile to use (e.g.: cloud, rainbow)",
    )
    parser.add_argument(
        "--custom_map_tile",
        nargs="+",
        default=[],
        help="add further folium custom map tiles "
        + '(format: <url>,<name>,<attribution>" '
        + '[e.g.: "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png'
        + ',DarkMatter no labels,OpenStreetMap authors"])',
    )
    parser.add_argument(
        "--plotly_theme",
        type=str,
        nargs="?",
        default="plotly_dark",
        help="plotly theme to use (e.g.: plotly_dark, plotly_white, etc. - "
        + "see https://plotly.com/python/templates/ for more)",
    )
    parser.add_argument(
        "--stats_file",
        type=str,
        nargs="?",
        default="",
        help="path to file where detailed stats should be written",
    )


# ==================== Shared code


def load_data(input_groups: str, input_positions: str) -> tuple[str, str, str]:
    """
    Loads the raw location and position data.
    """
    content_locations = ""
    if len(input_groups) > 0:
        with open(input_groups) as jsonFile:
            content_locations = jsonFile.read()
    else:
        content_locations = "".join(sys.stdin.readlines())
    content_positions = content_locations
    if len(input_positions) > 0:
        with open(input_positions) as jsonFile:
            content_positions = jsonFile.read()

    return content_locations, content_positions


def extract_position(value, jpath_x="", jpath_y="") -> types.Position:
    """
    Extracts one point from the given JSON by either using the given
    relative JSON path or assuming a two-element list of float.
    """
    try:
        desc = json.dumps(value, indent=2, sort_keys=True)
        if jpath_x and jpath_y:
            x_expr, y_expr = jsonpath_ng.parse(jpath_x), jsonpath_ng.parse(jpath_y)
            x_val, y_val = x_expr.find(value), y_expr.find(value)
            if len(x_val) != 1:
                raise Exception(f"unable to parse x value from {desc} using {jpath_x}")
            if len(y_val) != 1:
                raise Exception(f"unable to parse y value from {desc} using {jpath_y}")
            return types.Position(float(x_val[0].value), float(y_val[0].value), desc)
        else:
            return types.Position(float(value[0]), float(value[1]), desc)
    except Exception:
        print(
            f"error parsing point using {jpath_x} and {jpath_y}, "
            + "please make sure the paths point to valid numbers x/y. point data:"
        )
        print(desc)
        raise


def is_two_tuple(value, type):
    """
    Checks whether the given value can be converted to a point.
    """
    return isinstance(value, list) and len(value) == 2 and isinstance(value[0], type) and isinstance(value[1], type)


def extract_position_groups(
    json_groups,
    jpath_groups,
    json_pos,
    jpath_pos,
    jpath_x="",
    jpath_y="",
) -> list[list[types.Position]]:
    """
    Extracts grouped positions (as in clusters, routes) from JSON.
    If no specific path for positions (jpath_pos) is given,
    it is assumed that the path to the groups (jpath_groups)
    already is a list of positions. Furthermore, jpath_x & jpath_x
    can be used to further modify the location of the positions,
    if they are not a list of length two (but instead an object with
    x, y fields for example).
    """
    # Extract all positions, if given explicitly
    positions = []
    if jpath_pos:
        point_data = json.loads(json_pos)
        point_expression = jsonpath_ng.parse(jpath_pos)
        for match in point_expression.find(point_data):
            if is_two_tuple(match.value, (int, float)):  # It's already a point
                positions.append(extract_position(match.value, jpath_x, jpath_y))
            elif isinstance(match.value, list):  # It's a list of positions
                for point_val in match.value:
                    positions.append(extract_position(point_val, jpath_x, jpath_y))
            else:  # We cannot handle this case
                raise f"not processable value format for a point: {match.value}"
    # Extract groups of values
    group_data = json.loads(json_groups)
    group_expression = jsonpath_ng.parse(jpath_groups)
    # Extract all groups
    groups, oob_indices = [], []
    for match in group_expression.find(group_data):
        # If the value is null, we skip it (with a warning)
        if match.value is None:
            print(f"Warning! Found 'null' value at {str(match.full_path)}, skipping...")
            continue
        # If no separate position file was given, we expect positions to be given
        group = []
        if len(positions) == 0:
            if is_two_tuple(match.value, float) or is_two_tuple(match.value, int):
                group.append(extract_position(match.value))
            else:
                if isinstance(match.value, list):
                    for val in match.value:
                        if is_two_tuple(val, float) or is_two_tuple(val, int):
                            group.append(extract_position(val))
                        else:
                            group.append(extract_position(val, jpath_x, jpath_y))
                else:
                    group.append(extract_position(match.value, jpath_x, jpath_y))
        # Else we expect indices pointing to the list of positions
        else:
            # Extract full list of indices for the group
            indices = []
            if isinstance(match.value, int):
                indices = [match.value]
            elif isinstance(match.value, list):
                for val in match.value:
                    sub_indices = []
                    if isinstance(val, int):
                        sub_indices = [val]
                    elif is_two_tuple(val, int):
                        sub_indices = range(val[0], val[1] + 1)
                    else:
                        raise f"not processable value format: {val}"
                    for p in sub_indices:
                        indices.append(p)
            # Convert indices to points
            for index in indices:
                if 0 <= index < len(positions):
                    group.append(positions[index].clone())
                else:
                    oob_indices.append(index)
        groups.append(group)
    # Warn about out-of-bound indices
    if len(oob_indices) > 0:
        oobs = ", ".join([str(e) for e in oob_indices])
        print(f"Warning! {len(oob_indices)} indices were out of bounds and ignored: {oobs}")
    # Return
    return groups


def preprocess_coordinates(points, swap, desired_coordinates):
    """
    Checks the given positions for being from world coordinate domain
    and performs some additional checks.
    """
    # Swap points, if desired
    if swap:
        for pl in points:
            for p in pl:
                p.lon, p.lat = p.lat, p.lon
    # Check all positions against valid world coordinate ranges
    all_lon_ok = all((-180 <= p[0] <= 180) for point in points for p in point)
    all_lat_ok = all((-90 <= p[1] <= 90) for point in points for p in point)
    # Determine position nature
    world_coords = all_lon_ok and all_lat_ok
    if desired_coordinates == "euclidean":
        world_coords = False
    elif desired_coordinates == "haversine" and not world_coords:
        return None, None, "positions do not satisfy lon/lat ranges"
    return points, world_coords, ""


def km_to_miles(km):
    """
    Convert a distance in km to miles.
    """
    return km * 0.621371


def cw_angle_distance(origin, point):
    """
    Gets angle and distance for a point that can be used for sorting.
    """
    ref_vec = [0, 1]
    # Vector between point and the origin: v = p - o
    vector = [point[0] - origin[0], point[1] - origin[1]]
    # Length of vector: ||v||
    lenvector = math.hypot(vector[0], vector[1])
    # If length is zero there is no angle
    if lenvector == 0:
        return -math.pi, 0
    # Normalize vector: v/||v||
    normalized = [vector[0] / lenvector, vector[1] / lenvector]
    dotprod = normalized[0] * ref_vec[0] + normalized[1] * ref_vec[1]  # x1*x2 + y1*y2
    diffprod = ref_vec[1] * normalized[0] - ref_vec[0] * normalized[1]  # x1*y2 - y1*x2
    angle = math.atan2(diffprod, dotprod)
    # Negative angles represent counter-clockwise angles so we need to subtract them
    # from 2*pi (360 degrees)
    if angle < 0:
        return 2 * math.pi + angle, lenvector
    # I return first the angle because that's the primary sorting criterium
    # but if two vectors have the same angle then the shorter distance should come first.
    return angle, lenvector


def haversine(p1, p2):
    """
    Calculate the great circle distance between two points
    on the earth (specified in decimal degrees)
    (source: https://stackoverflow.com/questions/4913349)
    """
    lon1, lat1, lon2, lat2 = p1[0], p1[1], p2[0], p2[1]
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])

    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers. Use 3956 for miles
    return c * r


def euclidean(p1, p2):
    """
    Calculates the euclidean distance between the two given points.
    """
    return math.sqrt(math.pow(p1[0] - p2[0], 2) + math.pow(p1[1] - p2[1], 2))


def bounding_box(points) -> types.BoundingBox:
    """
    Calculates the bounding box of the given points.
    """
    # Determine size
    pos_x = [p[0] for pl in points for p in pl]
    pos_y = [p[1] for pl in points for p in pl]
    return types.BoundingBox(min(pos_x), max(pos_x), min(pos_y), max(pos_y))


def create_map(lon: float, lat: float, custom_layers: list[str] = None) -> tuple[folium.Map, dict[str, any]]:
    """
    Creates a default folium map focused on the given coordinates. Furthermore, it
    returns a tree structure that can be used to select different base layers
    using the TreeLayerControl.
    """
    m = folium.Map(
        location=[lat, lon],
        zoomSnap=0.25,
        zoomDelta=0.25,
        wheelPxPerZoomLevel=180,
    )

    tile_layers = [
        ("openstreetmap", folium.TileLayer("openstreetmap").add_to(m)),
        ("cartodbdark_matter", folium.TileLayer("cartodbdark_matter").add_to(m)),
        ("cartodb positron", folium.TileLayer("cartodb positron").add_to(m)),
    ]

    if custom_layers:
        for layer in custom_layers:
            if layer.startswith("http"):
                elements = layer.split(",")
                if len(elements) != 3:
                    raise Exception(f"Invalid custom layer definition: {layer}. Expected <url>,<name>,<attribution>")
                tile_layers.append(
                    (
                        elements[1],
                        folium.TileLayer(
                            tiles=elements[0],
                            name=elements[1],
                            attr=elements[2],
                        ).add_to(m),
                    )
                )
            else:
                raise Exception(f"Invalid custom layer definition: {layer}. Expected <url>,<name>,<attribution>")

    base_tree = {
        "label": "Base Layers",
        "children": [
            {
                "label": "Tiles",
                "radioGroup": "tiles",
                "children": [{"label": name, "layer": layer} for name, layer in tile_layers],
            },
        ],
    }

    return m, base_tree


# ==================== Color handling


# Defines the colors as they are used in cloud console
CLOUD_COLORS = [
    colorutils.Color(hex="#4e79a7"),
    colorutils.Color(hex="#f28e2c"),
    colorutils.Color(hex="#e15759"),
    colorutils.Color(hex="#76b7b2"),
    colorutils.Color(hex="#59a14f"),
    colorutils.Color(hex="#edc949"),
    colorutils.Color(hex="#af7aa1"),
    colorutils.Color(hex="#ff9da7"),
    colorutils.Color(hex="#7b47b2"),
    colorutils.Color(hex="#c5a493"),
    colorutils.Color(hex="#a0d86f"),
    colorutils.Color(hex="#9c755f"),
    colorutils.Color(hex="#1f78b4"),
    colorutils.Color(hex="#cab2d6"),
    colorutils.Color(hex="#cd672e"),
    colorutils.Color(hex="#fdbf6f"),
    colorutils.Color(hex="#33bb85"),
    colorutils.Color(hex="#bb9b00"),
    colorutils.Color(hex="#fb9a99"),
    colorutils.Color(hex="#a6cee3"),
]


def range_step(start: float, end: float, value: float) -> float:
    """
    Puts a fractional value [0,1] between start and end, i.e., 0 will be equal to start and 1 to end.
    """
    if start < end:
        return start + (end - start) * value
    else:
        return start - (start - end) * value


def gradient(start: colorutils.Color, end: colorutils.Color, count: int) -> list[str]:
    """
    Returns a gradient from start to end color (including both ends)
    """
    if count <= 0:
        return []
    elif count == 1:
        return start
    else:
        return [
            colorutils.Color(
                rgb=(
                    range_step(start.rgb[0], end.rgb[0], i / (count - 1)),
                    range_step(start.rgb[1], end.rgb[1], i / (count - 1)),
                    range_step(start.rgb[2], end.rgb[2], i / (count - 1)),
                )
            )
            for i in range(count)
        ]


def multi_gradient(colors: list[colorutils.Color], count: int) -> list[str]:
    """
    Creates a gradient across the given colors and returns as many colors as defined by count.
    """
    # # If count is smaller than provided colors, simply enumerate the colors
    if count < len(colors):
        return [colors[i] for i in range(count)]

    # Determine number of colors per gradient sections
    gradient_count = len(colors) - 1
    target_count = int(count / gradient_count)
    counts = [target_count for _ in range(gradient_count)]
    overall_count = sum(counts)
    # Fill up rounding errors
    for i in range(len(counts)):
        if overall_count < count:
            counts[i] += 1
            overall_count += 1
        else:
            break

    # Create and return colors
    multi = []
    for c, count in enumerate(counts):
        # Create gradient from start color to end color of this range
        # Note: to have more accurate transitions, omit the start of the range and leave
        # it to the previous range (except for the first one)
        if c == 0:
            multi.extend(list(gradient(colors[c], colors[c + 1], count)))
        else:
            multi.extend(list(gradient(colors[c], colors[c + 1], count + 1))[1:])
    return multi


def prepare_colors(point_groups, color_profile, sort_colors):
    """
    Sorts groups of points clockwise by their centroids.
    Color and centroid information will be added to the grouping objects
    as .centroid and .color.
    """
    # Determine coloring order
    color_sorting = list(range(len(point_groups)))
    if sort_colors:
        # Calculate centroids of all point groups
        for pg in point_groups:
            if len(pg.points) <= 0:
                continue  # Skip empty groups
            xs, ys = [p.lon for p in pg.points], [p.lat for p in pg.points]
            pg.centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
        # Calculate centroid of all group centroids
        xs, ys = (
            [r.centroid[0] for r in point_groups if hasattr(r, "centroid")],
            [r.centroid[1] for r in point_groups if hasattr(r, "centroid")],
        )
        centroid = (sum(xs) / len(xs), sum(ys) / len(ys))
        # Handle empty groups by cloning the group centroid for them
        for pg in filter(lambda p: not hasattr(p, "centroid"), point_groups):
            pg.centroid = centroid
        # Sort colors for groups clockwise by group centroids
        color_sorting = sorted(
            color_sorting,
            key=lambda i: cw_angle_distance(centroid, point_groups[i].centroid),
        )

    # Generate sufficient number of colors
    colors = get_colors(color_profile, len(color_sorting))

    # Set colors
    i = 0
    for i in range(len(color_sorting)):
        point_groups[color_sorting[i]].color = colors[i % len(colors)]
        i += 1


def get_colors(color_profile: str, count: int) -> list[colorutils.Color]:
    """
    Generates a set of colors according to the provided color profile.
    """
    # Generate colors to use (according to profile)
    if color_profile == types.ColorProfile.auto.value:
        if count > len(CLOUD_COLORS):
            color_profile = types.ColorProfile.rainbow.value
        else:
            color_profile = types.ColorProfile.cloud.value
    colors = [colorutils.Color(hsv=(188.0, 0.44, 0.46))]
    if color_profile == types.ColorProfile.cloud.value:
        colors = CLOUD_COLORS
    elif color_profile == types.ColorProfile.rainbow.value:
        colors = [colorutils.Color(hsv=((i / count * 360.0), 0.8, 0.8)) for i in range(count)]
    else:
        elements = color_profile.split(",")
        if elements[0].startswith("rainbow"):
            start, end, sat, val = (float(v) for v in elements[1:5])
            rng = (end - start) if start < end else (start - end)
            step = rng / count
            colors = [colorutils.Color(hsv=((start + i * step % 360.0), sat, val)) for i in range(count)]
        elif elements[0].startswith("gradient"):
            grad_colors = elements[1:]
            if len(grad_colors) < 2:
                raise f"at least 2 colors are required for gradient mode (got {len(grad_colors)})"
            colors = multi_gradient([colorutils.Color(hex=c) for c in grad_colors], count)
        else:
            raise Exception(f"Invalid color profile {color_profile}")
    return colors


def get_color(h: float, s: float, v: float) -> str:
    """
    Returns a color hex string as given by hue, saturation and value.

    param float h: Hue (0-360).
    param float s: Saturation (0-1).
    param float v: Value (0-1).
    """
    return colorutils.Color(hsv=(h, s, v)).hex
