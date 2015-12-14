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

import time
import os
import sys


class Comparator:
    def __init__(self, task):
        self.task = task
        self.app = self.task.app
        # Geometry_type is used to choose from style_lines.xml or
        # style_points.xml in map rendering
        self.geometry_type = ""
        self.database_type = ""      # "spatialite" OR "postgis"

    def download_osm(self):
        url = 'http://overpass-api.de/api/interpreter?{0}'.format(
              self.task.overpass_query)
        cmd = "wget '{0}' -O {1}".format(url, self.task.osm_file)
        self.task.execute("cmd", cmd)
        self.convert_osm_to_pbf(self.task.osm_file, self.task.osm_file_pbf)

    def filter_osm(self):
        current_dir = os.getcwd()
        os.chdir(self.task.osm_dir)
        self.task.execute("cmd", self.task.osmfilter_command)
        self.convert_osm_to_pbf(self.task.osm_file_o5m, self.task.osm_file_pbf)
        os.chdir(current_dir)

    def convert_osm_to_pbf(self, osm_file, pbf_file):
        cmd = "osmconvert {0} -o={1}".format(osm_file, pbf_file)
        self.task.execute("cmd", cmd)

    def analyse(self):
        if self.app.args.download_osm:
            print "\n== Donwload OSM data of the task"
            if self.task.overpass_query == "":
                sys.exit("\n*Error: you must specify an Overpass query for "
                         "\"{0}\" task in project.json to use "
                         "--download_osm".format(self.task.name))
            self.download_osm()

        if self.app.args.filter_osm:
            print "\n== Filter OSM data of the task"
            if self.task.osmfilter_command == "":
                sys.exit("\n*Error: you must specify an osmfilter command "
                         " (\"osmfilter_command\" property) for "
                         "\"{0}\" task in project.json to use "
                         "--filter_osm".format(self.task.name))
            self.filter_osm()

        # Check that OSM data exist
        if not os.path.isfile(self.task.osm_file_pbf):
            if (os.path.isfile(self.task.osm_file) and
                    os.stat(self.task.osm_file).st_size == 0):
                os.remove(self.task.osm_file)
            if os.path.isfile(self.task.osm_file):
                self.convert_osm_to_pbf(self.task.osm_file,
                                        self.task.osm_file_pbf)
            else:
                sys.exit("\n* Error: the file with OSM data "
                         "is missing. See \"OpenStreetMap data\" section in "
                         "README.md.")

        print "\n== Create database =="
        self.create_db()

        print ("\n== Calculate differences between OSM/open data ways"
               " and their buffers ==")
        for status in self.task.statuses:
            self.compare(status)

        print ("\n== Export analysis' result as GeoJSON and Shapefiles ==")
        self.export()

        self.task.analysis_time = time.strftime("%d/%m/%Y")

        print "\n== Read bbox and center coordinates of the zone =="
        self.task.read_boundaries_bbox()
        self.task.read_boundaries_center()

    def multilines_to_line(self, table_in, table_out):
        print ("\n- convert multilinestring to linestring"
               " in table {0}").format(table_in)
        # Extract MULTILINESTRINGs
        sql = """
            CREATE TABLE {0}_MULTILINESTRING AS SELECT Geometry
            FROM {1}
            WHERE GeometryType(Geometry) = 'MULTILINESTRING';""".format(
            table_out,
            table_in)
        self.task.execute("spatialite", sql)
        sql = """
            SELECT RecoverGeometryColumn('{0}_MULTILINESTRING', 'Geometry',
                4326, 'MULTILINESTRING', 'XY');""".format(table_out)
        self.task.execute("spatialite", sql)
        # Convert MULTILINESTRING to linestring and union with LINESTRINGs
        sql = (".elemgeo {0}_MULTILINESTRING Geometry"
               " {1}_SINGLELINESTRING pk_elem multi_id;").format(table_out,
                                                                 table_out)
        self.task.execute("spatialite", sql)
        sql = """
            CREATE TABLE {0} AS
            SELECT Geometry
            FROM {0}_SINGLELINESTRING
            UNION
            SELECT Geometry
            FROM {1} WHERE GeometryType(Geometry) = 'LINESTRING';
            """.format(table_out, table_in)
        self.task.execute("spatialite", sql)

    def export(self):
        """Export results.
           If output: "vector":
           Spatialite --> GeoJSON
           Spatialite --> Shapefile
        """
        for i, status in enumerate(self.task.statuses):
            print "status", status

            # Export as GeoJSON
            cmd = "ogr2ogr -f \"GeoJSON\" \"{0}\" ".format(
                  self.task.geojson_files[i])
            if self.database_type == "spatialite":
                cmd += "{0} -sql \"SELECT Geometry FROM ".format(
                       self.task.database)
            elif self.database_type == "postgis":
                cmd += ("PG:\"host=localhost user={0}"
                        " dbname={1} password={2}\" \"").format(
                        self.task.postgis_user, self.task.database,
                        self.task.postgis_password)
            cmd += "{0}\"".format(status)
            self.task.execute("cmd", cmd)

            # Export as Shapefile
            cmd = "ogr2ogr -f \"ESRI Shapefile\" \"{0}\" ".format(
                  self.task.shapefiles[i])
            if self.database_type == "spatialite":
                cmd += "{0} -sql \"SELECT Geometry FROM ".format(
                       self.task.database)
            elif self.database_type == "postgis":
                cmd += ("PG:\"host=localhost user={0}"
                        " dbname={1} password={2}\" \"").format(
                    self.task.postgis_user,
                    self.task.database,
                    self.task.postgis_password)
            cmd += "{0}\"".format(status)
            self.task.execute("cmd", cmd)
