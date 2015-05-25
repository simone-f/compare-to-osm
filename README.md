# compare-to-osm

License: GPL v3

This script creates GeoJSON files by comparing the geometries of highways from OSM and open data released as shapefile.
Results are displayed on a map in `html/index.html`.

The script ignores footway, cycleways and pedestrian highways.

## Dependencies
Data:

* A shapefile with highways (WGS84) from the local council (the geometries must be Linestring).
* A shapefile with the boundaries of the local council.

Programs:

* wget
* spatialite_tool
* ogr2ogr
* topojson

In Ubuntu, install with:

        sudo apt-get install spatialite-bin gdal-bin nodejs
        sudo npm install -g topojson

## Usage
* The first time, write into `config.cfg` file: `name`, `admin_level` and paths to local council's highways and boundaries shapefiles.
* Execute `pyhton ./script.py` to create or update the data file: `html/ways.GeoJSON`.
* (Optional) Update in `html/info.js` the text shown on the web page.
* Open `index.html` in a browser.