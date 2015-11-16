#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright Simone F. <groppo8@gmail.com>
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import os
import sys
import time
import argparse
from project import Project


class App():
    def __init__(self):

        # Options
        text = ("The program compares the geometries of highways in OSM with"
                " those in one or more shapefiles. It generates GeoJSON and"
                " shapefiles with highways missing in OSM and in the open"
                " data. The results are shown on a leaflet map as topojson"
                " or PNG tiles.")
        parser = argparse.ArgumentParser(description=text)

        parser.add_argument("project_file",
                            help="a file describing the project"
                                 " (see README.md)")

        parser.add_argument("-p", "--print_config",
                            help="print the project's configuration and exit",
                            action="store_true")

        parser.add_argument("--download_osm",
                            help="download OSM data through Overpass API, by "
                                 "using the zone's name and admin_level from "
                                 "the project file",
                            action="store_true")

        parser.add_argument("-a", "--analyse",
                            help="compare the OSM data with open data"
                                 " and produce output files",
                            action="store_true")

        parser.add_argument("-w", "--create_web_page",
                            help="read analysis' output files, create map data"
                                 " (GeoJSON or PNG tiles) and create the web"
                                 " page",
                            action="store_true")

        parser.add_argument("--create_web_page_no_data",
                            help="create the web page without updating the map"
                                 " data. Useful when you just want to test "
                                 "some changes to the web page's Jinja2 "
                                 "template without having to wait for mapnik "
                                 "to render the map tiles",
                            action="store_true")

        parser.add_argument("-t", "--tasks",
                            help="execute -a, -w or --create_web_page_no_data "
                                 "only with the tasks whose name is in this "
                                 "list, ignoring the other project tasks. "
                                 "Useful when you want to update one task's "
                                 "result without losing the data of the "
                                 "others",
                            nargs="+",
                            metavar=("TASKNAME"))

        start = time.time()

        self.args = parser.parse_args()

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        self.directory = os.path.dirname(os.path.abspath(__file__))
        os.chdir(self.directory)

        if not os.path.isfile(self.args.project_file):
            print "* Error: project file not found."
            sys.exit(1)

        # Build the project
        project = Project(self)

        project.print_configuration()
        if self.args.print_config:
            sys.exit()

        # Analyse
        if self.args.analyse:
            for task in project.tasks:
                print "\n= Task: {0} =".format(task.name)
                # Download OSM data, compare with open data
                # and produce output files
                task.compare()

        # Create the web page
        if self.args.create_web_page or self.args.create_web_page_no_data:
            if self.args.create_web_page:
                project.update_map_data()
            project.create_web_page()

        # Update the project file with comparisons' results
        project.update_output_file()

        end = time.time()
        print "\nExecution time: ", end - start, "seconds."

if __name__ == "__main__":
    app = App()
