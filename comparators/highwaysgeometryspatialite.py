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

from comparator import Comparator
import os
import sys


# Module for comparing highways in OSM with highways in open data.
# OSM features: highways
# Open data geometry: LINESTRING or MULTILINESTRING
# Source: Shapefile
# Database: Spatialite
class Highwaysgeometryspatialite(Comparator):
    def __init__(self, task):
        Comparator.__init__(self, task)
        self.name = "highwaysgeometryspatialite"
        self.geometry_type = "lines"
        self.database_type = "spatialite"

    def create_db(self):
        """Create a Spatialite database with OSM highways
           and lines from open data.
        """
        print "- Remove data produced by previous executions of the script"
        self.task.execute("cmd", "rm {0}/li* {1}".format(
                          self.task.osm_dir,
                          self.task.database))

        # Import boundaries_file
        print "\n- import zone's boundaries_file into database"
        cmd = ("spatialite_tool -i -shp {0} -d {1}"
               " -t boundaries_file -c UTF-8 -s 4326").format(
            self.task.boundaries_file,
            self.task.database)
        self.task.execute("cmd", cmd)
        sql = "SELECT CreateSpatialIndex('boundaries_file', 'Geometry');"
        self.task.execute("spatialite", sql)

        # Import OSM data
        print "\n- import OSM data into database"
        cmd = ("ogr2ogr -f \"ESRI Shapefile\" {0} {1}"
               " -sql \"SELECT osm_id FROM lines\""
               " -lco SHPT=ARC").format(self.task.osm_dir,
                                        self.task.osm_file_pbf)
        self.task.execute("cmd", cmd)

        cmd = ("spatialite_tool -i -shp {0} -d {1}"
               " -t raw_osm_ways -c UTF-8 -s 4326").format(
            os.path.join(self.task.osm_dir, "lines"),
            self.task.database)
        self.task.execute("cmd", cmd)

        print ("\n- extract highways in OSM that intersect zone's "
               "boundaries_file")
        sql = """
            CREATE TABLE osm_ways_MIXED AS
            SELECT ST_Intersection(b.Geometry, w.Geometry) AS Geometry
            FROM boundaries_file AS b, raw_osm_ways AS w;"""
        self.task.execute("spatialite", sql)

        self.multilines_to_line("osm_ways_MIXED", "osm_ways")
        sql = """
            SELECT RecoverGeometryColumn('osm_ways', 'Geometry',
            4326, 'LINESTRING', 'XY');"""
        self.task.execute("spatialite", sql)

        # Import open data
        print "\n- import open data"
        cmd = ("spatialite_tool -2 -i -shp {0} -d {1}"
               " -t open_data_ways_MIXED -c CP1252 -s 4326").format(
               self.task.shape_file,
               self.task.database)
        self.task.execute("cmd", cmd)

        self.multilines_to_line("open_data_ways_MIXED", "open_data_ways")
        sql = """
            SELECT RecoverGeometryColumn('open_data_ways', 'Geometry',
            4326, 'LINESTRING', 'XY');"""
        self.task.execute("spatialite", sql)

        # Create spatial indexes and buffers around OSM/open data ways
        for table in ("osm_ways", "open_data_ways"):

            print "\n- create spatial index of ", table
            sql = "SELECT CreateSpatialIndex('{0}', 'Geometry');".format(table)
            self.task.execute("spatialite", sql)

            print "\n- create buffers of ", table
            sql = """
                CREATE TABLE {0}_buffer AS
                SELECT ST_Buffer(Geometry, 0.0001) AS Geometry
                FROM {0}
                WHERE ST_Buffer(Geometry, 0.0001) NOT NULL;""".format(table)
            self.task.execute("spatialite", sql)
            sql = """
                SELECT RecoverGeometryColumn('{0}_buffer', 'Geometry',
                4326, 'POLYGON', 'XY');""".format(table)
            self.task.execute("spatialite", sql)
            sql = ("SELECT CreateSpatialIndex('{0}_buffer', "
                   "'Geometry');").format(table)
            self.task.execute("spatialite", sql)

    def compare(self, table):
        """Calculate differences between OSM/open data ways and their buffers
        """
        if table == "notinosm":
            print ("\n- Find ways in zone's data which are missing in OSM"
                   "\n  (open_data_ways - osm_ways_buffer)")
            ways = "open_data_ways"
            buff = "osm_ways_buffer"
        elif table == "onlyinosm":
            print ("\n- Find ways in OSM which are missing in zone's data"
                   "\n  (osm_ways - open_data_ways_buffer)")
            ways = "osm_ways"
            buff = "open_data_ways_buffer"

        sql = """
        CREATE TABLE {temptable}_MIXED AS
        SELECT Geometry FROM (
            SELECT
            ST_Difference(way.Geometry, ST_Union(buffer.Geometry)) AS Geometry
            FROM {ways} AS way, {buff} AS buffer
            WHERE ST_Intersects(way.Geometry, buffer.Geometry) AND
            buffer.ROWID IN (
                    SELECT ROWID
                    FROM SpatialIndex
                    WHERE f_table_name = '{buff}'
                    AND search_frame = way.Geometry)
            GROUP BY way.Geometry)
        WHERE Geometry IS NOT NULL
        UNION
        SELECT way.Geometry AS Geometry
        FROM {ways} AS way
        WHERE way.Geometry NOT IN
            (SELECT way.Geometry
            FROM {ways} AS way, {buff} AS buffer
            WHERE ST_Intersects(way.Geometry, buffer.Geometry)
            AND buffer.ROWID IN (
                SELECT ROWID
                FROM SpatialIndex
                WHERE f_table_name = '{buff}'
                AND search_frame = way.Geometry));
        """.format(temptable=table, ways=ways, buff=buff)
        self.task.execute("spatialite", sql)

        self.multilines_to_line("{0}_MIXED".format(table), table)
        sql = """
            SELECT RecoverGeometryColumn('{0}', 'Geometry',
            4326, 'LINESTRING', 'XY');""".format(table)
        self.task.execute("spatialite", sql)
