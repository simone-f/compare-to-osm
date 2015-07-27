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


class Highwaysgeometry(Comparator):
    def __init__(self, task):
        Comparator.__init__(self, task)

        self.name = "highwaysgeometry"
        task.geometry_type = "lines"

        self.overpass_query = 'data=area'
        self.overpass_query += '[name="%s"][admin_level=%s];' % (
            self.task.zone_name, self.task.zone_admin_level)
        self.overpass_query += 'way(area)["highway"]'
        self.overpass_query += '["highway"!~"footway"]["highway"!~"cycleway"];'
        self.overpass_query += '(._;>;);out meta;'

    def create_db(self):
        """Create a Spatialite database with OSM highways
           and lines from open data.
        """
        print "- Remove data produced by previous executions of the script"
        self.task.execute("cmd", "rm data/OSM/li* %s" % self.task.database)

        # Import boundaries
        print "\n- import zone's boundaries into database"
        cmd = ("spatialite_tool -i -shp %s -d %s"
               " -t boundaries -c UTF-8 -s 4326") % (self.task.boundaries,
                                                     self.task.database)
        self.task.execute("cmd", cmd)
        sql = "SELECT CreateSpatialIndex('boundaries', 'Geometry');"
        self.task.execute("qry", sql)

        # Import OSM data
        print "\n- import OSM data into database"
        cmd = ("ogr2ogr -f \"ESRI Shapefile\" data/OSM %s"
               " -sql \"SELECT osm_id FROM lines\""
               " -lco SHPT=ARC") % self.task.osm_file
        self.task.execute("cmd", cmd)

        cmd = ("spatialite_tool -i -shp data/OSM/lines -d %s"
               " -t raw_osm_ways -c UTF-8 -s 4326") % self.task.database
        self.task.execute("cmd", cmd)

        print "\n- extract highways in OSM that intersect zone's boundaries"
        sql = """
            CREATE TABLE osm_ways_MIXED AS
            SELECT ST_Intersection(b.Geometry, w.Geometry) AS Geometry
            FROM boundaries AS b, raw_osm_ways AS w;"""
        self.task.execute("qry", sql)

        self.multilines_to_line("osm_ways_MIXED", "osm_ways")
        sql = """
            SELECT RecoverGeometryColumn('osm_ways', 'Geometry',
            4326, 'LINESTRING', 'XY');"""
        self.task.execute("qry", sql)

        # Import open data
        print "\n- import open data"
        cmd = ("spatialite_tool -i -shp %s -d %s"
               " -t open_data_ways -c CP1252 -s 4326") % (self.task.shape_file,
                                                          self.task.database)
        self.task.execute("cmd", cmd)

        # Create spatial indexes and buffers around OSM/open data ways
        for table in ("osm_ways", "open_data_ways"):

            print "\n- create spatial index of ", table
            sql = "SELECT CreateSpatialIndex('%s', 'Geometry');" % table
            self.task.execute("qry", sql)

            print "\n- create buffers of ", table
            sql = """
                CREATE TABLE %s_buffer AS
                SELECT ST_Buffer(Geometry, 0.0001) AS Geometry
                FROM %s
                WHERE ST_Buffer(Geometry, 0.0001) NOT NULL;""" % (table,
                                                                  table)
            self.task.execute("qry", sql)
            sql = """
                SELECT RecoverGeometryColumn('%s_buffer', 'Geometry',
                4326, 'POLYGON', 'XY');""" % table
            self.task.execute("qry", sql)
            sql = "SELECT CreateSpatialIndex('%s_buffer', 'Geometry');" % table
            self.task.execute("qry", sql)

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
        CREATE TABLE {temptable} AS
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
        """.format(temptable="%s_MIXED" % table, ways=ways, buff=buff)
        self.task.execute("qry", sql)

        self.multilines_to_line("%s_MIXED" % table, table)
