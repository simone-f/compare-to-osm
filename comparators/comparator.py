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


class Comparator:
    def __init__(self, task):
        self.app = task.app
        self.task = task

    def download_osm(self):
        url = 'http://overpass.osm.rambler.ru/cgi/interpreter?'
        url += self.overpass_query
        cmd = "wget '%s' -O %s" % (url, self.task.osm_file)
        self.task.execute("cmd", cmd)

    def analyse(self):
        if not self.app.args.offline:
            print ("\n== Donwload OSM data of the task =="
                   "\n   highway=* != footway != cycleway")
            self.download_osm()
        if not os.path.isfile(self.task.osm_file):
            sys.exit("\n* Error: the file with OSM data is missing.")

        print "\n== Create Spatialite database =="
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
               " in table %s") % table_in
        # Extract MULTILINESTRINGs
        sql = """
            CREATE TABLE %s_MULTILINESTRING AS SELECT Geometry
            FROM %s
            WHERE GeometryType(Geometry) = 'MULTILINESTRING';""" % (table_out,
                                                                    table_in)
        self.task.execute("sql", sql)
        sql = """
            SELECT RecoverGeometryColumn('%s_MULTILINESTRING', 'Geometry',
                4326, 'MULTILINESTRING', 'XY');
            """ % (table_out)
        self.task.execute("sql", sql)
        # Convert MULTILINESTRING to linestring and union with LINESTRINGs
        sql = (".elemgeo %s_MULTILINESTRING Geometry"
               " %s_SINGLELINESTRING pk_elem multi_id;") % (table_out,
                                                            table_out)
        self.task.execute("sql", sql)
        sql = """
            CREATE TABLE %s AS
            SELECT Geometry
            FROM %s_SINGLELINESTRING
            UNION
            SELECT Geometry
            FROM %s WHERE GeometryType(Geometry) = 'LINESTRING';
            """ % (table_out, table_out, table_in)
        self.task.execute("sql", sql)

    def export(self):
        """Export results.
           If output: "vector":
           Spatialite --> GeoJSON
           Spatialite --> Shapefile
        """
        # Remove old files and create missing directories
        print "Remove old files..."
        self.task.remove_old_files_and_create_dirs(self.task.output_dir)
        print ""

        for i, status in enumerate(self.task.statuses):
            cmd = ("ogr2ogr -f \"GeoJSON\" \"%s\" %s"
                   " -sql \"SELECT Geometry"
                   " FROM %s\"") % (self.task.geojson_files[i],
                                    self.task.database,
                                    status)
            self.task.execute("cmd", cmd)
            cmd = ("ogr2ogr -f \"ESRI Shapefile\" \"%s\" %s"
                   " -sql \"SELECT Geometry FROM %s\"") % (
                self.task.shapefiles[i],
                self.task.database,
                status)
            self.task.execute("cmd", cmd)
