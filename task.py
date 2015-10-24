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
from subprocess import call, Popen, PIPE
from rendering.renderer import Renderer


class Task():
    def __init__(self, project, config):
        self.app = project.app
        self.statuses = ("notinosm", "onlyinosm")

        # Input
        self.name = config["name"]
        self.shape_file = config["data"]["shapefile"]
        self.boundaries_file = config["data"]["boundaries_file"]
        self.zone_name = config["zone"]["name"]
        self.zone_admin_level = config["zone"]["admin_level"]

        # OSM data
        osm_dir = os.path.join(project.data_dir, "osm_data", self.name)
        if not os.path.exists(osm_dir):
            os.makedirs(osm_dir)
        self.osm_file = os.path.join(osm_dir, "%s.osm" % self.name)
        self.osm_file_pbf = os.path.join(osm_dir, "%s.pbf" % self.name)

        # Output config
        if "output" not in config:
            self.output = "vector"
            self.min_zoom = ""
            self.max_zoom = ""
        else:
            self.output = config["output"]["type"]
            if "min_zoom" not in config["output"]:
                self.min_zoom = "5"
                self.max_zoom = "11"
            else:
                self.min_zoom = config["output"]["min_zoom"]
                self.max_zoom = config["output"]["max_zoom"]

        # Output data
        self.output_dir = os.path.join(project.data_dir, "output", self.name)
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        self.geojson_files = [os.path.join(self.output_dir,
                              "%s.GeoJSON" % status)
                              for status in self.statuses]

        self.shapefiles = [os.path.join(self.output_dir,
                           "%s.shp" % status)
                           for status in self.statuses]

        # Map config
        self.bbox = config["program"]["bbox"]
        self.center = config["program"]["center"]
        self.analysis_time = config["program"]["analysis_time"]

        # Map data
        self.map_data_dir = os.path.join(project.html_dir, "data", self.name)
        self.map_data_dir_topojson = os.path.join(self.map_data_dir,
                                                  "topojson")
        self.map_data_dir_png = os.path.join(self.map_data_dir, "PNG")
        self.map_data_dir_tiles = os.path.join(self.map_data_dir, "tiles")

        if "postgis_user" not in config:
            self.postgis_user = ""
        else:
            self.postgis_user = config["postgis_user"]
        if "postgis_password" not in config:
            self.postgis_password = ""
        else:
            self.postgis_password = config["postgis_password"]

        modulename = "comparators.%s" % config["comparator"]
        classname = modulename[12:].title()
        m = __import__(modulename, globals(), locals(), [classname])
        self.comparator = getattr(m, classname)(self)

        if self.comparator.database_type == "spatialite":
            self.database = os.path.join(project.data_dir,
                                         "%s.sqlite" % self.name)
        elif self.comparator.database_type == "postgis":
            self.database = self.name

        # Additional info that may be used by
        # a custom index.html jinja2 template
        if "info" in config:
            self.info = config["info"]
        else:
            self.info = {}

    def compare(self):
        self.comparator.analyse()

    def read_boundaries_bbox(self):
        """Read boundaries_file bbox to use it in generate_tiles.py
        """
        if self.comparator.database_type == "spatialite":
            query = """
                SELECT MbrMinX(Geometry), MbrMinY(Geometry),
                MbrMaxX(Geometry), MbrMaxY(Geometry) FROM boundaries_file;"""
            echo_query = Popen(["echo", query], stdout=PIPE)
            find_bbox = Popen(["spatialite", self.database],
                              stdin=echo_query.stdout, stdout=PIPE)
            echo_query.stdout.close()
            (stdoutdata, err) = find_bbox.communicate()
            self.bbox = [float(x) for x in stdoutdata[:-1].split("|")]
        elif self.comparator.database_type == "postgis":
            query = ("SELECT ST_XMin(ST_Extent(Geometry)), "
                     "ST_YMin(ST_Extent(Geometry)), "
                     "ST_XMax(ST_Extent(Geometry)), "
                     "ST_YMax(ST_Extent(Geometry)) "
                     "FROM notinosm;")
            echo_query = Popen(["echo", query], stdout=PIPE)
            find_bbox = Popen(["psql", self.database],
                              stdin=echo_query.stdout, stdout=PIPE)
            echo_query.stdout.close()
            (stdoutdata, err) = find_bbox.communicate()
            self.bbox = [float(x.strip())
                         for x in stdoutdata.split("\n")[2].split("|")]
        print "bbox:", self.bbox

    def read_boundaries_center(self):
        """Read boundaries_file center to use it in index.html
        """
        lon = self.bbox[0] + (self.bbox[2] - self.bbox[0]) / 2
        lat = self.bbox[1] + (self.bbox[3] - self.bbox[1]) / 2
        self.center = [lat, lon]
        print "center:", self.center

    def update_map_data(self):
        """Update data files used by Leaflet.
           If output: "vector":
               GeoJSON --> TopoJSON
           if output: "raster":
               Shapefile --> (mapnik) PNG tiles
        """
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
                         self.comparator.geometry_type)

    def remove_old_files_and_create_dirs(self, directory):
        if os.path.isdir(directory):
            self.execute("cmd", "rm -r %s/*" % directory)
        else:
            os.makedirs(directory)

    def execute(self, mode, cmd):
        """mode == cmd OR spatialite OR postgis
        """
        if mode == "spatialite":
            cmd = "echo \"%s\" | spatialite %s" % (cmd, self.database)
        elif mode == "postgis":
            cmd = "echo \"%s\" | psql -d %s" % (cmd, self.database)
        print cmd
        call(cmd, shell=True)
