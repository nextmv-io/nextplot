# Examples

More detailed examples and descriptions are given below. Further examples can be
found in the [gallery](gallery/README.md) section.

## General steps

When plotting clusters or routes from JSON files we need to first identify where
the necessary information is stored within the JSON structure. For this, we can
use the `test` mode of `nextplot`.

```bash
nextplot test --help
```

Let's look at `data/hamburg-route.json`. The relevant data (routes as list of
points) is stored as follows.

```json
{
  "state": {
    "drivers": [
      {
        "geometry": {
          "coordinates": [
            [7.445303531392447, 51.49135302624266],
            [7.447852883113915, 51.48998800466363],
            [7.447056459334395, 51.48748598974504],
            [7.446920673259998, 51.48822589325628],
            [7.446382930568115, 51.48952134441981],
            [7.445632420473728, 51.48962184633942]
          ]
        }
      }
    ]
  }
}
```

Hence, we should be able to extract the routes with the following JSON path:
`state.drivers[*].geometry.coordinates[*]`. Let's test it by invoking the `test`
mode. Adding the `--stats` flag will give us the number of routes found.

```bash
nextplot test \
    --input data/hamburg-route.json \
    --jpath "state.drivers[*].geometry.coordinates" \
    --stats
```

The result should be all the expected lists of routes. For the given example
`271 matches` should be returned.

## Route plotting

Now let's plot some routes. We will be using `data/dortmund-route.json` as
sample input data. The file contains the same structure as the Hamburg example
above. Hence, we can use the same `jpath`. We can get our plot with this:

```bash
nextplot route \
    --input_route data/dortmund-route.json \
    --jpath_route "state.drivers[*].geometry.coordinates"
```

The output at stdout should be:

```txt
Route stats
Route count: 271
Route stops (max): 29
Route stops (min): 1
Route stops (avg): 21.365313653136532
Route length (max): 8.344633870323412
Route length (min): 0
Route length (avg): 2.1533391639934014
Plotting image to data/dortmund-route.json.png
Plotting map to data/dortmund-route.json.html
```

The output contains some statistics and shows that the plot files have been
written to `data/<original_name>.png` & `data/<original_name>.html`. At default,
the plots are written to the same directory as the input file using its name.
This can be changed via the `--output_image` & `--output_map` parameters.

The map plot should look like [this](https://nextmv-io.github.io/nextplot/plots/dortmund-route):
![dortmund-route.json.html.png](https://nextmv-io.github.io/nextplot/plots/dortmund-route/dortmund-route.json.html.png)

## Route plotting with routingkit support

Next, we're gonna plot routes using the road network. We do this with the
support of [go-routingkit](go-routingkit).

### Pre-requisites

1. Install [go-routingkit](go-routingkit) standalone:

    ```bash
    go install github.com/nextmv-io/go-routingkit/cmd/routingkit@latest
    ```

2. Download suitable osm file of containing all locations (e.g. Kansai region
   for Kyōto example):

    ```bash
    wget -N http://download.geofabrik.de/asia/japan/kansai-latest.osm.pbf
    ```

### Plot route paths

The command is similar to the one above, but specifies some extra options (refer
to the full list [below](#additional-information)). The `rk_osm` option
activates routingkit driven plotting.

```bash
nextplot route \
        --input_route data/kyoto-route.json \
        --jpath_route "vehicles[*].route" \
        --jpath_x "position.lon" \
        --jpath_y "position.lat" \
        --output_map kyoto-route.html \
        --output_image kyoto-route.png \
        --rk_osm kansai-latest.osm.pbf
```

The map plot should look like [this](https://nextmv-io.github.io/nextplot/plots/kyoto-route):
![kyoto-route.json.html.png](https://nextmv-io.github.io/nextplot/plots/kyoto-route/kyoto-route.json.html.png)

## Cluster plotting

Now let's move on to plotting some clusters. We will use
`data/rome-cluster.json` as an example. Unfortunately, the file does not contain
the positions for the points itself. It does contain the indices of the points
to plot though. Looking at the file we know we can extract them via
`state.clusters[*].points`. (note: some data was removed from the preview below)

```json
{
  "state": {
    "clusters": [
      {
        "centroid": [-88.13468293225804, 41.81753548064515],
        "points": [
          51,
          65,
          148
        ]
      }
    ]
  }
}
```

Now we need the actual positions of the points at these indices. We can get
them from the `data/rome-point.json` file. The JSON structure is very simple. We
can find the list of points at `points`. The assumption here is that the indices
of the file above are in line with the order of points in this file.

```json
{
  "depot": 0,
  "neighbors": 500,
  "points": [
    [12.450535369539924, 41.82296871624285],
    [12.244249981200547, 41.81779915932505]
  ]
}
```

Since we have two files, we also have separate _inputs_ and _jpaths_. There are
`--input_pos` & `--jpath_pos` available for the position information and
`--input_cluster` & `--jpath_cluster` for the cluster information.

This is all information we need. The following command will give us the plots:

```bash
nextplot cluster \
    --input_cluster data/rome-cluster.json \
    --jpath_cluster "state.clusters[*].points" \
    --input_pos data/rome-point.json \
    --jpath_pos "points"
```

Command output:

```txt
Cluster stats
Total points: 1622
Cluster count: 57
Cluster size (max): 35
Cluster size (min): 11
Cluster size (avg): 28.45614035087719
Cluster size (variance): 26.28316405047707
Cluster diameter (max): 16.17086445602463
Cluster diameter (min): 1.0249801072810207
Cluster diameter (avg): 6.762504023482336
Sum of max distances from centroid: 226.9416857406218
Max distance from centroid: 11.637893312799743
Sum of distances from centroid: 2807.765322949338
Sum of squares from centroid: 7723.523174962022
Bad assignments: 139
Plotting image to data/rome-cluster.json.png
Plotting map to data/rome-cluster.json.html
```

We again get some statistics about our clusters and the plots are also available
at the data file location.

The map plot should look like [this](https://nextmv-io.github.io/nextplot/plots/rome-cluster):
![rome-cluster.json.html.png](https://nextmv-io.github.io/nextplot/plots/rome-cluster/rome-cluster.json.html.png)

## Additional information

Above descriptions should cover most route/cluster plotting needs. However,
there are more options for steering the resulting plots towards your needs or
handle certain data formats. Find an outline of these options here:

- `--coords [{euclidean,haversine,auto}]`:
  There are different modes (`euclidean`, `haversine` & `auto`) how coordinates
  are processed. These can be selected via `--coords`.
  - `euclidean` uses euclidean distance for measuring route characteristics and
    deactivates html-map plotting.
  - `haversine` uses haversine distance for measuring route characteristics and
    activates html-map plotting. In this mode coordinates are required to be
    valid lon/lat. I.e., x, y need to be from the ranges [-180, 180], [-90, 90]
  - `auto` results in haversine, if coordinates are valid lon/lat. Otherwise,
    euclidean will be used.
- `--omit_start` & `--omit_end`:
  If the input file contains routes starting and/or ending at a depot, many
  routes will overlap and long lines will be shown. To avoid these confusing
  plots `--omit_start` & `--omit_end` can be activated. These will simply cause
  the first and/or last stop of a route to be omitted.
- `--swap`:
  `nextplot` expects positions to be given in (x,y) / (lon,lat) manner. If the
  positions are in the opposite order, they can be reversed by using the
  `--swap` flag.
- `--sort_color`:
  Routes and clusters are all colored using the same saturation & brightness.
  The hue value is uniformly distributed among them and set in the same order as
  the routes/clusters appear. For a rainbow like effect colors may be sorted
  clockwise by the route/cluster centroids using the `--sort_color` flag.
- `--colors`:
  Specifies the color profile. Can simply be a preset like `cloud` and
  `rainbow`, but there are also customization modes:
  - `gradient`: performs a color gradient from one color to another, e.g.,
    `gradient,419AA8,092940` (it is possible to define multiple colors like
    this: `gradient,FFFFFF,419AA8,092940,333333`)
  - `rainbow`: performs a rainbow from first hue-value to second using the
    saturation and value settings, e.g., `rainbow,140,180,0.6,0.7`
- `--custom_map_tile`:
  When plotting interactive maps `nextplot` uses the default OSM map tiles
  (more details) and CartoDB Dark Matter (black to focus colored
  routes/cluster). Additional custom map tiles can be added via
  `--custom_map_tile [CUSTOM_MAP_TILE]`. An overview can be found here:
  [folium-tiles][folium-tiles].
  - Custom tile providers can even be used by supplying them in the format
    `"<tile-url>,<layer-name>,<attribution>"`.
    Example:

      ```bash
      --custom_map_tile "https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png,DarkMatter no labels,OpenStreetMap authors"
      ```

    (an overview of custom tile providers can be found [here][custom-layers])
- `--jpath_x` & `--jpath_y`:
  `nextplot` expects to find arrays of points or indices, if a path like
  `state.drivers[*].geometry.coordinates` is given. I.e., either
  `[[7.44, 51.49], [7.44, 51.48], ...]` or `[[24, 400, ...]]` are expected.
  However, sometimes route/cluster objects are more complex. For example, a list
  of named lon/lat like the following, may be given at the path above:
  `{ "lon": 7.44, "lat": 51.49 }` (instead of `[7.44, 51.49]`). In order to
  extract the positions from the nested structure we use `--jpath_x lon` &
  `--jpath_y lat`.
- `--jpath_unassigned` (route only):
  Path to the array of unassigned points. If provided and points are found, they
  will be plot separately.
- `--jpath_unassigned_x` & `--jpath_unassigned_y` (route only):
  Same as `--jpath_x` & `--jpath_y`, but for the unassigned points.
- `--route_direction` (route only):
  Specifies how to indicate route direction. Can be one of `none` (no route
  direction indication), `arrow` (arrows drawn onto the route) and `animation`
  (animated route flow). By default, route directions are not annotated.
- `--route_animation_color` (route only):
  Specifies the background color for the two color route direction animation.
  Colors can be provided as hex strings without the leading `#`, e.g., `000000`.
  The default animation background color is white (`FFFFFF`).
- `--weight_route <factor>` (route only):
  The thickness of the routes can be controlled by the `weight_route` factor.
  For example, a factor of 2 doubles the thickness.
- `--no_points` (cluster & route):
  The `--no_points` flag may be used to skip plotting the actual points in
  addition to the clusters / routes.
- `--weight_points` (cluster & route):
  The size of the individual points is controlled via the `weight_points`
  factor. For example, a factor of 2 doubles the point diameter.
- `--start_end_markers` (route only):
  The `--start_end_markers` flag may be used to mark the first and last stops of
  the routes.
- `--stats_file <path-to-file>`:
  If provided, statistics will be written to the given file in addition to
  stdout.
- `rk_bin` (route only):
  Path to the [go-routingkit][go-rk] standalone binary. Alternatively,
  `routingkit` command will be used at default (requires go-routingkit
  [installation][go-rk-install]).
- `rk_osm` (route only):
  Path to the OpenStreetMap data file to be used for routing. All points must be
  contained within the region of the file. This file is mandatory when using
  routingkit. Furthermore, this switch activates road level routes, if provided.
- `rk_profile` (route only):
  Profile used to generate paths via routingkit. Can be one of _car_, _bike_ &
  _pedestrian_.
- `rk_distance` (route only):
  If given routingkit costs will be returned in distance instead of duration.

[go-rk]: https://github.com/nextmv-io/go-routingkit/tree/stable/cmd/routingkit
[go-rk-install]: https://github.com/nextmv-io/go-routingkit/tree/stable/cmd/routingkit#install
[custom-layers]: http://leaflet-extras.github.io/leaflet-providers/preview/
[folium-tiles]: https://deparkes.co.uk/2016/06/10/folium-map-tiles/
