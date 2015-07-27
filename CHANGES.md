v0.4
----

* Refactorization:
    * split the main file, now called compare-to-osm.py, into several files and classes for easier maintenance
    * create Task class, representing a comparison task
    * create Comparator class, collecting the methods that analyse the data, so that it will possible to add different type of comparisons.

* Add options so that it's possible to separately analyse the data or update the map's data:
    * -a, --analyse; download OSM data, compare with open data and produce output files
    * -m, --update_map; read analysis'output files and update map's data (e.g. render tiles)

* Other options:
    * --offline, do not download data from OSM; use the OSM data already present.<br>Useful for testing or when an area is too big to be downloaded with Overpass API and the user wants to use an OSM file he or she created, for example with osmfilter
    * --tasks TASKNAME [TASKNAME ...]; execute -a or -m only for the specified task.<br>Useful for when the user wants to update a task (the comparison of a specific zone), without having to run all the other tasks too (analyse the data of all the other zones)
    * -p, --print_tasks_configuration; print tasks'configuration and exit

* New output type: show results as PNG tiles rendered with Mapnik

* Show on the web page the dates in which the comparisons have been made (update time)

Other changes:

* Convert tasks configuration file from ConfigParser to JSON (tasks.json)
* Convert html/data/zones_info.js to JSON (html/data/tasks_info.json)
* Do not create transparent tiles and speed up rendering a little
* Improve README.md and add documentation
* Add .gitignore
* Comply to PEP8 conventions (flake8)
* Clean up code

v0.3
----
* Support multiple zones