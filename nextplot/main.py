#!/usr/bin/env python3
# PYTHON_ARGCOMPLETE_OK
import argparse

import argcomplete

from . import __about__, cluster, common, geojson, point, progression, route, test

# ==================== Argument parsing


MODE_CLUSTER = "cluster"
MODE_GEOJSON = "geojson"
MODE_POINT = "point"
MODE_PROGRESSION = "progression"
MODE_ROUTE = "route"
MODE_TEST = "test"


def argparse_generate():
    """
    Creates the CLI argument parser.
    """
    parser = argparse.ArgumentParser(description=f"nextmv.io plotting tools (version: {__about__.__version__})")
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__about__.__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")
    routeparser = subparsers.add_parser(MODE_ROUTE)
    route.arguments(routeparser)
    common.generic_arguments(routeparser)
    clusterparser = subparsers.add_parser(MODE_CLUSTER)
    cluster.arguments(clusterparser)
    common.generic_arguments(clusterparser)
    pointparser = subparsers.add_parser(MODE_POINT)
    point.arguments(pointparser)
    common.generic_arguments(pointparser)
    progressionparser = subparsers.add_parser(MODE_PROGRESSION)
    progression.arguments(progressionparser)
    geojsonparser = subparsers.add_parser(MODE_GEOJSON)
    geojson.arguments(geojsonparser)
    testparser = subparsers.add_parser(MODE_TEST)
    test.arguments(testparser)
    return parser


def entry_point():
    """
    Main entry point.
    """
    # Read arguments
    parser = argparse_generate()
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Guide flow
    if args.command == MODE_ROUTE:
        route.plot(
            input_route=args.input_route,
            jpath_route=args.jpath_route,
            input_pos=args.input_pos,
            jpath_pos=args.jpath_pos,
            jpath_x=args.jpath_x,
            jpath_y=args.jpath_y,
            jpath_unassigned=args.jpath_unassigned,
            jpath_unassigned_x=args.jpath_unassigned_x,
            jpath_unassigned_y=args.jpath_unassigned_y,
            swap=args.swap,
            coords=args.coords,
            omit_start=args.omit_start,
            omit_end=args.omit_end,
            omit_short=args.omit_short,
            route_direction=args.route_direction,
            output_image=args.output_image,
            output_plot=args.output_plot,
            output_map=args.output_map,
            stats_file=args.stats_file,
            colors=args.colors,
            sort_color=args.sort_color,
            weight_route=args.weight_route,
            weight_points=args.weight_points,
            no_points=args.no_points,
            start_end_markers=args.start_end_markers,
            rk_osm=args.rk_osm,
            rk_bin=args.rk_bin,
            rk_profile=args.rk_profile,
            rk_distance=args.rk_distance,
            route_animation_color=args.route_animation_color,
            custom_map_tile=args.custom_map_tile,
            plotly_theme=args.plotly_theme,
            nextroute=args.nextroute,
        )
    elif args.command == MODE_CLUSTER:
        cluster.plot(
            input_cluster=args.input_cluster,
            jpath_cluster=args.jpath_cluster,
            input_pos=args.input_pos,
            jpath_pos=args.jpath_pos,
            jpath_x=args.jpath_x,
            jpath_y=args.jpath_y,
            swap=args.swap,
            coords=args.coords,
            output_image=args.output_image,
            output_plot=args.output_plot,
            output_map=args.output_map,
            stats_file=args.stats_file,
            colors=args.colors,
            sort_color=args.sort_color,
            no_points=args.no_points,
            weight_points=args.weight_points,
            custom_map_tile=args.custom_map_tile,
            plotly_theme=args.plotly_theme,
        )
    elif args.command == MODE_POINT:
        point.plot(
            input_point=args.input_point,
            jpath_point=args.jpath_point,
            input_pos=args.input_pos,
            jpath_pos=args.jpath_pos,
            jpath_x=args.jpath_x,
            jpath_y=args.jpath_y,
            swap=args.swap,
            coords=args.coords,
            output_image=args.output_image,
            output_plot=args.output_plot,
            output_map=args.output_map,
            stats_file=args.stats_file,
            colors=args.colors,
            sort_color=args.sort_color,
            weight_points=args.weight_points,
            custom_map_tile=args.custom_map_tile,
            plotly_theme=args.plotly_theme,
        )
    elif args.command == MODE_PROGRESSION:
        progression.plot(
            input_progression=args.input_progression,
            jpath_solution=args.jpath_solution,
            jpath_value=args.jpath_value,
            jpath_elapsed=args.jpath_elapsed,
            output_png=args.output_png,
            output_html=args.output_html,
            title=args.title,
            label_x=args.label_x,
            label_y=args.label_y,
            color_profile=args.color_profile,
            plotly_theme=args.plotly_theme,
            legend_position=args.legend_position,
            weight=args.weight,
            nextroute=args.nextroute,
        )
    elif args.command == MODE_GEOJSON:
        geojson.plot(
            input_geojson=args.input_geojson,
            jpath_geojson=args.jpath_geojson,
            output_map=args.output_map,
            style=args.style,
            custom_map_tile=args.custom_map_tile,
        )
    elif args.command == MODE_TEST:
        test.test_filter(
            input=args.input,
            jpath=args.jpath,
            stats=args.stats,
        )
    else:
        print("Unexpected input arguments. Please consult --help")
