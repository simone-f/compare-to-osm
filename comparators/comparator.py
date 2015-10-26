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


class Comparator:
    def __init__(self, task):
        self.task = task
        self.app = self.task.app
        # Geometry_type is used to choose from style_lines.xml or
        # style_points.xml in map rendering
        self.geometry_type = ""
        self.database_type = ""      # "spatialite" OR "postgis"

    def download_osm(self):
        url = 'http://overpass.osm.rambler.ru/cgi/interpreter?'
        url += self.overpass_query
        cmd = "wget '%s' -O %s" % (url, self.task.osm_file)
        self.task.execute("cmd", cmd)

    def analyse(self):
        if self.app.args.download_osm:
            print "\n== Donwload OSM data of the task"
            self.download_osm()

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
               " in table %s") % table_in
        # Extract MULTILINESTRINGs
        sql = """
            CREATE TABLE %s_MULTILINESTRING AS SELECT Geometry
            FROM %s
            WHERE GeometryType(Geometry) = 'MULTILINESTRING';""" % (table_out,
                                                                    table_in)
        self.task.execute("spatialite", sql)
        sql = """
            SELECT RecoverGeometryColumn('%s_MULTILINESTRING', 'Geometry',
                4326, 'MULTILINESTRING', 'XY');
            """ % (table_out)
        self.task.execute("spatialite", sql)
        # Convert MULTILINESTRING to linestring and union with LINESTRINGs
        sql = (".elemgeo %s_MULTILINESTRING Geometry"
               " %s_SINGLELINESTRING pk_elem multi_id;") % (table_out,
                                                            table_out)
        self.task.execute("spatialite", sql)
        sql = """
            CREATE TABLE %s AS
            SELECT Geometry
            FROM %s_SINGLELINESTRING
            UNION
            SELECT Geometry
            FROM %s WHERE GeometryType(Geometry) = 'LINESTRING';
            """ % (table_out, table_out, table_in)
        self.task.execute("spatialite", sql)

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
            print "status", status

            # Export as GeoJSON
            cmd = "ogr2ogr -f \"GeoJSON\" \"%s\" " % self.task.geojson_files[i]
            if self.database_type == "spatialite":
                cmd += "%s -sql \"SELECT Geometry FROM " % self.task.database
            elif self.database_type == "postgis":
                cmd += ("PG:\"host=localhost user=%s"
                        " dbname=%s password=%s\" \"" % (
                        self.task.postgis_user, self.task.database,
                        self.task.postgis_password))
            cmd += "%s\"" % status
            self.task.execute("cmd", cmd)

            # Export as Shapefile
            cmd = ("ogr2ogr -f \"ESRI Shapefile\" "
                   "\"%s\" ") % self.task.shapefiles[i]
            if self.database_type == "spatialite":
                cmd += "%s -sql \"SELECT Geometry FROM " % self.task.database
            elif self.database_type == "postgis":
                cmd += ("PG:\"host=localhost user=%s"
                        " dbname=%s password=%s\" \"") % (
                    self.task.postgis_user,
                    self.task.database,
                    self.task.postgis_password)
            cmd += "%s\"" % status
            self.task.execute("cmd", cmd)
