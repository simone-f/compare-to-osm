This README describes a compare-to-osm project file.

You can create a new project by creating a directory and a project file (e.g. `projects/myproject/project.json`) with the following content.

```
{

    # OPTIONAL web page title (default: "Compare to OSM")
    "title": "Compare to OSM",

    # OPTIONAL map center's latitude (default: last task center's coordinates)
    "map_lat": "41.8921",

    # OPTIONAL map center's longitude (default: last task center's coordinates)
    "map_lon": "12.4832",

    # OPTIONAL map zoom (default: 5)
    "map_zoom": "6",

    "tasks": [

        # Add a task for each comparison you want to do

        {
            # MANDATORY name, without empty spaces, to identify the task
            "name": "Rimini",

            # MANDATORY comparison type: a name of a module in 'comparators/'.
            # To create new comparators just add their module in 'comparators/'.
            "comparator": "highwaysgeometryspatialite",

            # MANDATORY if the comparator uses PostGIS
            "postgis_user": "simone",

            "postgis_password": "#######",

            "data": {
                     "open_data": {
                            # MANDATORY shapefile with open data.
                            # Path can be absolute or relative to compare-to-osm/projects/project_directory/data/open_data
                            "shapefile": "Rimini/archiWGS84.shp",

                            # MANDATORY if comparator == highwaysgeometry. Shapefile with boundaries of the open data.
                            # Path can be absolute or relative to compare-to-osm/projects/project_directory/data/open_data
                            "boundaries_file": "Rimini/boundaries_rn.shp"
                        },

                    # MANDATORY if you want to download OSM data automatically from Overpass API, with --download_osm option.
                    "osm_data": {
                            "overpass_query": "data=area[name=\"Rimini\"][admin_level=8];way(area)[\"highway\"][\"highway\"!~\"footway\"][\"highway\"!~\"cycleway\"];(._;>;);out meta;"
                        }
                    },

            # OPTIONAL
            "output": {
                    # Type of output:
                    # "vector" (default) for GeoJSON layers on Leaflet
                    # "raster" for PNG tiles layers on Leaflet
                    "type": "vector",

                    # Min zoom for tiles rendering (default: 5)
                    "min_zoom": 5,

                    # Max zoom for tiles rendering (default: 11)
                    "max_zoom": 15
                    },

            # OPTIONAL information that may be used in a custom Jinja2 template and shown the web page
            "info": {
                    "data_license": "<a href=\"http://creativecommons.org/publicdomain/zero/1.0/\" target=\"_blank\">CC0</a>",
                    "data_link": "<a href=\"http://www.comune.rimini.it/filo_diretto/open_data/-toponomastica/\" target=\"_blank\">Comune di Rimini</a>",
                    "data_time": ""
                    }
        },

        {
            # Second task
            "name": "Verona",
            "comparator": "highwaysgeometrypostgis",
            ...
        }
        ]
}
```
