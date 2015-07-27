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
from task import Task
import json


class App():
    def __init__(self):

        # Options
        text = ("The program compares the geometries of highways in OSM with"
                " those in one or more shapefiles. It generates GeoJSON and"
                " shapefiles with highways missing in OSM and in the open"
                " data. The results are shown on a leaflet map as topojson"
                " or PNG tiles.")
        parser = argparse.ArgumentParser(description=text)
        parser.add_argument("-p", "--print_tasks_configuration",
                            help="print tasks'configuration and exit",
                            action="store_true")

        parser.add_argument("-a", "--analyse",
                            help=("download OSM data, compare with open data"
                                  " and produce output files"),
                            action="store_true")

        parser.add_argument("--offline",
                            help="do not download data from OSM;"
                                 " use the data downloaded in previous run",
                            action="store_true")

        parser.add_argument("-m", "--update_map",
                            help=("read analysis'output files and"
                                  " update map's data"),
                            action="store_true")

        parser.add_argument("-t", "--tasks",
                            help=("consider only the tasks whose name is in"
                                  " this list and ignore the other"
                                  " in tasks.json"),
                            nargs="+",
                            metavar=("TASKNAME"))

        start = time.time()

        self.args = parser.parse_args()

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        # Configuration
        print "= Read tasks file ="
        self.TASKSFILE = 'tasks.json'  # written by the user
        # written by program for the web page
        self.TASKSINFOFILE = "html/data/tasks_info.json"
        self.PAGEINFOFILE = "html/data/page_info.js"

        tasks_config = self.read_config()
        tasks_names = [t["name"] for t in tasks_config["tasks"]]

        # Analyse only specified tasks (--tasks option)
        if self.args.tasks:
            for task_name in self.args.tasks:
                if task_name not in tasks_names:
                    sys.exit("\n* Error: tasks.json does not contain a task"
                             " with this name: %s" % task_name)

        self.print_tasks(tasks_config)
        if self.args.print_tasks_configuration:
            sys.exit()

        if not (self.args.analyse or self.args.update_map):
            sys.exit("\nThere is nothing left for me to tell you.")

        self.allTasks = []
        self.tasks = []
        for task_config in tasks_config["tasks"]:
            task = Task(self, task_config)
            self.allTasks.append(task)
            if not self.args.tasks or task_config["name"] in self.args.tasks:
                self.tasks.append(task)

        # Analyse
        if self.args.analyse:
            for task in self.tasks:
                print "\n= Analyse: %s =" % task.name
                # Download OSM data, compare with open data
                # and produce output files
                task.comparator.analyse()

        # Update map
        if self.args.update_map:
            for task in self.tasks:
                print "\n= Update map data: %s =" % task.name
                task.update_map_data()

        # Update JSON file with informations about the tasks, used by the map
        self.update_tasks_info_file()

        end = time.time()
        print "\nExecution time: ", end - start, "seconds."

    def read_config(self):
        if not os.path.isfile(self.TASKSFILE):
            open(self.TASKSFILE, 'a').close()
            sys.exit("\n* Please, add informations to %s. See"
                     "'tasks_example.json' as an example.") % self.TASKSFILE

        # Read tasks data
        tasks_config = self.read_json(self.TASKSFILE)
        # Read tasks info from tasks_info.json (file )used by the web page)
        if not os.path.exists(self.TASKSINFOFILE):
            tasks_info = {"tasks": []}
        else:
            tasks_info = self.read_json(self.TASKSINFOFILE)

        for task in tasks_config["tasks"]:
            # Check for missing parameters
            for param in ("name", "comparator", "data", "zone", "output"):
                if param not in task:
                    sys.exit("* Error: task %s is missing '%s' parameter." % (
                             task["name"], param))
            boundaries = task["data"]['boundaries']
            shapefile = task["data"]['shapefile']
            for (file_type, file_path) in (("Boundaries", boundaries),
                                           ("Zone", shapefile)):
                if not os.path.isfile(file_path):
                    sys.exit("* Error: %s shapefile file is missing:\n%s" % (
                             file_type, file_path))
            task["data"]['shapefile'] = shapefile[:-4]
            task["data"]['boundaries'] = boundaries[:-4]

            if 'min_zoom' not in task["output"]:
                task["output"]["min_zoom"] = 5
            else:
                task["output"]["min_zoom"] = int(task["output"]["min_zoom"])
            if 'max_zoom' not in task["output"]:
                task["output"]["max_zoom"] = 13
            else:
                task["output"]["max_zoom"] = int(task["output"]['max_zoom'])

            new_task = True
            for oldtask in tasks_info["tasks"]:
                if oldtask["name"] == task["name"]:
                    new_task = False
                    bbox = oldtask["bbox"]
                    center = oldtask["center"]
                    analysis_time = oldtask["analysis_time"]
                    break
            if new_task:
                (bbox, center, analysis_time) = ("", "", "")
            task["bbox"] = bbox
            task["center"] = center
            task["analysis_time"] = analysis_time

        # Create missing directories and files
        osmdir = os.path.join("data", "OSM")
        if not os.path.exists(osmdir):
            os.makedirs(osmdir)
        if not os.path.isfile(self.PAGEINFOFILE):
            with open(self.PAGEINFOFILE, "w") as fp:
                text = ("var title = 'Compare to OSM';"
                        "\nvar mapLat = 41.8921;"
                        "\nvar mapLon = 12.4832;"
                        "\nvar mapZoom = 5;"
                        "\nvar infobox = '<b>Compare to OSM</b>';"
                        "\ninfobox += '<br><br>Modify this box by editing:"
                        "<br><i>%s</i>';"
                        "\ninfobox += '<br><br>OSM data:';"
                        "\nfor (i in tasks) {"
                        "\n    infobox += '<br><i>- ' + tasks[i].name + ' ' + "
                        "tasks[i][\"analysis_time\"] + '</i>';"
                        "\n}"
                        "\ninfobox += '<br><br>Click on the map to "
                        "edit with JOSM.';"
                        "\ninfobox += '<br><br>Created with:"
                        "<br><a href=\"https://github.com/simone-f/"
                        "compare-to-osm\" target=\"_blank\">"
                        "compare-to-osm</a>';") % self.PAGEINFOFILE
                fp.write(text)
        return tasks_config

    def read_json(self, jsonfile):
        try:
            with open(jsonfile) as fp:
                return json.load(fp)
        except ValueError:
            sys.exit("* Error, %s invalid json. Check if it has any error"
                     " (e.g. comments left)." % jsonfile)

    def update_tasks_info_file(self):
        tasks_info = {"tasks": []}
        for task in self.allTasks:
            tasks_info["tasks"].append({"comparator": task.comparator.name,
                                        "name": task.name,
                                        "bbox": task.bbox,
                                        "center": task.center,
                                        "output": task.output,
                                        "analysis_time": task.analysis_time
                                        })
        with open(self.TASKSINFOFILE, "w") as fp:
            fp.write(json.dumps(tasks_info,
                                sort_keys=True,
                                indent=4,
                                separators=(',', ': ')))

    def print_tasks(self, tasks_config):
        print "\n= Tasks ="
        for task in tasks_config["tasks"]:
            if self.args.tasks is None or (self.args.tasks is not None
               and task["name"] in self.args.tasks):
                print "\nname:", task["name"]
                print "comparator:", task["comparator"]
                print "zone name:", task["zone"]["name"]
                print "zone admin_level:", task["zone"]["admin_level"]
                print "boundaries shapefile:", task["data"]["boundaries"]
                print "highways shapefile:", task["data"]["shapefile"]
                print "output:", task["output"]["type"]
                print "min zoom:", task["output"]["min_zoom"]
                print "max zoom:", task["output"]["max_zoom"]


if __name__ == "__main__":
    app = App()
