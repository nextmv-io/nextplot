# nextplot

[![pypi_version](https://img.shields.io/pypi/v/nextplot?label=pypi)](https://pypi.org/project/nextplot)[![build](https://github.com/nextmv-io/nextplot/actions/workflows/build.yml/badge.svg)](https://github.com/nextmv-io/nextplot/actions/workflows/build.yml)

Tools for plotting routes and clusters from JSON

## Installation

```bash
pip install nextplot
```

## Usage

If the installation succeeded, you should be able to invoke the following:

```bash
nextplot --help
```

Furthermore, use the __route__ and __cluster__ commands for the respective
plotting type. Find an overview of the arguments for the specific mode by
invoking `nextplot route --help` and `nextplot cluster --help`.

Above shows some information about how to use the script. Below presents some
further information for running the script using route plotting as an example.

There are basically two options of running the script. Either feed the JSON to
STDIN of the script like so:

```bash
cat examples/data/kyoto-route.json | nextplot route \
  --jpath_route "vehicles[*].route" \
  --jpath_x "position.lon" \
  --jpath_y "position.lat"
```

Or supply a path to the `.json` file like so:

```bash
nextplot route \
  --input_route examples/data/kyoto-route.json \
  --jpath_route "vehicles[*].route" \
  --jpath_x "position.lon" \
  --jpath_y "position.lat"
```

Both approaches will create a `.png` plot image and if possible (valid lon/lat
coordinates given) an interactive `.html` plot file. The filenames will be
`plot.[png,html]` for the first option, based on the input filename for the
second option and customized ones if `--output_image` and/or `--output_map` are
specified.

The input file is expected to have some JSON array of positions which can be
addressed using the notation described here:
[https://goessner.net/articles/JsonPath/](https://goessner.net/articles/JsonPath/).
The path to the positions can be modified via the `--jpath_route` parameter.
For example, if your input file stores the locations like shown below, the path
`"vehicles[*].route"` will extract them. As you can see, the
path first goes through the `vehicles`. Next, `[*]` denotes that a list of
vehicles is expected, which in turn results in a list of routes. Finally,
`.route` points to the exact location of the route object per vehicle. The
`--jpath_x` and `--jpath_y` parameters are used to extract the longitude and
latitude values from the stop objects at `position.lon` and `position.lat`.

```jsonc
{
    "vehicles": [
        // ...
        {
            "id": "v1",
            "route": [
                {
                    "id": "v1-start",
                    "position": { "lon": 135.73723, "lat": 35.04381 }
                },
                {
                    "id": "Kinkaku-ji",
                    "position": { "lon": 135.728898, "lat": 35.039705 }
                },
                {
                    "id": "Nijō Castle",
                    "position": { "lon": 135.748134, "lat": 35.014239 }
                },
                {
                    "id": "Arashiyama Bamboo Forest",
                    "position": { "lon": 135.672009, "lat": 35.017209 }
                }
            ]
        }
        // ...
    ]
}
```

### Further examples

A more detailed introduction and a plot gallery can be found [here](examples/README.md).

## Preview

Preview _route_ plot (screenshot of .html-file, cartodbdark_matter selected):

![sample-popup](https://nextmv-io.github.io/nextplot/plots/sneak/example-popup.png)

Another preview _route_ plot (screenshot of .html-file, cartodbdark_matter selected):

![sample-plot-html](https://nextmv-io.github.io/nextplot/plots/sneak/example-route-html.png)

Preview _cluster_ plot (screenshot of .html-file, cartodbdark_matter selected):

![sample-plot-html](https://nextmv-io.github.io/nextplot/plots/sneak/example-cluster-html.png)

## Auto-completion

Auto-completion (using _tab_) is supported via `argcomplete`. To enable it, install the package:

```bash
pip install argcomplete
```

Then, add the following line to your `~/.bashrc`:

```bash
eval "$(register-python-argcomplete nextplot)"
```

## Tests

Tests are located in `tests/` and can be run via `python -m pytest`. Update test
expectations (golden files) by running `UPDATE=1 python test_cli.py` from the
test directory. Tests require specific versions of the dependencies to be
installed. These can be installed via `pip install -r requirements-dev.txt`.
It is recommended to update the expectations in a docker container to avoid
messing up local dependencies. This can be done by running the following
commands:

```bash
docker run --rm -it -v $(pwd):/app -w /app python:3.11 bash -c "pip install -r requirements-dev.txt && cd tests && UPDATE=1 python test_cli.py"
```
