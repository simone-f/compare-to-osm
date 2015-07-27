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
from subprocess import call, Popen, PIPE
from rendering.renderer import Renderer


class Task():
    def __init__(self, app, task_config):
        self.app = app
        self.statuses = ("notinosm", "onlyinosm")

        # Input
        self.name = task_config["name"]
        self.zone_name = task_config["zone"]["name"]
        self.zone_admin_level = task_config["zone"]["admin_level"]
        self.shape_file = task_config["data"]["shapefile"]
        self.boundaries = task_config["data"]["boundaries"]
        self.bbox = task_config["bbox"]
        self.center = task_config["center"]
        self.analysis_time = task_config["analysis_time"]

        self.osm_file = "data/OSM/%s.osm" % self.name

        # Output
        self.output = task_config["output"]["type"]
        self.min_zoom = task_config["output"]["min_zoom"]
        self.max_zoom = task_config["output"]["max_zoom"]

        self.database = "data/out/%s.sqlite" % self.name
        self.output_dir = os.path.join("data", "out", self.name)
        self.geojson_files = [os.path.join(self.output_dir,
                              "%s.GeoJSON" % status)
                              for status in self.statuses]

        self.shapefiles = [os.path.join(self.output_dir,
                           "%s.shp" % status)
                           for status in self.statuses]

        # Export to map
        self.map_data_dir = os.path.join("html", "data", self.name)
        self.map_data_dir_topojson = os.path.join(self.map_data_dir,
                                                  "topojson")
        self.map_data_dir_png = os.path.join(self.map_data_dir, "PNG")
        self.map_data_dir_tiles = os.path.join(self.map_data_dir, "tiles")

        # geometries_type is used to choose from style_lines.xml or
        # style_points.xml in rendering
        self.geometry_type = ""

        modulename = "comparators.%s" % task_config["comparator"]
        classname = modulename[12:].title()
        m = __import__(modulename, globals(), locals(), [classname])
        self.comparator = getattr(m, classname)(self)

    def read_boundaries_bbox(self):
        """Read boundaries bbox to use it in generate_tiles.py
        """
        query = """
            SELECT MbrMinX(Geometry), MbrMinY(Geometry),
            MbrMaxX(Geometry), MbrMaxY(Geometry) FROM boundaries;"""
        echo_query = Popen(["echo", query], stdout=PIPE)
        find_bbox = Popen(["spatialite", self.database],
                          stdin=echo_query.stdout, stdout=PIPE)
        echo_query.stdout.close()
        (stdoutdata, err) = find_bbox.communicate()
        self.bbox = [float(x) for x in stdoutdata[:-1].split("|")]
        print "bbox:", self.bbox

    def read_boundaries_center(self):
        """Read boundaries center to use it in index.html
        """
        query = """
            SELECT ST_Y(ST_Centroid(ST_Boundary(Geometry))),
            ST_X(ST_Centroid(ST_Boundary(Geometry))) FROM boundaries;"""
        echo_query = Popen(["echo", query], stdout=PIPE)
        find_center = Popen(["spatialite", self.database],
                            stdin=echo_query.stdout, stdout=PIPE)
        echo_query.stdout.close()
        (stdoutdata, err) = find_center.communicate()
        self.center = [float(x) for x in stdoutdata[:-1].split("|")]
        print "center:", self.center

    def update_map_data(self):
        """Update data files used by Leaflet.
           If output: "vector":
               GeoJSON --> TopoJSON
           if output: "raster":
               Shapefile --> (mapnik) PNG tiles
        """
        if not os.path.isfile(self.database):
            sys.exit("\n* Error: it is not possible to continue; the database"
                     " with the analysis is missing.")

        # Remove old files and create missing directories
        print "Remove old files..."
        for directory in (self.map_data_dir_topojson,
                          self.map_data_dir_png,
                          self.map_data_dir_tiles):
            self.remove_old_files_and_create_dirs(directory)

        print ""
        if self.output == "vector":
            cmd = "topojson -q 10000000 -o %s %s" % (
                  os.path.join(self.map_data_dir_topojson, "vector.GeoJSON"),
                  " ".join(self.geojson_files))
            self.execute("cmd", cmd)

        elif self.output == "raster":
            for i, status in enumerate(self.statuses):
                Renderer(self, status, self.shapefiles[i],
                         self.geometry_type)

    def remove_old_files_and_create_dirs(self, directory):
        if os.path.isdir(directory):
            self.execute("cmd", "rm -r %s/*" % directory)
        else:
            os.makedirs(directory)

    def execute(self, mode, cmd):
        """mode == cmd OR qry
        """
        if mode == "qry":
            cmd = "echo \"%s\" | spatialite %s" % (cmd, self.database)
        print cmd
        call(cmd, shell=True)