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
        self.file = os.path.join(self.app.directory,
                                 self.app.args.project_file)
        self.directory = os.path.dirname(self.file)

        # Read tasks data
        config = self.read_file()

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
        if "page_template" not in config or config["page_template"] == "":
            self.page_template = ""
        else:
            self.page_template = config["page_template"]

        # Analyse only the specified tasks (--tasks option)
        self.tasks_config = config["tasks"]
        tasks_names = [t["name"] for t in self.tasks_config]
        if self.app.args.tasks:
            for task_name in self.app.args.tasks:
                if task_name not in tasks_names:
                    sys.exit("\n* Error: tasks.json does not contain a task"
                             " with this name: %s" % task_name)

        self.allTasks = []
        self.tasks = []
        for task_config in config["tasks"]:
            # Create Task object
            task = Task(self, task_config)
            self.allTasks.append(task)
            if not self.app.args.tasks or (task_config["name"]
                                           in self.app.args.tasks):
                self.tasks.append(task)

    def read_file(self):
        try:
            with open(self.file) as fp:
                return json.load(fp)
        except ValueError:
            sys.exit("* Error: %s invalid json. Check if there is any error "
                     "in it." % self.file)

    def print_configuration(self):
        print "\n= Project"
        print "\ntitle:", self.title
        print "map lat:", self.map_lat
        print "map lon:", self.map_lon
        print "map zoom:", self.map_zoom
        print "page template:", self.page_template
        print "\n== Tasks"
        for task in self.allTasks:
            print "\nname:", task.name
            print "comparator:", task.comparator.name
            print "zone name:", task.zone_name
            print "zone admin_level:", task.zone_admin_level
            print "boundaries_file shapefile:", task.boundaries_file
            print "highways shapefile:", task.shape_file
            print "output:", task.output
            print "min zoom:", task.min_zoom
            print "max zoom:", task.max_zoom

    def update_map_data(self):
        for task in self.tasks:
            print "\n= Update map data: %s =" % task.name
            task.update_map_data()

    def create_web_page(self):
        """Generate html/index.html with jinja2
        """
        if self.map_lat == self.map_lon == "":
            self.map_lat = self.allTasks[-1].center[0]
            self.map_lon = self.allTasks[-1].center[1]
        if self.page_template == "":
            template_dir = os.path.join(self.app.directory, "html",
                                        "templates")
            template_file = "default_index.html"
        else:
            template_dir = self.templates_dir
            template_file = self.page_template
        template_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
                                          template_dir))
        template = template_env.get_template(template_file)
        output_text = template.render({"project": self})
        style_file = open(os.path.join(self.html_dir, "index.html"), "w")
        style_file.write(output_text)
        style_file.close()

    def update_file(self):
        config = {"title": self.title,
                  "map_lat": self.map_lat,
                  "map_lon": self.map_lon,
                  "map_zoom": self.map_zoom,
                  "page_template": self.page_template,
                  "tasks": []}
        for task in self.allTasks:
            config["tasks"].append({
                "name": task.name,

                "comparator": task.comparator.name,

                "data": {
                    "shapefile": task.shape_file + ".shp",
                    "boundaries_file": task.boundaries_file + ".shp",
                    },

                "zone": {
                    "name": task.zone_name,
                    "admin_level": task.zone_admin_level,
                    },

                "output": {
                    "type": task.output,
                    "min_zoom": task.min_zoom,
                    "max_zoom": task.max_zoom
                    },

                "info": task.info,

                "program": {
                    "analysis_time": task.analysis_time,
                    "bbox": task.bbox,
                    "center": task.center
                }})
            if task.info != {}:
                config["tasks"][-1]["info"] = task.info

            if task.postgis_user != "":
                config["tasks"][-1]["postgis_user"] = task.postgis_user

            if task.postgis_password != "":
                config["tasks"][-1]["postgis_password"] = task.postgis_password

        with open(self.file, "w") as fp:
            fp.write(json.dumps(config,
                                sort_keys=True,
                                indent=4,
                                separators=(',', ': ')))
