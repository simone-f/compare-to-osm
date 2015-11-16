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
import json
from task import Task
import jinja2
from shutil import copytree


class Project(object):

    def __init__(self, app):
        self.app = app
        # Configuration
        project_file = os.path.join(self.app.directory,
                                    self.app.args.project_file)
        self.directory = os.path.dirname(project_file)
        self.project_output_file = os.path.join(self.directory,
                                                "project_output.json")

        # Read tasks data
        config = self.read_file(project_file)

        # Create missing directories and files
        self.data_dir = os.path.join(self.directory, "data")
        self.osm_dir = os.path.join(self.data_dir, "osm_data")
        self.templates_dir = os.path.join(self.directory, "templates")
        self.html_dir = os.path.join(self.directory, "html")
        for d in (self.data_dir, self.osm_dir, self.html_dir,
                  self.templates_dir):
            if not os.path.exists(d):
                if d == self.html_dir:
                    copytree(os.path.join(self.app.directory, "html", "js"),
                             os.path.join(self.html_dir, "js"))
                    copytree(os.path.join(self.app.directory, "html", "css"),
                             os.path.join(self.html_dir, "css"))
                else:
                    os.makedirs(d)

        if "title" not in config:
            self.title = "Compare to OSM"
        else:
            self.title = config["title"]
        if "map_lat" not in config:
            self.map_lat = ""
            self.map_lon = ""
        else:
            self.map_lat = config["map_lat"]
            self.map_lon = config["map_lon"]
        if "map_zoom" not in config:
            self.map_zoom = "5"
        else:
            self.map_zoom = config["map_zoom"]

        # Tasks config

        # Analyse only the specified tasks (--tasks option)
        self.tasks_config = config["tasks"]
        tasks_names = [t["name"] for t in self.tasks_config]
        if self.app.args.tasks:
            for task_name in self.app.args.tasks:
                if task_name not in tasks_names:
                    sys.exit("\n* Error: tasks.json does not contain a task"
                             " with this name: {0}".format(task_name))

        # Read stats from previous execution (project_output.json)
        if not os.path.isfile(self.project_output_file):
            self.output_stats = {"tasks": {}}
        else:
            self.output_stats = self.read_file(self.project_output_file)

        self.allTasks = []
        self.tasks = []
        for task_config in config["tasks"]:
            # Build Task object
            task = Task(self, task_config)
            self.allTasks.append(task)
            if not self.app.args.tasks or (task_config["name"]
                                           in self.app.args.tasks):
                self.tasks.append(task)

    def read_file(self, filename):
        try:
            with open(filename) as fp:
                return json.load(fp)
        except ValueError:
            sys.exit("* Error: {0} invalid json. Check if there is any error "
                     "in it.".format(filename))

    def print_configuration(self):
        print "\n= Project"
        print "\ntitle:", self.title
        print "map lat:", self.map_lat
        print "map lon:", self.map_lon
        print "map zoom:", self.map_zoom
        print "\n== Tasks"
        for task in self.allTasks:
            print "\nname:", task.name
            print "comparator:", task.comparator.name
            print "overpass query:", task.overpass_query
            print "boundaries_file shapefile:", task.boundaries_file
            print "highways shapefile:", task.shape_file
            print "output:", task.output
            print "min zoom:", task.min_zoom
            print "max zoom:", task.max_zoom

    def update_map_data(self):
        for task in self.tasks:
            print "\n= Update map data: {0} =".format(task.name)
            task.update_map_data()

    def create_web_page(self):
        """Generate html/index.html with jinja2
        """
        if self.map_lat == self.map_lon == "":
            self.map_lat = self.allTasks[-1].center[0]
            self.map_lon = self.allTasks[-1].center[1]
        template_file = "index.html"
        if os.path.isfile(os.path.join(self.templates_dir, template_file)):
            template_dir = self.templates_dir
        else:
            template_dir = os.path.join(self.app.directory, "html",
                                        "templates")
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
                                          template_dir))
        template = template_env.get_template(template_file)
        output_text = template.render({"project": self})
        with open(os.path.join(self.html_dir, "index.html"), "w") as f:
            f.write(output_text)

    def update_output_file(self):
        """Update the file that contains statistics of the analysis.
        """
        config = {"tasks": {}}
        for task in self.allTasks:
            config["tasks"][task.name] = {"analysis_time": task.analysis_time,
                                          "bbox": task.bbox,
                                          "center": task.center}

        with open(self.project_output_file, "w") as fp:
            fp.write(json.dumps(config,
                                sort_keys=True,
                                indent=4,
                                separators=(',', ': ')))
