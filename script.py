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

from subprocess import call, Popen, PIPE
import os
import sys
import time
import ConfigParser
from rendering.renderer import Renderer


class App():
    def __init__(self):

        start = time.time()

        # Configuration
        print "= Read config.cfg file ="
        self.zones = []
        for name, zone_config in self.read_config().iteritems():
            print "\n= %s =" % name
            self.zones.append(Zone(name, zone_config))

        print "\n= Export results ="
        for zone in self.zones:
            zone.export()

        # Create js file with list of zones
        self.create_zonesinfo_js()

        end = time.time()
        print "Execution time: ", end-start, "seconds."

    def create_zonesinfo_js(self):
        zones_list_file = open("html/data/zones_info.js", "w")
        text = ("// Automatically generated file"
                "\nvar zones = [")
        for i, zone in enumerate(self.zones):
            if i != 0:
                text += ","
            text += "['%s', %s, %s, '%s']" % (
                zone.name,
                zone.bbox,
                zone.center,
                zone.output)
        text += "];"
        zones_list_file.write(text)
        zones_list_file.close()

    def read_config(self):
        if not os.path.isfile('config.cfg'):
            open('config.cfg', 'a').close()
            sys.exit('Please, fill informations in \'config.cfg\'. See\
 \'config_example.cfg\' as an example')
        config = ConfigParser.RawConfigParser()
        config.read('config.cfg')

        # Read zones data
        zones_config = {}
        for name in config.sections():
            zones_config[name] = {}
            zones_config[name]["admin_level"] = config.get(name, 'admin_level')
            boundaries = config.get(name, 'boundaries')
            shapefile = config.get(name, 'shapefile')
            for (file_type, file_path) in (("Boundaries", boundaries),
                                           ("Local council", shapefile)):
                if not os.path.isfile(file_path):
                    sys.exit("%s shapefile file is missing:\n%s" % (file_type,
                                                                    file_path))
            zones_config[name]["boundaries"] = boundaries[:-4]
            zones_config[name]["shapefile"] = shapefile[:-4]
            zones_config[name]["output"] = config.get(name, 'output')
            if not config.has_option(name, 'min_zoom'):
                zones_config[name]["min_zoom"] = 10
            else:
                zones_config[name]["min_zoom"] = int(config.get(name,
                                                                'min_zoom'))
            if not config.has_option(name, 'max_zoom'):
                zones_config[name]["max_zoom"] = 13
            else:
                zones_config[name]["max_zoom"] = int(config.get(name,
                                                                'max_zoom'))

        # Create missing directories and files
        osmdir = os.path.join("data", "OSM")
        if not os.path.exists(osmdir):
            os.makedirs(osmdir)
        if not os.path.isfile('html/data/info.js'):
            info_file = open('html/data/info.js', "w")
            text = """
var title = 'Compare to OSM';
var mapZoom = 0;
var info = '<b>Compare to OSM</b>';
info += '<p>Modify html/data/info.js to write here';
info += '<br><br><a href="https://github.com/simone-f/\
compare-to-osm" target="_blank">Script code</a>';"""
            info_file.write(text)
            info_file.close()

        self.print_local_councils_data(zones_config)

        return zones_config

    def print_local_councils_data(self, zones_config):
        print "\n= Local Councils ="
        for name, zone_config in zones_config.iteritems():
            print "name:", name
            print "admin_level:", zone_config["admin_level"]
            print "boundaries shapefile:", zone_config["boundaries"]
            print "highways shapefile:", zone_config["shapefile"]
            print "output:", zone_config["output"]
            print


class Zone():
    def __init__(self, name, zone_config):
        # Input
        self.name = name
        self.admin_level = zone_config["admin_level"]
        self.shapeFile = zone_config["shapefile"]
        self.boundaries = zone_config["boundaries"]
        self.bbox = ""
        self.center = ""

        self.osmFile = "data/OSM/%s.osm" % name
        self.database = "data/%s.sqlite" % name

        # Output
        self.output = zone_config["output"]
        self.min_zoom = zone_config["min_zoom"]
        self.max_zoom = zone_config["max_zoom"]

        self.output_dir = os.path.join("data", "out", self.name)

        self.export_dir = os.path.join("html", "data", self.name)
        self.export_dir_topojson = os.path.join(self.export_dir, "topojson")
        self.export_dir_png = os.path.join(self.export_dir, "PNG")
        self.export_dir_tiles = os.path.join(self.export_dir, "tiles")

        print ("\n= Donwload OSM data of the zone ="
               "\n  highway=* != footway != cycleway")
        self.download_osm()

        print "\n= Create Spatialite database ="
        self.create_db()
        self.read_boundaries_bbox()
        self.read_boundaries_center()

        print "\n= Calculate differences between OSM/lc ways ="
        # Calculate differences between osm/lc ways and lc/osm buffers
        self.statuses = ("notinosm", "onlyinosm")

        for status in self.statuses:
            self.find_ways(status)

    def download_osm(self):
        url = 'http://overpass.osm.rambler.ru/cgi/interpreter?data=area'
        url += '[name="%s"][admin_level=%s];' % (self.name, self.admin_level)
        url += 'way(area)["highway"]'
        url += '["highway"!~"footway"]["highway"!~"cycleway"];'
        url += '(._;>;);out meta;'
        cmd = "wget '%s' -O %s" % (url, self.osmFile)
        self.execute("cmd", cmd)

    def create_db(self):
        """Create a Spatialite database with OSM highways and
           and lines from local council released data.
        """
        print "- Remove data produced by previous executions of the script"
        self.execute("cmd", "rm data/OSM/li* %s" % self.database)

        # Import boundaries
        print "\n- import local council's boundaries"
        cmd = ("spatialite_tool -i -shp %s -d %s"
               " -t boundaries -c UTF-8 -s 4326") % (self.boundaries,
                                                     self.database)
        self.execute("cmd", cmd)

        # Import OSM data
        print "\n- import OSM data into database"
        cmd = ("ogr2ogr -f \"ESRI Shapefile\" data/OSM %s"
               " -sql \"SELECT osm_id FROM lines\""
               " -lco SHPT=ARC") % self.osmFile
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
               " -t open_data_ways -c CP1252 -s 4326") % (self.shapeFile,
                                                         self.database)
        self.execute("cmd", cmd)

        # Create spatial indexes and buffers around osm/lc ways
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
        """Calculate differences between osm/lc ways and lc/osm buffers
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
           Spatialite --> GeoJSON --> TopoJSON for Leaflet
           if output: "raster":
           Spatialite --> Shapefile --> (mapnik) PNG tiles for Leaflet
        """
        print "\n- Export results for zone:", self.name

        # Remove old files and create missing directories
        print "- Remove old files..."
        for directory in (self.output_dir, self.export_dir_topojson,
                          self.export_dir_png,
                          self.export_dir_tiles):
            self.remove_old_files_and_create_dirs(directory)

        if self.output == "vector":
            geojson_files = [os.path.join(self.output_dir,
                             "%s.GeoJSON" % status)
                             for status in self.statuses]
            for i, status in enumerate(self.statuses):
                cmd = ("ogr2ogr -f \"GeoJSON\" \"%s\" %s"
                       " -sql \"SELECT Geometry FROM %s\"") % (geojson_files[i],
                                                               self.database,
                                                               status)
                self.execute("cmd", cmd)

            cmd = "topojson -q 10000000 -o %s %s" % (
                  os.path.join(self.export_dir_topojson, "vector.GeoJSON"),
                  " ".join(geojson_files))
            self.execute("cmd", cmd)

        elif self.output == "raster":
            shapefiles = [os.path.join(self.output_dir,
                          "%s.shp" % status)
                          for status in self.statuses]
            for i, status in enumerate(self.statuses):
                cmd = ("ogr2ogr -f \"ESRI Shapefile\" \"%s\" %s"
                       " -sql \"SELECT Geometry FROM %s\"") % (shapefiles[i],
                                                               self.database,
                                                               status)
                self.execute("cmd", cmd)

                Renderer(self, status, shapefiles[i])

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


if __name__ == "__main__":
    app = App()
