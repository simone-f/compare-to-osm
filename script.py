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

from subprocess import call
import os
import sys
import ConfigParser


class App():
    def __init__(self):
        # Configuration
        print "= Read config.cfg file="

        zones = []
        for zoneData in self.read_config():
            print "\n= %s =" % zoneData[0]
            zones.append(Zone(zoneData))

        # Create js file with list of zones
        zonesListFile = open("html/data/zones_names.js", "w")
        text = "// Automatically generated file\nvar zones = ["
        for i, zone in enumerate(zones):
            if i != 0:
                text += ","
            text += "'%s'" % zone.name
        text += "];"
        zonesListFile.write(text)
        zonesListFile.close()

    def read_config(self):
        if not os.path.isfile('config.cfg'):
            open('config.cfg', 'a').close()
            sys.exit('Please, fill informations in \'config.cfg\'. See\
 \'config_example.cfg\' as an example')
        config = ConfigParser.RawConfigParser()
        config.read('config.cfg')

        # Read zones data
        zonesData = []
        for name in config.sections():
            adminlevel = config.get(name, 'admin_level')
            boundaries = config.get(name, 'boundaries')
            shapeFile = config.get(name, 'lines')
            for (fileType, filePath) in (("Boundaries", boundaries),
                                         ("Local council", shapeFile)):
                if not os.path.isfile(filePath):
                    sys.exit("%s shapefile file is imissing:\n%s" % (fileType,
                                                                     filePath))
            boundaries = boundaries[:-4]
            shapeFile = shapeFile[:-4]

            zonesData.append([name, adminlevel, boundaries, shapeFile])

        # Create missing directories and files
        osmdir = os.path.join("data", "OSM")
        if not os.path.exists(osmdir):
            os.makedirs(osmdir)
        if not os.path.isfile('html/data/info.js'):
            infoFile = open('html/data/info.js', "w")
            text = """
var title = 'Compare to OSM';
var mapLat = 0;
var mapLon = 0;
var mapZoom = 0;
var info = '<b>Compare to OSM</b>';
info += '<p>Modify html/data/info.js to write here';
info += '<br><br><a href="https://github.com/simone-f/\
compare-to-osm" target="_blank">Script code</a>';"""
            infoFile.write(text)
            infoFile.close()

        self.print_local_councils_data(zonesData)

        return zonesData

    def print_local_councils_data(self, zonesData):
        print "\n= Local Councils ="
        for zoneData in zonesData:
            print "name:", zoneData[0]
            print "admin_level:", zoneData[1]
            print "boundaries shapefile:", zoneData[2]
            print "highways shapefile:", zoneData[3]
            print


class Zone():
    def __init__(self, (name, adminlevel, boundaries, shapeFile)):
        self.name = name
        self.adminlevel = adminlevel
        self.boundaries = boundaries
        self.shapeFile = shapeFile

        self.osmFile = "data/OSM/%s.osm" % name
        self.database = "data/%s.sqlite" % name

        print "\n= Donwload OSM data of highway=* (!= footway != cycleway)\
 inside the local council="
        self.download_osm()

        print "\n= Create Spatialite database ="
        self.create_db()

        print "\n= Calculate differences between OSM/lc ways ="
        # Calculate differences between osm/lc ways and lc/osm buffers
        statuses = ("notinosm", "onlyinosm")
        for status in statuses:
            self.find_ways(status)

        print "\n= Export results ="
        self.export(statuses)

    def download_osm(self):
            url = 'http://overpass.osm.rambler.ru/cgi/interpreter?data=area'
            url += '[name="%s"][admin_level=%s];' % (self.name, self.adminlevel)
            url += 'way(area)["highway"]["highway"!~"footway"]["highway"!~"cycleway"];(._;>;);out meta;'
            cmd = "wget \"%s\" -O %s" % (url, self.osmFile)
            self.execute("cmd", cmd)

    def create_db(self):
        """Create a Spatialite database with OSM highways and
           and lines from local council released data.
        """
        print "- Remove data produced by previous executions of the script"
        self.execute("cmd", "rm data/OSM/li* %s" % self.database)

        print "\n- import OSM data into database"
        # Convert OSM to shp
        cmd = "ogr2ogr -f \"ESRI Shapefile\" data/OSM %s -sql \"SELECT osm_id FROM lines\" -lco SHPT=ARC" % self.osmFile
        self.execute("cmd", cmd)
        # Import OSM data
        cmd = "spatialite_tool -i -shp data/OSM/lines -d %s -t rawOsmWays -c UTF-8 -s 4326" % self.database
        self.execute("cmd", cmd)

        print "\n- import local council's boundaries"
        cmd = "spatialite_tool -i -shp %s -d %s -t boundaries -c UTF-8 -s 4326" % (self.boundaries,
                                                                                   self.database)
        self.execute("cmd", cmd)
        sql = "SELECT CreateSpatialIndex('%s', 'Geometry');" % "boundaries"
        self.execute("qry", sql)

        print "\n- extract highways in OSM that intersect local council's boundaries"
        sql = """
            CREATE TABLE osmWays_MIXED AS
            SELECT ST_Intersection(b.Geometry, w.Geometry) AS Geometry
            FROM boundaries AS b, rawOsmWays AS w;"""
        self.execute("qry", sql)

        self.multilines_to_line("osmWays_MIXED", "osmWays")

        # Import lc data
        print "\n- import local council released data"
        cmd = "spatialite_tool -i -shp %s -d %s -t archi -c CP1252 -s 4326" % (self.shapeFile, self.database)
        self.execute("cmd", cmd)

        # Create spatial indexes and buffers around osm/lc ways
        for table in ("osmWays", "archi"):

            print "\n- create spatial index of ", table
            sql = "SELECT CreateSpatialIndex('%s', 'Geometry');" % table
            self.execute("qry", sql)

            print "\n- create buffers of ", table
            sql = """
                CREATE TABLE %sBuf AS
                SELECT ST_Buffer(Geometry, 0.0001) AS Geometry
                FROM %s
                WHERE ST_Buffer(Geometry, 0.0001) NOT NULL;""" % (table,
                                                                  table)
            self.execute("qry", sql)
            sql = """
            SELECT RecoverGeometryColumn('%sBuf', 'Geometry',
              4326, 'POLYGON', 'XY');
            """ % table
            self.execute("qry", sql)
            sql = "SELECT CreateSpatialIndex('%sBuf', 'Geometry');" % table
            self.execute("qry", sql)

    def multilines_to_line(self, tableIn, tableOut):
        print "\n- convert multilinestring to linestring of tabel %s" % tableIn
        # Extract MULTILINESTRINGs
        sql = """
            CREATE TABLE %s_MULTILINESTRING AS SELECT Geometry
            FROM %s
            WHERE GeometryType(Geometry) = 'MULTILINESTRING';""" % (tableOut,
                                                       tableIn)
        self.execute("qry", sql)
        sql = """
            SELECT RecoverGeometryColumn('%s_MULTILINESTRING', 'Geometry',
                4326, 'MULTILINESTRING', 'XY');
            """ % (tableOut)
        self.execute("qry", sql)
        # Convert MULTILINESTRING to linestring and union with LINESTRINGs
        self.execute("qry", ".elemgeo %s_MULTILINESTRING Geometry %s_SINGLELINESTRING pk_elem multi_id;" % (tableOut, tableOut))
        sql = """
            CREATE TABLE %s AS
            SELECT Geometry
            FROM %s_SINGLELINESTRING
            UNION
            SELECT Geometry
            FROM %s WHERE GeometryType(Geometry) = 'LINESTRING';
            """ % (tableOut, tableOut, tableIn)
        self.execute("qry", sql)

    def find_ways(self, table):
        """Calculate differences between osm/lc ways and lc/osm buffers
        """
        if table == "notinosm":
            print "\n- Find ways in local council's data which are missing in OSM (comunali - buffer(OSM))"
            ways = "archi"
            buff = "osmWaysBuf"
        elif table == "onlyinosm":
            print "\n- Find ways in OSM which are missing in local council's data (OSM - buffer(comunali))"
            ways = "osmWays"
            buff = "archiBuf"

        sql = """
        CREATE TABLE {temptable} AS
        SELECT Geometry FROM (
            SELECT ST_Difference(way.Geometry, ST_Union(buffer.Geometry)) AS Geometry
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

    def export(self, statuses):
        """Export results:
           Spatialite --> GeoJSON --> TopoJSON for Leaflet
        """
        geojsonFiles = ["html/%s_%s.GeoJSON" % (self.name, status) for status in statuses]
        self.remove_geojson_files(geojsonFiles)
        for i, status in enumerate(statuses):
            cmd = "ogr2ogr -f \"GeoJSON\" \"%s\" %s -sql \"SELECT Geometry FROM %s\"" % (geojsonFiles[i], self.database, status)
            self.execute("cmd", cmd)

        cmd = "topojson -q 10000000 -o html/%s.GeoJSON %s" % (self.name,
                                                 " ".join(geojsonFiles))
        self.execute("cmd", cmd)

        self.remove_geojson_files(geojsonFiles)

    def remove_geojson_files(self, fileNames):
        for fileName in fileNames:
            if os.path.exists(fileName):
                self.execute("cmd", "rm %s" % fileName)


    def execute(self, mode, cmd):
        """mode == cmd OR qry
        """
        if mode == "qry":
            cmd = "echo \"%s\" | spatialite %s" % (cmd, self.database)
        print cmd
        call(cmd, shell=True)


if __name__ == "__main__":
    app = App()
