import argparse
import collections
import difflib
import os
import pathlib
import re
import subprocess
import sys

import imagehash
import pytest
from PIL import Image

# Define variables used by all tests (will be filled in by pre-test fixture)
READY = False
UPDATE = False
OUTPUT_DIR = None
DATA_DIR = None
NEXTPLOT_PATH = None


# Define CLI test parameters
MapTest = collections.namedtuple(
    "Test",
    [
        "name",
        "args",
        "out_img",
        "out_plot",
        "out_map",
        "golden_log",
        "golden_img",
        "golden_plot",
        "golden_map",
    ],
)
GeoJSONTest = collections.namedtuple(
    "Test",
    [
        "name",
        "args",
        "out_html",
        "golden_log",
        "golden_html",
    ],
)
ProgressionTest = collections.namedtuple(
    "Test",
    [
        "name",
        "args",
        "out_img",
        "out_html",
        "golden_log",
        "golden_img",
        "golden_html",
    ],
)


def _diff_report(expected: str, got: str) -> str:
    """
    Create a unified diff report between two strings.
    """
    diff = difflib.unified_diff(expected.splitlines(), got.splitlines())
    return "\n".join(list(diff))


def _prepare_tests() -> None:
    global READY, UPDATE, OUTPUT_DIR, DATA_DIR, NEXTPLOT_PATH
    # If it's the first test, setup all variables
    if not READY:
        # Read arguments
        parser = argparse.ArgumentParser(description="nextplot golden file tests")
        parser.add_argument(
            "--update",
            dest="update",
            action="store_true",
            default=False,
            help="updates the golden files",
        )
        args, _ = parser.parse_known_args()  # Ignore potentially forwarded pytest args
        UPDATE = args.update

        # Update if requested by env var
        update_requested = os.environ.get("UPDATE", "0")
        if update_requested == "1" or update_requested.lower() == "true":
            UPDATE = True

        # Set paths
        OUTPUT_DIR = str(pathlib.Path(__file__).parent.joinpath("./output").resolve())
        DATA_DIR = str(pathlib.Path(__file__).parent.joinpath("./testdata").resolve(strict=True))
        NEXTPLOT_PATH = str(pathlib.Path(__file__).parent.joinpath("../plot.py").resolve(strict=True))

        # Prepare output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Mark as ready
        READY = True


@pytest.fixture(autouse=True)
def run_around_tests() -> None:
    """
    Prepare tests and clean up.
    """
    _prepare_tests()

    # Run a test
    yield

    # Clean up
    # - nothing to do, we keep the output for manual inspection


def _clean(data: str) -> str:
    """
    Remove data subject to change from the given string.
    """
    # Remove any GUIDs
    data = re.sub(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", "", data)
    # Remove folium IDs
    data = re.sub(r"[a-f0-9]{32}", "", data)
    return data


def _run_map_test(test: MapTest) -> None:
    # Clear old results
    if os.path.isfile(test.out_img):
        os.remove(test.out_img)
    if os.path.isfile(test.out_map):
        os.remove(test.out_map)

    # Assemble command and arguments
    base = [sys.executable, NEXTPLOT_PATH]
    cmd = [*base, *test.args]
    cmd.extend(
        [
            "--output_image",
            test.out_img,
            "--output_plot",
            test.out_plot,
            "--output_map",
            test.out_map,
        ]
    )

    # Log
    cmd_string = " ".join(test.args)
    print(f"Invoking: {cmd_string}")

    # Run command
    result = subprocess.run(cmd, stdout=subprocess.PIPE)

    # Expect no errors
    assert result.returncode == 0

    # Compare log output
    output = result.stdout.decode("utf-8")
    if UPDATE:
        with open(test.golden_log, "w") as file:
            file.write(output)
    else:
        expected = ""
        with open(test.golden_log) as file:
            expected = file.read()
        assert output == expected, _diff_report(expected, output)

    # Compare plot file against expectation
    if UPDATE:
        # Copy plot file, but replace any GUIDs
        with open(test.out_plot) as fr:
            with open(test.golden_plot, "w") as fw:
                fw.write(_clean(fr.read()))
    else:
        # Compare plot file
        expected, got = "", ""
        with open(test.golden_plot) as f:
            expected = f.read()
        with open(test.out_plot) as f:
            got = _clean(f.read())
        assert got == expected, _diff_report(expected, got)

    # Compare map file against expectation
    if UPDATE:
        # Copy map file, but replace any GUIDs
        with open(test.out_map) as fr:
            with open(test.golden_map, "w") as fw:
                fw.write(_clean(fr.read()))
    else:
        # Compare map file
        expected, got = "", ""
        with open(test.golden_map) as f:
            expected = f.read()
        with open(test.out_map) as f:
            got = _clean(f.read())
        assert got == expected, _diff_report(expected, got)

    # Compare image file against expectation
    # (we cannot compare the html file, as it is not deterministic)
    hash_gotten = imagehash.phash(Image.open(test.out_img))
    if UPDATE:
        # Update expected hash
        with open(test.golden_img, "w") as f:
            f.write(str(hash_gotten) + "\n")
    else:
        # Compare image similarity via imagehash library
        hash_expected = None
        with open(test.golden_img) as f:
            hash_expected = imagehash.hex_to_hash(f.read().strip())
        distance = hash_gotten - hash_expected
        assert distance < 7, (
            f"hash distance too large: {distance},\n" + f"got:\t{hash_gotten}\n" + f"want:\t{hash_expected}"
        )


def _run_geojson_test(test: GeoJSONTest) -> None:
    # Clear old results
    if os.path.isfile(test.out_html):
        os.remove(test.out_html)

    # Assemble command and arguments
    base = [sys.executable, NEXTPLOT_PATH]
    cmd = [*base, *test.args]
    cmd.extend(
        [
            "--output_map",
            test.out_html,
        ]
    )

    # Log
    cmd_string = " ".join(test.args)
    print(f"Invoking: {cmd_string}")

    # Run command
    result = subprocess.run(cmd, stdout=subprocess.PIPE)

    # Expect no errors
    assert result.returncode == 0

    # Compare log output
    output = result.stdout.decode("utf-8")
    if UPDATE:
        with open(test.golden_log, "w") as file:
            file.write(output)
    else:
        expected = ""
        with open(test.golden_log) as file:
            expected = file.read()
        assert output == expected, _diff_report(expected, output)

    # Compare html file against expectation
    if UPDATE:
        # Copy html file, but replace any GUIDs
        with open(test.out_html) as fr:
            with open(test.golden_html, "w") as fw:
                fw.write(_clean(fr.read()))
    else:
        # Compare html file
        expected, got = "", ""
        with open(test.golden_html) as f:
            expected = f.read()
        with open(test.out_html) as f:
            got = _clean(f.read())
        assert got == expected, _diff_report(expected, got)


def _run_progression_test(test: ProgressionTest) -> None:
    # Clear old results
    if os.path.isfile(test.out_img):
        os.remove(test.out_img)
    if os.path.isfile(test.out_html):
        os.remove(test.out_html)

    # Assemble command and arguments
    base = [sys.executable, NEXTPLOT_PATH]
    cmd = [*base, *test.args]
    cmd.extend(
        [
            "--output_png",
            test.out_img,
            "--output_html",
            test.out_html,
        ]
    )

    # Log
    cmd_string = " ".join(test.args)
    print(f"Invoking: {cmd_string}")

    # Run command
    result = subprocess.run(cmd, stdout=subprocess.PIPE)

    # Expect no errors
    assert result.returncode == 0

    # Compare log output
    output = result.stdout.decode("utf-8")
    if UPDATE:
        with open(test.golden_log, "w") as file:
            file.write(output)
    else:
        expected = ""
        with open(test.golden_log) as file:
            expected = file.read()
        assert output == expected, _diff_report(expected, output)

    # Compare html file against expectation
    if UPDATE:
        # Copy html file, but replace any GUIDs
        with open(test.out_html) as fr:
            with open(test.golden_html, "w") as fw:
                fw.write(_clean(fr.read()))
    else:
        # Compare html file
        expected, got = "", ""
        with open(test.golden_html) as f:
            expected = f.read()
        with open(test.out_html) as f:
            got = _clean(f.read())
        assert got == expected, _diff_report(expected, got)

    # Compare image file against expectation
    # (we cannot compare the html file, as it is not deterministic)
    hash_gotten = imagehash.phash(Image.open(test.out_img))
    if UPDATE:
        # Update expected hash
        with open(test.golden_img, "w") as f:
            f.write(str(hash_gotten) + "\n")
    else:
        # Compare image similarity via imagehash library
        hash_expected = None
        with open(test.golden_img) as f:
            hash_expected = imagehash.hex_to_hash(f.read().strip())
        distance = hash_gotten - hash_expected
        assert distance < 7, (
            f"hash distance too large: {distance},\n" + f"got:\t{hash_gotten}\n" + f"want:\t{hash_expected}"
        )


def test_map_plot_cli_paris_route():
    test = MapTest(
        "paris-route",
        [
            "route",
            "--input_route",
            os.path.join(DATA_DIR, "paris-route.json"),
            "--jpath_route",
            "state.tours[*].route",
            "--jpath_x",
            "location[1]",
            "--jpath_y",
            "location[0]",
            "--omit_start",
            "--omit_end",
            "--custom_map_tile",
            'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png,DarkMatter no labels,<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            "--weight_route",
            "4",
            "--weight_points",
            "4",
        ],
        os.path.join(OUTPUT_DIR, "paris-route.plot.png"),
        os.path.join(OUTPUT_DIR, "paris-route.plot.html"),
        os.path.join(OUTPUT_DIR, "paris-route.html"),
        os.path.join(DATA_DIR, "paris-route.json.golden"),
        os.path.join(DATA_DIR, "paris-route.plot.png.golden"),
        os.path.join(DATA_DIR, "paris-route.plot.html.golden"),
        os.path.join(DATA_DIR, "paris-route.map.html.golden"),
    )
    _run_map_test(test)


def test_map_plot_cli_paris_cluster():
    test = MapTest(
        "paris-cluster",
        [
            "cluster",
            "--input_cluster",
            os.path.join(DATA_DIR, "paris-cluster.json"),
            "--jpath_cluster",
            "state.tours[*].route",
            "--jpath_x",
            "location[1]",
            "--jpath_y",
            "location[0]",
            "--no_points",
            "--custom_map_tile",
            'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png,DarkMatter no labels,<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            "--weight_points",
            "4",
        ],
        os.path.join(OUTPUT_DIR, "paris-cluster.plot.png"),
        os.path.join(OUTPUT_DIR, "paris-cluster.plot.html"),
        os.path.join(OUTPUT_DIR, "paris-cluster.html"),
        os.path.join(DATA_DIR, "paris-cluster.json.golden"),
        os.path.join(DATA_DIR, "paris-cluster.plot.png.golden"),
        os.path.join(DATA_DIR, "paris-cluster.plot.html.golden"),
        os.path.join(DATA_DIR, "paris-cluster.map.html.golden"),
    )
    _run_map_test(test)


def test_map_plot_cli_paris_point():
    test = MapTest(
        "paris-point",
        [
            "point",
            "--input_point",
            os.path.join(DATA_DIR, "paris-point.json"),
            "--jpath_point",
            "state[*].tours[*].route",
            "--jpath_x",
            "location[1]",
            "--jpath_y",
            "location[0]",
            "--weight_points",
            "4",
        ],
        os.path.join(OUTPUT_DIR, "paris-point.plot.png"),
        os.path.join(OUTPUT_DIR, "paris-point.plot.html"),
        os.path.join(OUTPUT_DIR, "paris-point.html"),
        os.path.join(DATA_DIR, "paris-point.json.golden"),
        os.path.join(DATA_DIR, "paris-point.plot.png.golden"),
        os.path.join(DATA_DIR, "paris-point.plot.html.golden"),
        os.path.join(DATA_DIR, "paris-point.map.html.golden"),
    )
    _run_map_test(test)


def test_map_plot_cli_paris_route_indexed():
    test = MapTest(
        "paris-route-indexed",
        [
            "route",
            "--input_route",
            os.path.join(DATA_DIR, "paris-route-indexed.json"),
            "--jpath_route",
            "state.tours[*].route",
            "--input_pos",
            os.path.join(DATA_DIR, "paris-pos.json"),
            "--jpath_pos",
            "positions",
            "--jpath_x",
            "",
            "--jpath_y",
            "",
            "--custom_map_tile",
            'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png,DarkMatter no labels,<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
            "--weight_route",
            "1.5",
            "--weight_points",
            "2",
            "--swap",
        ],
        os.path.join(OUTPUT_DIR, "paris-route-indexed.plot.png"),
        os.path.join(OUTPUT_DIR, "paris-route-indexed.plot.html"),
        os.path.join(OUTPUT_DIR, "paris-route-indexed.html"),
        os.path.join(DATA_DIR, "paris-route-indexed.json.golden"),
        os.path.join(DATA_DIR, "paris-route-indexed.plot.png.golden"),
        os.path.join(DATA_DIR, "paris-route-indexed.plot.html.golden"),
        os.path.join(DATA_DIR, "paris-route-indexed.map.html.golden"),
    )
    _run_map_test(test)


def test_map_plot_cli_geojson():
    test = GeoJSONTest(
        "geojson",
        [
            "geojson",
            "--input_geojson",
            os.path.join(DATA_DIR, "geojson-data.json"),
        ],
        os.path.join(OUTPUT_DIR, "geojson-data.json.map.html"),
        os.path.join(DATA_DIR, "geojson-data.json.golden"),
        os.path.join(DATA_DIR, "geojson-data.json.map.html.golden"),
    )
    _run_geojson_test(test)


def test_progression_plot_cli_fleet_cloud_comparison():
    test = ProgressionTest(
        "fleet-cloud-comparison",
        [
            "progression",
            "--input_progression",
            "0.7.3," + os.path.join(DATA_DIR, "fleet-cloud-all-0.7.3.json"),
            "0.8," + os.path.join(DATA_DIR, "fleet-cloud-all-0.8.json"),
            "--title",
            "Fleet cloud comparison",
        ],
        os.path.join(OUTPUT_DIR, "fleet-cloud-comparison.png"),
        os.path.join(OUTPUT_DIR, "fleet-cloud-comparison.html"),
        os.path.join(DATA_DIR, "fleet-cloud-comparison.golden"),
        os.path.join(DATA_DIR, "fleet-cloud-comparison.png.golden"),
        os.path.join(DATA_DIR, "fleet-cloud-comparison.html.golden"),
    )
    _run_progression_test(test)


if __name__ == "__main__":
    _prepare_tests()
    test_map_plot_cli_paris_route()
    test_map_plot_cli_paris_cluster()
    test_map_plot_cli_paris_point()
    test_map_plot_cli_paris_route_indexed()
    test_map_plot_cli_geojson()
    test_progression_plot_cli_fleet_cloud_comparison()
    print("Everything passed")
