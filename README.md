# compare-to-osm

This program compares the geometries of highways in OSM with those in one or more shapefiles.

It generates GeoJSON and Shapefiles with highways missing in OSM and in the open data and shows the results on a Leaflet map, as Topojson files or PNG tiles.

Output example with open data from Italy:<br>[index.html
](https://dl.dropboxusercontent.com/u/41550819/OSM/compare-to-osm/index.html)

The program ignores footways, cycleways and pedestrian highways.

## Dependencies
Programs:

* wget
* spatialite_tool
* ogr2ogr
* topojson
* mapnik
* jinja2

In Ubuntu, install everything with:

        sudo apt-get install spatialite-bin gdal-bin nodejs python-mapnik python-jinja2
        sudo npm install -g topojson
        
Data:

* a WGS84 shapefile with open data regarding highways from the the zone you are interested (e.g. a local council); the geometries must be Linestring
* a Shapefile with the boundaries of the zone.

## Usage
### Configuration
* Create a file named `tasks.json`, with the list of comparisons (tasks) you want to do.<br>See `./tasks_example.json`.
* Optional: write in `./html/data/page_info.js` the text that you want to show in the box over the map in `./html/index.html`.<br>See `./html/data/page_info_example.js`.

### Execution
For the list of options, run:

        pyhton ./compare-to-osm.py -h
        
Analyse the data descripted in `tasks.json` and create or update the output files (`./data/out/*`):

        pyhton ./compare-to-osm.py --analyse
        
Read output files and generate the files used by the map (`./html/data/*`)

        pyhton ./compare-to-osm.py --update_map
        
Open `./html/index.html` in a browser to see the results.

### Demo
1. Uncompress the files in `./data/open_data/*.tar.gz`
2. rename `./tasks_example.json` as `./tasks.json` and fix the files' paths in it
3. rename `./html/data/page_info_example.js` as `./html/data/page_info.js`
4. execute `python ./compare-to-osm.py --analyse --update_map`
5. open `./html/index.html` in a browser.

### Notes
For big areas you may prefer to use a local OSM file instead of downloading the highways from Overpass API. In this case, create the highways file manually (e.g. with `osmfilter --keep=highway Verona.o5m -o=data/OSM/Verona.osm`, where Verona is the task name) and use the options `--analyse --offline`.

## Development
License: GPL v3

Author: Simone F.

Coding conventions: flake8