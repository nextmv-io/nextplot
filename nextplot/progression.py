import collections
import datetime
import gzip
import json
import os
import re
import sys

import jsonpath_ng
import plotly.graph_objects as go

from . import common

# ==================== This file contains value progression plotting code (mode: 'progression')

# Define some helper data structures
Point = collections.namedtuple("Point", ["time", "value"])
Progression = collections.namedtuple("Progression", ["label", "points"])
Series = collections.namedtuple("Series", ["file", "label"])


# ==================== Progression plot profiles


class ProgressionPlotProfile:
    """
    Pre-configured plot profiles for progression plotting.
    """

    def __init__(
        self,
        jpath_solution: str = "",
        jpath_value: str = "",
        jpath_elapsed: str = "",
    ):
        self.jpath_solution = jpath_solution
        self.jpath_value = jpath_value
        self.jpath_elapsed = jpath_elapsed

    def __str__(self):
        return (
            "ProgressionPlotProfile("
            + f"jpath_solution={self.jpath_solution}, "
            + f"jpath_value={self.jpath_value}, "
            + f"jpath_elapsed={self.jpath_elapsed})"
        )


def nextroute_profile() -> ProgressionPlotProfile:
    """
    Returns the nextroute profile.
    """
    return ProgressionPlotProfile(
        jpath_solution="statistics.series_data.value.data_points[*]",
        jpath_elapsed="x",
        jpath_value="y",
    )


# ==================== Duration parsing


# Convert durations to datetime.timedelta
# Based on: https://github.com/icholy/durationpy

# Define unit sizes
NANOSECOND_SIZE = 1
MICROSECOND_SIZE = 1000 * NANOSECOND_SIZE
MILLISECOND_SIZE = 1000 * MICROSECOND_SIZE
SECOND_SIZE = 1000 * MILLISECOND_SIZE
MINUTE_SIZE = 60 * SECOND_SIZE
HOUR_SIZE = 60 * MINUTE_SIZE
DAY_SIZE = 24 * HOUR_SIZE
WEEK_SIZE = 7 * DAY_SIZE
MONTH_SIZE = 30 * DAY_SIZE
YEAR_SIZE = 365 * DAY_SIZE

UNITS = {
    "ns": NANOSECOND_SIZE,
    "us": MICROSECOND_SIZE,
    "µs": MICROSECOND_SIZE,
    "μs": MICROSECOND_SIZE,
    "ms": MILLISECOND_SIZE,
    "s": SECOND_SIZE,
    "m": MINUTE_SIZE,
    "h": HOUR_SIZE,
    "d": DAY_SIZE,
    "w": WEEK_SIZE,
    "mm": MONTH_SIZE,
    "y": YEAR_SIZE,
}


class DurationError(ValueError):
    """duration error"""


# ==================== Progression mode argument definition


def arguments(parser):
    """
    Defines arguments specific to value progression plotting.
    """
    parser.add_argument(
        "--input_progression",
        type=str,
        nargs="*",
        help="Solution files with labels (e.g.: --input_progression file1,file1.json)",
    )
    parser.add_argument(
        "--jpath_solution",
        type=str,
        nargs="?",
        default="solutions[*]",
        help="Path to solution element in JSON",
    )
    parser.add_argument(
        "--jpath_value",
        type=str,
        nargs="?",
        default="statistics.value",
        help="Path to value element within solution element",
    )
    parser.add_argument(
        "--jpath_elapsed",
        type=str,
        nargs="?",
        default="statistics.time.elapsed",
        help="Path to elapsed element within solution element",
    )
    parser.add_argument(
        "--output_png",
        type=str,
        nargs="?",
        default=None,
        help="Image file path",
    )
    parser.add_argument(
        "--output_html",
        type=str,
        nargs="?",
        default=None,
        help="Interactive html file path",
    )
    parser.add_argument(
        "--title",
        type=str,
        nargs="?",
        default=None,
        help="Title of the plot (will automatically infer one, if not set)",
    )
    parser.add_argument(
        "--label_x",
        type=str,
        nargs="?",
        default="time (seconds)",
        help="X-axis label",
    )
    parser.add_argument(
        "--label_y",
        type=str,
        nargs="?",
        default="solution value",
        help="Y-axis label",
    )
    parser.add_argument(
        "--color_profile",
        type=str,
        nargs="?",
        default="default",
        help="color profile to use (e.g.: cloud, rainbow)",
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
        "--legend_position",
        type=str,
        nargs="?",
        default="top",
        help="legend position (e.g.: top, bottom, left, right)",
    )
    parser.add_argument(
        "--weight",
        type=float,
        nargs="?",
        default=1,
        help="weight / width factor to apply to the points and lines (e.g., 1.5)",
    )
    parser.add_argument(
        "--nextroute",
        dest="nextroute",
        action="store_true",
        default=False,
        help="overrides jpaths for nextroute outputs",
    )


# ==================== Progression plotting specific functionality


def duration_from_str(duration):
    """
    Parse a duration string to a datetime.timedelta.
    """

    if duration in ("0", "+0", "-0"):
        return datetime.timedelta()

    pattern = re.compile(r"([\d\.]+)([a-zµμ]+)")
    matches = pattern.findall(duration)
    if not len(matches):
        raise DurationError(f"Invalid duration {duration}")

    total = 0
    sign = -1 if duration[0] == "-" else 1

    for value, unit in matches:
        if unit not in UNITS:
            raise DurationError(f"Unknown unit {unit} in duration {duration}")
        try:
            total += float(value) * UNITS[unit]
        except Exception:
            raise DurationError(f"Invalid value {value} in duration {duration}") from None

    microseconds = total / MICROSECOND_SIZE
    return datetime.timedelta(microseconds=sign * microseconds)


def read_content(input):
    """
    Reads the content of the given file.
    If the file is gzipped, it will be gunzipped during the process.
    If an empty string is given, content is read from stdin instead.
    """
    # Determine input (stdin vs. file)
    content = ""
    if input != "":
        # Check for gzip file
        gz = False
        with open(input, "rb") as test_f:
            gz = test_f.read(2) == b"\x1f\x8b"
        if gz:
            # Read gzip file
            with gzip.open(input, "rb") as f:
                content = f.read().decode("utf-8")
        else:
            # Read file
            with open(input) as output_file:
                content = output_file.read()
    else:
        # TODO: test for gzip
        # gz = False
        # sys.stdin.buffer.read(2)
        # Read from stdin
        content = sys.stdin.read()
    return content


# Return the longest prefix of all list elements.
def commonprefix(m):
    """
    Given a list of pathnames, returns the longest common leading component
    Source: https://stackoverflow.com/questions/6718196/determine-prefix-from-a-set-of-similar-strings
    """
    if not m:
        return ""
    s1 = min(m)
    s2 = max(m)
    for i, c in enumerate(s1):
        if c != s2[i]:
            return s1[:i]
    return s1


def parse(
    progression_data: list[tuple[str, str]],
    jpath_solution: str,
    jpath_value: str,
    jpath_elapsed: str,
) -> list[Progression]:
    """
    Parses the given content and returns the progression data.

    :param input_progressions: List of input data as string.
    :param jpath_solution: Path to solution element in JSON.
    :param jpath_value: Path to value element within solution element.
    :param jpath_elapsed: Path to elapsed element within solution element.
    :return: List of parsed progressions.
    """
    # Prepare
    progressions = []

    # Process all inputs
    for label, data in progression_data:
        # Process JSON
        json_data = json.loads(data)

        # Extract values
        points = []
        expr_solution = jsonpath_ng.parse(jpath_solution)
        expr_value = jsonpath_ng.parse(jpath_value)
        expr_elapsed = jsonpath_ng.parse(jpath_elapsed)
        for match_solution in expr_solution.find(json_data):
            value = expr_value.find(match_solution.value)
            elapsed = expr_elapsed.find(match_solution.value)
            if len(value) != 1:
                raise Exception(
                    f"Invalid number of value matches ({len(value)}) for {jpath_value}: {match_solution.value}"
                )
            if len(elapsed) != 1:
                raise Exception(
                    f"Invalid number of elapsed matches ({len(elapsed)}) for {jpath_elapsed}: {match_solution.value}"
                )
            try:
                # Try to parse seconds directly
                elapsed_sec = float(elapsed[0].value)
            except ValueError:
                # Parse duration string
                elapsed_sec = duration_from_str(elapsed[0].value).total_seconds()
            points.append(Point(elapsed_sec, value[0].value))

        # Collect progression
        progressions.append(Progression(label, points))

    # Return
    return progressions


def create_figure(
    progressions: list[Progression],
    title: str,
    label_x: str,
    label_y: str,
    color_profile: str,
    plotly_theme: str,
    legend_position: str,
    weight: float,
) -> go.Figure:
    """
    Creates a plotly figure from the given progressions.

    :param progressions: List of progressions.
    :param title: Title of the plot.
    :param label_x: Label of the x-axis.
    :param label_y: Label of the y-axis.
    :param color_profile: Color profile to use.
    :param plotly_theme: Plotly theme to use.
    :param legend_position: Legend position (top, bottom, left, right).
    :return: Plotly figure.
    """
    # Prepare colors
    colors = None
    if color_profile != "default":
        colors = common.get_colors(color_profile, len(progressions))

    # Set legend position
    if legend_position == "top":
        leg = {"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1}
    elif legend_position == "bottom":
        leg = {"orientation": "h", "yanchor": "top", "y": -0.2, "xanchor": "right", "x": 1}
    elif legend_position == "left":
        leg = {"orientation": "v", "yanchor": "top", "y": 1, "xanchor": "right", "x": -0.2}
    elif legend_position == "right":
        leg = {"orientation": "v", "yanchor": "top", "y": 1, "xanchor": "left", "x": 1.02}
    else:
        leg = None

    # Plot value progression
    fig = go.Figure(
        layout=go.Layout(
            title=go.layout.Title(text=title),
            xaxis_title=label_x,
            yaxis_title=label_y,
            template=plotly_theme,
            # margin=dict(l=20, r=20, b=20, t=20, pad=4),
            legend=leg,
        )
    )
    for i, prog in enumerate(progressions):
        xs = [p.time for p in prog.points]
        ys = [p.value for p in prog.points]
        if colors is not None:
            color = f"rgb({colors[i].rgb[0]},{colors[i].rgb[1]},{colors[i].rgb[2]})"
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    line={
                        "shape": "hv",
                        "color": color,
                        "width": weight * 2,
                    },
                    marker={
                        "size": weight * 4,
                    },
                    mode="lines+markers",
                    name=prog.label,
                )
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    line={
                        "shape": "hv",
                        "width": weight * 2,
                    },
                    marker={
                        "size": weight * 4,
                    },
                    mode="lines+markers",
                    name=prog.label,
                )
            )

    # Enforce legend (also for single trace plots)
    fig.update_layout(showlegend=True)

    # Return
    return fig


def plot(
    input_progression: list[str],
    jpath_solution: str,
    jpath_value: str,
    jpath_elapsed: str,
    output_png: str,
    output_html: str,
    title: str,
    label_x: str,
    label_y: str,
    color_profile: str,
    plotly_theme: str,
    legend_position: str,
    weight: float,
    nextroute: bool,
):
    """
    Plots value progression based on the given arguments.
    Interprets args, reads .json, plots a .png and plots an interactive .html.
    """
    # Apply profiles, if requested
    profile = ProgressionPlotProfile(
        jpath_solution=jpath_solution,
        jpath_value=jpath_value,
        jpath_elapsed=jpath_elapsed,
    )
    if nextroute:
        profile = nextroute_profile()

    # Prepare inputs
    inputs = input_progression
    # Default to one stdin file, if no inputs given
    if not inputs or len(inputs) <= 0:
        inputs = ["stdin,"]

    # Prepare inputs
    series = []
    for i in inputs:
        # Process input args
        label, file = i.split(",")
        # Add series
        series.append(Series(file, label))

    # Read input files as strings
    raw_data = [(s.label, read_content(s.file)) for s in series]

    # Parse input data
    progressions = parse(
        raw_data,
        profile.jpath_solution,
        profile.jpath_value,
        profile.jpath_elapsed,
    )

    # Determine common prefix (used as default for title and filenames)
    prefix = commonprefix([os.path.basename(s.file) for s in series])
    directory = os.path.dirname(commonprefix([s.file for s in series]))

    # Determine title
    if title is None:
        title = prefix
        if title == "":
            title = "stdin"

    # Plot
    fig = create_figure(
        progressions,
        title,
        label_x,
        label_y,
        color_profile,
        plotly_theme,
        legend_position,
        weight,
    )

    # Write image
    if output_png is None:
        output_png = os.path.join(directory, prefix + ".png")
        if output_png == "":
            output_png = "plot.png"
        print(f"Plotting image to {output_png}")
    fig.write_image(output_png, scale=3)

    # Write html
    if output_html is None:
        output_html = os.path.join(directory, prefix + ".html")
        if output_html == "":
            output_html = "plot.html"
        print(f"Plotting html to {output_html}")
    fig.write_html(output_html)
