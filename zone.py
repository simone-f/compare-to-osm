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
import time


class Zone():
    def __init__(self, app, name, zone_config):
        self.app = app
        self.statuses = ("notinosm", "onlyinosm")

        # Input
        self.name = name
        self.admin_level = zone_config["admin_level"]
        self.shape_file = zone_config["shapefile"]
        self.boundaries = zone_config["boundaries"]
        self.bbox = zone_config["bbox"]
        self.center = zone_config["center"]
        self.analysis_time = zone_config["analysis_time"]

        self.osm_file = "data/OSM/%s.osm" % name

        # Output
        self.output = zone_config["output"]
        self.min_zoom = zone_config["min_zoom"]
        self.max_zoom = zone_config["max_zoom"]

        self.database = "data/out/%s.sqlite" % name
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

    def analyse(self):
        if not self.app.args.offline:
            print ("\n== Donwload OSM data of the zone =="
                   "\n   highway=* != footway != cycleway")
            self.download_osm()
        if not os.path.isfile(self.osm_file):
            sys.exit("\n* Error: the file with OSM data is missing. Run"
                     " the program again without --offline and --export"
                     " options")

        print "\n== Create Spatialite database =="
        self.create_db()

        print ("\n== Calculate differences between OSM/open data ways"
               " and their buffers ==")
        for status in self.statuses:
            self.find_ways(status)

        print ("\n== Export analysis' result as GeoJSON and Shapefiles ==")
        self.export()

        self.analysis_time = time.strftime("%H-%d/%m/%Y")
        self.read_boundaries_bbox()
        self.read_boundaries_center()

    def download_osm(self):
        url = 'http://overpass.osm.rambler.ru/cgi/interpreter?data=area'
        url += '[name="%s"][admin_level=%s];' % (self.name, self.admin_level)
        url += 'way(area)["highway"]'
        url += '["highway"!~"footway"]["highway"!~"cycleway"];'
        url += '(._;>;);out meta;'
        cmd = "wget '%s' -O %s" % (url, self.osm_file)
        self.execute("cmd", cmd)

    def create_db(self):
        """Create a Spatialite database with OSM highways
           and lines from open data.
        """
        print "- Remove data produced by previous executions of the script"
        self.execute("cmd", "rm data/OSM/li* %s" % self.database)

        # Import boundaries
        print "\n- import zone's boundaries"
        cmd = ("spatialite_tool -i -shp %s -d %s"
               " -t boundaries -c UTF-8 -s 4326") % (self.boundaries,
                                                     self.database)
        self.execute("cmd", cmd)
        sql = "SELECT CreateSpatialIndex('boundaries', 'Geometry');"
        self.execute("qry", sql)

        # Import OSM data
        print "\n- import OSM data into database"
        cmd = ("ogr2ogr -f \"ESRI Shapefile\" data/OSM %s"
               " -sql \"SELECT osm_id FROM lines\""
               " -lco SHPT=ARC") % self.osm_file
        self.execute("cmd", cmd)

        cmd = ("spatialite_tool -i -shp data/OSM/lines -d %s"
               " -t raw_osm_ways -c UTF-8 -s 4326") % self.database
        self.execute("cmd", cmd)

        print "\n- extract highways in OSM that intersect zone's boundaries"
        sql = """
            CREATE TABLE osm_ways_MIXED AS
            SELECT ST_Intersection(b.Geometry, w.Geometry) AS Geometry
            FROM boundaries AS b, raw_osm_ways AS w;"""
        self.execute("qry", sql)

        self.multilines_to_line("osm_ways_MIXED", "osm_ways")
        sql = """
            SELECT RecoverGeometryColumn('osm_ways', 'Geometry',
            4326, 'LINESTRING', 'XY');"""
        self.execute("qry", sql)

        # Import open data
        print "\n- import open data"
        cmd = ("spatialite_tool -i -shp %s -d %s"
               " -t open_data_ways -c CP1252 -s 4326") % (self.shape_file,
                                                          self.database)
        self.execute("cmd", cmd)

        # Create spatial indexes and buffers around OSM/open data ways
        for table in ("osm_ways", "open_data_ways"):

            print "\n- create spatial index of ", table
            sql = "SELECT CreateSpatialIndex('%s', 'Geometry');" % table
            self.execute("qry", sql)

            print "\n- create buffers of ", table
            sql = """
                CREATE TABLE %s_buffer AS
                SELECT ST_Buffer(Geometry, 0.0001) AS Geometry
                FROM %s
                WHERE ST_Buffer(Geometry, 0.0001) NOT NULL;""" % (table,
                                                                  table)
            self.execute("qry", sql)
            sql = """
                SELECT RecoverGeometryColumn('%s_buffer', 'Geometry',
                4326, 'POLYGON', 'XY');""" % table
            self.execute("qry", sql)
            sql = "SELECT CreateSpatialIndex('%s_buffer', 'Geometry');" % table
            self.execute("qry", sql)

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

    def multilines_to_line(self, table_in, table_out):
        print ("\n- convert multilinestring to linestring"
               " in table %s") % table_in
        # Extract MULTILINESTRINGs
        sql = """
            CREATE TABLE %s_MULTILINESTRING AS SELECT Geometry
            FROM %s
            WHERE GeometryType(Geometry) = 'MULTILINESTRING';""" % (table_out,
                                                                    table_in)
        self.execute("qry", sql)
        sql = """
            SELECT RecoverGeometryColumn('%s_MULTILINESTRING', 'Geometry',
                4326, 'MULTILINESTRING', 'XY');
            """ % (table_out)
        self.execute("qry", sql)
        # Convert MULTILINESTRING to linestring and union with LINESTRINGs
        sql = (".elemgeo %s_MULTILINESTRING Geometry"
               " %s_SINGLELINESTRING pk_elem multi_id;") % (table_out,
                                                            table_out)
        self.execute("qry", sql)
        sql = """
            CREATE TABLE %s AS
            SELECT Geometry
            FROM %s_SINGLELINESTRING
            UNION
            SELECT Geometry
            FROM %s WHERE GeometryType(Geometry) = 'LINESTRING';
            """ % (table_out, table_out, table_in)
        self.execute("qry", sql)

    def find_ways(self, table):
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
        self.execute("qry", sql)

        self.multilines_to_line("%s_MIXED" % table, table)

    def export(self):
        """Export results.
           If output: "vector":
           Spatialite --> GeoJSON
           Spatialite --> Shapefile
        """
        # Remove old files and create missing directories
        print "Remove old files..."
        self.remove_old_files_and_create_dirs(self.output_dir)
        print ""

        for i, status in enumerate(self.statuses):
            cmd = ("ogr2ogr -f \"GeoJSON\" \"%s\" %s"
                   " -sql \"SELECT Geometry"
                   " FROM %s\"") % (self.geojson_files[i],
                                    self.database,
                                    status)
            self.execute("cmd", cmd)

            print ""

            cmd = ("ogr2ogr -f \"ESRI Shapefile\" \"%s\" %s"
                   " -sql \"SELECT Geometry FROM %s\"") % (self.shapefiles[i],
                                                           self.database,
                                                           status)
            self.execute("cmd", cmd)

    def update_map_data(self):
        """Update data files used by Leaflet.
           If output: "vector":
               GeoJSON --> TopoJSON
           if output: "raster":
               Shapefile --> (mapnik) PNG tiles
        """
        if not os.path.isfile(self.database):
            sys.exit("\n* Error: it is not possible to continue; the database"
                     " with the analysis is missing. Try to execute the"
                     " program again without --export_only option.")

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
                cmd = ("ogr2ogr -f \"ESRI Shapefile\" \"%s\" %s"
                       " -sql \"SELECT Geometry"
                       " FROM %s\"") % (self.shapefiles[i],
                                        self.database,
                                        status)
                self.execute("cmd", cmd)

                Renderer(self, status, self.shapefiles[i])

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
