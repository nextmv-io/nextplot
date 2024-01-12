# Gallery

The gallery contains a list of plots using the provided sample files. Try to
execute the listed calls from the [example](example) directory.

---

This route plot uses sorting to get a rainbow like result. Since the coordinates
are not nested but a list of points, the `--jpath_x` and `--jpath_y` flags are
reset to `""`.

```bash
nextplot route \
        --input_route ../data/dortmund-route.json \
        --jpath_route "state.drivers[*].geometry.coordinates" \
        --jpath_x "" \
        --jpath_y "" \
        --output_map dortmund-route.map.html \
        --output_plot dortmund-route.plot.html \
        --output_image dortmund-route.plot.png \
        --sort_color
```

Image result:

![dortmund-route.png](https://nextmv-io.github.io/nextplot/gallery/dortmund-route/dortmund-route.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/dortmund-route)):

![dortmund-route.html.png](https://nextmv-io.github.io/nextplot/gallery/dortmund-route/dortmund-route.html.png)

---

This cluster plot has a separate file containing the coordinates while the main
file contains sets of indices referring to them as clusters. Furthermore, it
uses sorting to get a rainbow like result. Since the coordinates are not nested
but a list of points, the `--jpath_x` and `--jpath_y` flags are reset to `""`.

```bash
nextplot cluster \
        --input_cluster ../data/dortmund-cluster.json \
        --jpath_cluster "state.clusters[*].points" \
        --input_pos ../data/dortmund-point.json \
        --jpath_pos "points" \
        --jpath_x "" \
        --jpath_y "" \
        --output_map dortmund-cluster.map.html \
        --output_plot dortmund-cluster.plot.html \
        --output_image dortmund-cluster.plot.png \
        --sort_color
```

Image result:

![dortmund-cluster.png](https://nextmv-io.github.io/nextplot/gallery/dortmund-cluster/dortmund-cluster.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/dortmund-cluster)):

![dortmund-cluster.html.png](https://nextmv-io.github.io/nextplot/gallery/dortmund-cluster/dortmund-cluster.html.png)

---

This point plot uses sorting to get a rainbow like result.

```bash
nextplot point \
        --input_point ../data/dortmund-route.json \
        --jpath_point "state.drivers[*].geometry.coordinates" \
        --jpath_x "" \
        --jpath_y "" \
        --output_map dortmund-point.map.html \
        --output_plot dortmund-point.plot.html \
        --output_image dortmund-point.plot.png \
        --no_points \
        --sort_color
```

Image result:

![dortmund-point.png](https://nextmv-io.github.io/nextplot/gallery/dortmund-point/dortmund-point.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/dortmund-point)):

![dortmund-point.html.png](https://nextmv-io.github.io/nextplot/gallery/dortmund-point/dortmund-point.html.png)

---

This route plot uses custom x, y paths, omits the depot location at start & end,
quadruples the width of the route lines and adds a custom tile layer.

```bash
nextplot route \
        --input_route ../data/paris-route.json \
        --jpath_route "state.tours[*].route" \
        --jpath_x "location[1]" \
        --jpath_y "location[0]" \
        --output_map paris-route.map.html \
        --output_plot paris-route.plot.html \
        --output_image paris-route.plot.png \
        --omit_start \
        --omit_end \
        --custom_map_tile 'https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png,DarkMatter no labels,<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>' \
        --weight_route 2.5 \
        --weight_points 4
```

Image result:

![paris-route.png](https://nextmv-io.github.io/nextplot/gallery/paris-route/paris-route.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/paris-route)):

![paris-route.html.png](https://nextmv-io.github.io/nextplot/gallery/paris-route/paris-route.html.png)

---

This plot uses routingkit and therefore needs OSM information. Download a
suitable region file via:

```bash
wget -N http://download.geofabrik.de/north-america/us/texas-latest.osm.pbf
```

This route plot uses routingkit for plotting road paths. Furthermore, unassigned
points are plotted in addition to the route stops.

```bash
nextplot route \
        --input_route ../data/fleet-cloud.json \
        --jpath_route "state.vehicles[*].route" \
        --jpath_unassigned "state.unassigned" \
        --output_map fleet-cloud.map.html \
        --output_plot fleet-cloud.plot.html \
        --output_image fleet-cloud.plot.png \
        --rk_osm "texas-latest.osm.pbf"
```

Image result:

![fleet-cloud.png](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud/fleet-cloud.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud)):

![fleet-cloud.html.png](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud/fleet-cloud.html.png)

---

This plot uses routingkit like the one above. Download a suitable region file
via:

```bash
wget -N https://download.geofabrik.de/europe/france/ile-de-france-latest.osm.pbf
```

In addition to what the plots above introduced, this one adds start and end
markers for the routes. Since the routes in the `paris-route.json` file start at
a mutual "depot", we are omitting the start and end to get individual markers.

```bash
nextplot route \
        --input_route ../data/paris-route.json \
        --jpath_route "state.tours[*].route" \
        --jpath_x "location[1]" \
        --jpath_y "location[0]" \
        --omit_start \
        --omit_end \
        --output_map paris-markers.map.html \
        --output_plot paris-markers.plot.html \
        --output_image paris-markers.plot.png \
        --start_end_markers \
        --rk_osm "ile-de-france-latest.osm.pbf"
```

Image result:

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/paris-markers)):

![fleet-cloud.html.png](https://nextmv-io.github.io/nextplot/gallery/paris-markers/paris-markers.html.png)

---

This plot adds animations as an indication for route direction to previous plot.
Hence, don't forget to download a suitable region file (see above).

```bash
nextplot route \
        --input_route ../data/fleet-cloud.json \
        --jpath_route "state.vehicles[*].route" \
        --jpath_unassigned "state.unassigned" \
        --output_map fleet-cloud.map.html \
        --output_plot fleet-cloud.plot.html \
        --output_image fleet-cloud.plot.png \
        --rk_osm "texas-latest.osm.pbf" \
        --route_direction animation
```

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud/fleet-cloud-animation.html)):

![fleet-cloud-animation.html.gif](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud/fleet-cloud-animation.gif)

---

Following command plots the points of the Paris file while maintaining their
grouping (as indicated by the jpath - grouped by route).

```bash
nextplot point \
        --input_point ../data/paris-route.json \
        --jpath_point state[*].tours[*].route \
        --jpath_x location[1] \
        --jpath_y location[0] \
        --output_map paris-point-grouped.map.html \
        --output_plot paris-point-grouped.plot.html \
        --output_image paris-point-grouped.plot.png \
        --no_points \
        --weight_points 4
```

Image result:

![paris-point-grouped.png](https://nextmv-io.github.io/nextplot/gallery/paris-point-grouped/paris-point-grouped.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/paris-point-grouped)):

![paris-point-grouped.html.png](https://nextmv-io.github.io/nextplot/gallery/paris-point-grouped/paris-point-grouped.html.png)

---

Following command plots the same points ignoring their grouping.

```bash
nextplot point \
        --input_point ../data/paris-route.json \
        --jpath_point state[*].tours[*].route[*].location \
        --output_map paris-point-ungrouped.map.html \
        --output_plot paris-point-ungrouped.plot.html \
        --output_image paris-point-ungrouped.plot.png \
        --weight_points 4 \
        --swap \
        --no_points \
        --sort_color
```

Image result:

![paris-point-ungrouped.png](https://nextmv-io.github.io/nextplot/gallery/paris-point-ungrouped/paris-point-ungrouped.png)

Map result ([link](https://nextmv-io.github.io/nextplot/gallery/paris-point-ungrouped)):

![paris-point-ungrouped.html.png](https://nextmv-io.github.io/nextplot/gallery/paris-point-ungrouped/paris-point-ungrouped.html.png)

---

Following command plots the solution value progression of two hop runs with all
solutions returned. The default jpaths adhere to hop's all solutions structure.
However, if necessary `jpath_solution`, `jpath_value` & `jpath_elapsed` can be
used to customize the path to the relevant information. For additional
information please refer to `nextplot progression --help`.

```bash
nextplot progression \
        --input_progression 0.7.3,../data/fleet-cloud-all-0.7.3.json 0.8,../data/fleet-cloud-all-0.8.json \
        --output_png fleet-cloud-comparison.png \
        --output_html fleet-cloud-comparison.html \
        --title "Fleet cloud comparison"
```

Interactive result: [link](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud-comparison)

Image result:

![fleet-cloud-comparison.png](https://nextmv-io.github.io/nextplot/gallery/fleet-cloud-comparison/fleet-cloud-comparison.png)
