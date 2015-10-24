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

        parser.add_argument("-p", "--print_tasks_configuration",
                            help="print tasks'configuration and exit",
                            action="store_true")

        parser.add_argument("-a", "--analyse",
                            help="download OSM data, compare with open data"
                                 " and produce output files",
                            action="store_true")

        parser.add_argument("--offline",
                            help="do not download data from OSM;"
                                 " use the data downloaded in previous run",
                            action="store_true")

        parser.add_argument("-m", "--update_map",
                            help="read analysis'output files and"
                                 " update map's data",
                            action="store_true")

        parser.add_argument("-t", "--tasks",
                            help="consider only the tasks whose name is in"
                                 " this list and ignore the other"
                                 " in tasks.json",
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

        project.print_tasks_configuration()
        if self.args.print_tasks_configuration:
            sys.exit()

        # Analyse
        if self.args.analyse:
            for task in project.tasks:
                print "\n= Task: %s =" % task.name
                # Download OSM data, compare with open data
                # and produce output files
                task.compare()

        # Update map
        if self.args.update_map:
            for task in project.tasks:
                print "\n= Update map data: %s =" % task.name
                task.update_map_data()
            project.create_web_page()

        # Update the project file with comparisons' results
        project.update_file()

        end = time.time()
        print "\nExecution time: ", end - start, "seconds."

if __name__ == "__main__":
    app = App()
