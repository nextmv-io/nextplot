import json

import folium
import jsonpath_ng
from folium import plugins
from folium.elements import JSCSSMixin
from folium.map import Layer
from jinja2 import Template

from . import common

# ==================== This file contains plain geojson plotting code (mode: 'geojson')


# ==================== geojson mode argument definition


def arguments(parser):
    """
    Defines arguments specific to geojson plotting.
    """
    parser.add_argument(
        "--input_geojson",
        type=str,
        nargs="?",
        default="",
        help="path to the GeoJSON file to plot",
    )
    parser.add_argument(
        "--jpath_geojson",
        type=str,
        nargs="?",
        default="",
        help="JSON path to the GeoJSON elements (XPATH like,"
        + " see https://goessner.net/articles/JsonPath/,"
        + ' example: "state.routes[*].geojson")',
    )
    parser.add_argument(
        "--output_map",
        type=str,
        nargs="?",
        default=None,
        help="Interactive map file path",
    )
    parser.add_argument(
        "--custom_map_tile",
        nargs="+",
        default=[],
        help="add further folium custom map tiles "
        + "(either by name "
        + '[e.g.: "stamenwatercolor"] or '
        + 'by "<url>,<name>,<attribution>" '
        + '[e.g.: "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png'
        + ',DarkMatter no labels,OpenStreetMap authors"])',
    )
    parser.add_argument(
        "--style",
        dest="style",
        action="store_true",
        default=False,
        help="indicates whether to attempt to apply any style info found",
    )


# ==================== geojson plotting specific functionality


class StyledGeoJson(JSCSSMixin, Layer):
    """
    Creates a GeoJson which supports simplestyle and maki markers.

    source: https://stackoverflow.com/questions/66813862/loosing-geojsons-feature-property-information-when-visualising-by-using-folium
    """

    _template = Template(
        """
        {% macro script(this, kwargs) %}

            var {{ this.get_name() }} = L.geoJson({{ this.data }},
                {
                    useSimpleStyle: true,
                    useMakiMarkers: false
                }
            ).addTo({{ this._parent.get_name() }});
        {% endmacro %}
        """
    )

    default_js = [
        ("leaflet-simplestyle", "https://unpkg.com/leaflet-simplestyle"),
    ]

    def __init__(self, data, name=None, overlay=True, control=True, show=True):
        super().__init__(name=name, overlay=overlay, control=control, show=show)
        self._name = "StyledGeoJson"
        self.data = data


def parse(
    input_geojson: str,
    jpath_geojson: str,
) -> list[dict]:
    """
    Parses the geojson data object(s) from the file(s).
    """
    # Load json data
    content_geojson, _ = common.load_data(input_geojson, "")

    # Extract geojsons
    if jpath_geojson:
        expression = jsonpath_ng.parse(jpath_geojson)
        geojsons = [json.loads(match.value) for match in expression.find(content_geojson)]
    else:
        geojsons = [json.loads(content_geojson)]

    return geojsons


def plot(
    input_geojson: str,
    jpath_geojson: str,
    output_map: str,
    style: bool,
    custom_map_tile: list[str],
):
    """
    Plots geojson objects from the given file(s) onto a map.
    """

    # Determine base filename
    base_name = "plot"  # Default for STDIN
    if input_geojson:
        base_name = input_geojson

    # Parse data
    geojsons = parse(
        input_geojson,
        jpath_geojson,
    )

    # Quit on no points
    if len(geojsons) <= 0:
        print("no geojson found in given file")
        return

    # Determine bbox for zooming
    bbox_sw, bbox_ne = [90, 180], [-90, -180]
    for gj in geojsons:
        sw, ne = determine_geojson_bbox(gj)
        bbox_sw[0], bbox_sw[1] = min(bbox_sw[0], sw[0]), min(bbox_sw[1], sw[1])
        bbox_ne[0], bbox_ne[1] = max(bbox_ne[0], ne[0]), max(bbox_ne[1], ne[1])

    # Make map plot of geojson data
    map_file = output_map
    if not map_file:
        map_file = base_name + ".map.html"
        print(f"Plotting map to {map_file}")
    m, base_tree = common.create_map(
        (bbox_sw[1] + bbox_ne[1]) / 2.0,
        (bbox_sw[0] + bbox_ne[0]) / 2.0,
        custom_map_tile,
    )
    plot_groups = {}
    group_names = {}
    for i, gj in enumerate(geojsons):
        group_name = f"GeoJSON {i}"
        plot_groups[i] = folium.FeatureGroup(name=group_name)
        group_names[plot_groups[i]] = group_name
        if style:
            StyledGeoJson(gj).add_to(plot_groups[i])
        else:
            folium.GeoJson(gj).add_to(plot_groups[i])
        plot_groups[i].add_to(m)

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
                "label": "GeoJSONs",
                "select_all_checkbox": True,
                "collapsed": True,
                "children": [{"label": group_names[v], "layer": v} for v in plot_groups.values()],
            }
        ],
    }

    # Add control for all layers and write file
    plugins.TreeLayerControl(base_tree=base_tree, overlay_tree=overlay_tree).add_to(m)

    # Fit bounds
    m.fit_bounds([sw, ne])

    # Save map
    m.save(map_file)


def determine_geojson_bbox(d: dict) -> tuple[tuple[float, float], tuple[float, float]]:
    """
    Determine the bounding box of a geojson object.
    """
    sw, ne = [90, 180], [-90, -180]

    def traverse(d):
        if isinstance(d, list) and len(d) == 2 and isinstance(d[0], int | float):
            sw[0], sw[1] = min(sw[0], d[1]), min(sw[1], d[0])
            ne[0], ne[1] = max(ne[0], d[1]), max(ne[1], d[0])
            return
        elif isinstance(d, dict):
            for value in d.values():
                traverse(value)
        elif isinstance(d, list):
            for value in d:
                traverse(value)

    traverse(d)
    return sw, ne
