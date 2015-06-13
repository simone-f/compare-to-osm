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
import ConfigParser
import argparse
from zone import Zone


class App():
    def __init__(self):

        # Options
        text = ("The program compares the geometries of highways in OSM with"
                " those in one or more shapefiles. It generates GeoJSON and"
                " shapefiles with highways missing in OSM and in the open"
                " data. The results are shown on a leaflet map as topojson"
                " or PNG tiles.")
        parser = argparse.ArgumentParser(description=text)
        parser.add_argument("-p", "--print_zones_configuration",
                            help="print zones'configuration and exit",
                            action="store_true")

        parser.add_argument("-a", "--analyse",
                            help=("download OSM data, compare with open data"
                                  " and produce output files"),
                            action="store_true")

        parser.add_argument("-e", "--update_map",
                            help=("read analysis'output files and"
                                  " update map's data"),
                            action="store_true")

        parser.add_argument("-z", "--zones",
                            help=("consider only the zones whose name is in"
                                  " this list and ignore other zones"
                                  " in config.cfg"),
                            nargs="+")

        parser.add_argument("--offline",
                            help="do not download data from OSM;"
                                 " use the data downloaded in previous run",
                            action="store_true")

        start = time.time()

        self.args = parser.parse_args()

        if len(sys.argv) == 1:
            parser.print_help()
            sys.exit(1)

        # Configuration
        print "= Read config.cfg file ="
        zones_config = self.read_config()
        # Analyse only specified zones (--zones option)
        if self.args.zones:
            for zone_name in self.args.zones:
                if zone_name not in zones_config:
                    sys.exit("\n* Error: config.cfg does not contain a zone"
                             "with this name: %s" % zone_name)

        self.print_zones(zones_config)
        if self.args.print_zones_configuration:
            sys.exit()

        if not (self.args.analyse or self.args.update_map):
            sys.exit("\nThere is nothing left for me to tell you.")

        self.zones = []
        for name, zone_config in zones_config.iteritems():
            if self.args.zones is None or (self.args.zones is not None
               and name in self.args.zones):
                print "\n= %s =" % name
                zone = Zone(self, name, zone_config)
                if self.args.analyse:
                    # Download OSM data, compare with open data
                    # and produce output files
                    zone.analyse()
                self.zones.append(zone)

        if self.args.update_map:
            print "\n= Update map data ="
            for zone in self.zones:
                zone.update_map_data()
            # Create js file with list of zones
            self.create_zonesinfo_js()

        end = time.time()
        print "Execution time: ", end - start, "seconds."

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
            sys.exit("\n* Please, add informations to 'config.cfg'. See"
                     "'config_example.cfg' as an example.")
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
                                           ("Zone", shapefile)):
                if not os.path.isfile(file_path):
                    sys.exit("%s shapefile file is missing:\n%s" % (file_type,
                                                                    file_path))
            zones_config[name]["boundaries"] = boundaries[:-4]
            zones_config[name]["shapefile"] = shapefile[:-4]
            zones_config[name]["output"] = config.get(name, 'output')
            if not config.has_option(name, 'min_zoom'):
                zones_config[name]["min_zoom"] = 5
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

        return zones_config

    def print_zones(self, zones_config):
        print "\n= Zones ="
        for name, zone_config in zones_config.iteritems():
            if self.args.zones is None or (self.args.zones is not None
               and name in self.args.zones):
                print "\nname:", name
                print "admin_level:", zone_config["admin_level"]
                print "boundaries shapefile:", zone_config["boundaries"]
                print "highways shapefile:", zone_config["shapefile"]
                print "output:", zone_config["output"]


if __name__ == "__main__":
    app = App()
