# compare-to-osm

This program compares the geometries of highways in OSM with those in one or more shapefiles. It generates GeoJSON and Shapefiles with highways missing in OSM and in the open data. The results are shown on a Leaflet map (in `html/index.html`) as Topojson files or PNG tiles.

Output example with open data from Italy: [compare-to-osm/index.html
](https://dl.dropboxusercontent.com/u/41550819/OSM/compare-to-osm/index.html)

The program ignores footway, cycleways and pedestrian highways.

## Dependencies
Programs:

* wget
* spatialite_tool
* ogr2ogr
* topojson
* mapnik
* jinja2

In Ubuntu, install with:

        sudo apt-get install spatialite-bin gdal-bin nodejs python-mapnik python-jinja2
        sudo npm install -g topojson
        
Data:

* a WGS84 shapefile with open data regarding highways from the the zone you are interested (e.g. a local council); geometries must be Linestring
* a Shapefile with the boundaries of the zone.

## Usage
### Configuration
* Create a `config.cfg` file with one section for each zone that you want to analyse. See `./config_example.cfg` as an example.
* (Optional) Write in `./html/data/info.js` the text that you want to show in the box over the map in `./html/index.html`.

### Execution
For the list of options, run:

        pyhton ./compare-to-osm.py -h
        
Analyse the data descripted in `config.cfg` and create/update the output files (`./data/out/*`):

        pyhton ./compare-to-osm.py
        
Open `index.html` in a browser to see the results.

## Development
License: GPL v3

Author: Simone F.