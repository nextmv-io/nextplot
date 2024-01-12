import json
import sys

import jsonpath_ng

# ==================== This file contains testing code (mode: 'test')


# ==================== Test mode argument definition


def arguments(parser):
    """
    Defines arguments specific to testing.
    """
    parser.add_argument(
        "--input",
        type=str,
        nargs="?",
        default="",
        help="path to the file to test",
    )
    parser.add_argument(
        "--jpath",
        type=str,
        nargs="?",
        default="",
        required=True,
        help="JSON path to test (XPATH like,"
        + " see https://goessner.net/articles/JsonPath/,"
        + ' example: "state.clusters[*].points")',
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="plots some statistics about tested matching",
    )


# ==================== Test specific functionality


def test_filter(
    input: str,
    jpath: str,
    stats: bool,
):
    """
    Simply filters a file using the given path and prints the result.
    """
    # Load json data and extract information
    content = ""
    if len(input) > 0:
        with open(input) as jsonFile:
            content = jsonFile.read()
    else:
        content = "".join(sys.stdin.readlines())
    data = json.loads(content)
    try:
        expression = jsonpath_ng.parse(jpath)
    except Exception:
        print(f'error in path syntax: "{jpath}"')
        return
    # Find and print all matching results
    matches = 0
    for match in expression.find(data):
        print(match.value)
        matches += 1
    if stats:
        print("Statistics:")
        print(f"{matches} matches")
