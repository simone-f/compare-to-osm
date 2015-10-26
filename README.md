# compare-to-osm

This program compares the geometries of highways in OSM with those in one or more shapefiles.

It generates GeoJSON files and Shapefiles with highways missing in OSM and in the open data and shows the results on a Leaflet map, as Topojson files or PNG tiles.

[Here](https://dl.dropboxusercontent.com/u/41550819/OSM/compare-to-osm/index.html) is an ouput example with open data from Italy.

## Dependencies
Programs:

* wget
* ogr2ogr
* topojson
* mapnik
* jinja2

In Ubuntu, install everything with:

        sudo apt-get install gdal-bin nodejs python-mapnik python-jinja2
        sudo npm install -g topojson

You will also need Spatialite or PostGIS, depending on the comparator you use (see section below): `sudo apt-get install spatialite-bin` or `sudo apt-get install postgis postgresql-contrib osmosis`.

Data:

* a WGS84 shapefile with open data regarding highways from the the zone of your interest, e.g. a local council
* a Shapefile with the boundaries of the zone (if using `highwaysgeometryspatialite` comparator).

## Usage
### Configuration
Create a new project directory into `projects` and write a `project.json` file with the configuration. See `projects/README.md` for more informations.<br>Optionally, write a Jinja2 template to generate a custom web page.

### Execution
Show the list of options:

        pyhton ./compare-to-osm.py -h

Analyse the data and create the output files:

        pyhton ./compare-to-osm.py projects/myproject/project.json --analyse

Read analysis' output files and create the web page and GeoJSON or PNG tiles used by the map:

        pyhton ./compare-to-osm.py projects/myproject/project.json --update_map

Open `projects/myproject/html/index.html` in a web browser to see the results.

### Demo
Run `python ./compare-to-osm.py projects/projectdemo/project.json --analyse --update_map` and  open `projects/projectdemo/html/index.html` in a web browser.

### Comparators
The comparison is performed by one of the modules in `comparators` directory:

* `comparators/highwaysgeometryspatialite.py` needs spatialite-bin package and supports Linestring shapefiles.
* `comparators/highwaysgeometrypostgis.py` needs PostGIS and osmosis and supports Multilinestring shapefiles.

You may add new modules to compare different OSM object (e.g. rivers). Just add in the project file the name of the comparator you want to use (e.g. `"comparator": "highwaysgeometryspatialite"`).

### OpenStreetMap data
By default the program downloads the OSM data from Overpass API, ignoring footways, cycleways and pedestrian highways.

For big areas you may prefer to create the OSM file manually. E.g.:

       osmconvert Italy.pbf -B=Verona.poly -o=Verona.o5m
       
       osmfilter --keep=  --keep=highway Verona.o5m -o=projects/myproject/data/OSM/Verona_highways.osm`

where Verona_highways is the task name, and then use the options `--analyse --offline` to avoid the download.

## Development
License: GPL v3

Author: Simone F.

Coding conventions: flake8