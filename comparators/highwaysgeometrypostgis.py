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
# Oepn data geometry: MULTILINESTRINGZM
# Source: Shapefile
# Database: PostGis
class Highwaysgeometrypostgis(Comparator):
    def __init__(self, task):
        Comparator.__init__(self, task)
        self.name = "highwaysgeometrypostgis"
        self.geometry_type = "lines"
        self.database_type = "postgis"

        # OSM query
        self.overpass_query = 'data=area'
        self.overpass_query += '[name="{0}"][admin_level={1}];'.format(
            self.task.zone_name, self.task.zone_admin_level)
        self.overpass_query += 'way(area)["highway"]'
        self.overpass_query += '["highway"!~"footway"]["highway"!~"cycleway"];'
        self.overpass_query += '(._;>;);out meta;'

    def create_db(self):
        """Create a PostGis database with OSM highways
           and lines from open data.
        """
        if not os.path.isfile(self.task.osm_file_pbf):
            sys.exit("\n* Error: the file with OSM data "
                     "is missing:\n{0}".format(self.task.osm_file_pbf))
        if self.task.postgis_user == "" or self.task.postgis_password == "":
            sys.exit("\n* Error: postgis_user or postgis_password are missing "
                     "in project file")

        print "- Create a new database"
        self.task.execute("cmd", "dropdb {0} --if-exists".format(
                          self.task.database))
        self.task.execute("cmd", "createdb {0}".format(self.task.database))

        self.task.execute("postgis", "CREATE EXTENSION postgis;")
        self.task.execute("postgis", "CREATE EXTENSION hstore;")

        self.task.execute("cmd",
                          ("psql -d {0} -f /usr/share/doc/osmosis/examples/"
                           "pgsnapshot_schema_0.6.sql").format(
                           self.task.database))
        self.task.execute("cmd",
                          ("psql -d {0} -f /usr/share/doc/osmosis/examples/"
                           "pgsnapshot_schema_0.6_linestring.sql").format(
                           self.task.database))

        # Import boundaries
        """
        print "\n- import zone's boundaries into database"
        cmd = ("spatialite_tool -i -shp {0} -d {1}"
               " -t boundaries -c UTF-8 -s 4326").format(self.task.boundaries,
                                                         self.task.database)
        self.task.execute("cmd", cmd)
        sql = "SELECT CreateSpatialIndex('boundaries', 'Geometry');"
        self.task.execute("sql", sql)"""

        # Import OSM data
        print "\n- import OSM data into database"
        self.task.execute("cmd",
                          ("osmosis --rb {0} --wp database={1} "
                           "user={2} password={3}").format(
                           self.task.osm_file_pbf, self.task.database,
                           self.task.postgis_user, self.task.postgis_password))

        # Import open data
        print "\n- import open data into database"
        sql_file = self.task.shape_file + ".sql"
        if os.path.isfile(sql_file):
            self.task.execute("cmd", "rm {0}".format(sql_file))
        self.task.execute("cmd",
                          ("shp2pgsql -s 4326 -W 'LATIN1' {0}.shp open_data "
                           "{1} > {2}").format(self.task.shape_file,
                                               self.task.database,
                                               sql_file))

        self.task.execute("cmd", "psql -d {0} -f {1}".format(
                          self.task.database,
                          sql_file))
        sql = """
            DROP TABLE IF EXISTS open_data_dump;

            CREATE TABLE open_data_dump AS
            SELECT open_data.gid AS gid,
            (ST_Dump(ST_Force2d(open_data.geom))).geom AS Geometry
            FROM open_data;
            CREATE INDEX ON open_data_dump USING GIST (Geometry);
            CREATE INDEX ON open_data_dump (gid);
            VACUUM ANALYZE open_data_dump;"""
        self.task.execute("postgis", sql)

        # Create buffers around OSM and open data ways
        for ways in ("ways", "open_data_dump"):
            print "\n- create buffers of ", ways
            if ways == "ways":
                geometry = "linestring"
            else:
                geometry = "Geometry"
            sql = """
                DROP TABLE IF EXISTS {ways}_buffer;

                CREATE TABLE {ways}_buffer AS
                SELECT ST_Buffer({geometry}, 0.0001) AS Geometry
                FROM {ways}
                WHERE ST_Buffer({geometry}, 0.0001) IS NOT NULL;

                CREATE INDEX ON {ways}_buffer USING GIST (Geometry);
                VACUUM ANALYZE {ways}_buffer;""".format(ways=ways,
                                                        geometry=geometry)
            self.task.execute("postgis", sql)

    def compare(self, table):
        """Calculate differences between OSM/open data ways and their buffers
        """

        if table == "notinosm":
            print "\n- Find ways in open data which are missing in OSM"
            ways = "open_data_dump"
            ways_id = "gid"
            ways_geometry = "Geometry"
            buff = "ways_buffer"
        elif table == "onlyinosm":
            print "\n- Find ways in OSM which are missing in open data"
            ways = "ways"
            ways_id = "id"
            ways_geometry = "linestring"
            buff = "open_data_dump_buffer"

        sql = """
            DROP TABLE IF EXISTS {ways}_intersecting, {table};

            -- Create a table with ways intersecting buffers
            CREATE TABLE {ways}_intersecting AS
              SELECT DISTINCT ways.{ways_id} AS id,
                              ways.{ways_geometry} AS Geometry
              FROM {ways} AS ways, {buff} AS buff
              WHERE ST_Intersects(ways.{ways_geometry}, buff.Geometry);

            CREATE INDEX ON {ways}_intersecting USING GIST (Geometry);
            CREATE INDEX ON {ways}_intersecting (id);
            VACUUM ANALYZE {ways}_intersecting;

            CREATE TABLE {table} AS (
              -- Difference between ways intersecating buffers and buffers
              SELECT (ST_Dump(ST_Difference(ways.Geometry,
                      ST_Union(buff.Geometry)))).geom AS Geometry
              FROM {ways}_intersecting AS ways, {buff} AS buff
              WHERE ST_Intersects(ways.Geometry, buff.Geometry)
              GROUP BY ways.Geometry
            UNION
              -- Add non intersecating ways
              SELECT ways.{ways_geometry} AS Geometry
              FROM {ways} AS ways
              LEFT OUTER JOIN {ways}_intersecting
              ON ways.{ways_id} = {ways}_intersecting.id
              WHERE {ways}_intersecting.id IS NULL);""".format(
            table=table,
            ways=ways,
            ways_id=ways_id,
            ways_geometry=ways_geometry,
            buff=buff)

        self.task.execute("postgis", sql)
