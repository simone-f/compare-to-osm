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
import json


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

        parser.add_argument("-m", "--update_map",
                            help=("read analysis'output files and"
                                  " update map's data"),
                            action="store_true")

        parser.add_argument("-z", "--zones",
                            help=("consider only the zones whose name is in"
                                  " this list and ignore other zones"
                                  " in config.cfg"),
                            nargs="+",
                            metavar=("ZONENAME"))

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
        self.ZONESINFOFILE = "html/data/zones_info.json"
        zones_config = self.read_config()
        # Analyse only specified zones (--zones option)
        if self.args.zones:
            for zone_name in self.args.zones:
                if zone_name not in zones_config:
                    sys.exit("\n* Error: config.cfg does not contain a zone"
                             " with this name: %s" % zone_name)

        self.print_zones(zones_config)
        if self.args.print_zones_configuration:
            sys.exit()

        if not (self.args.analyse or self.args.update_map):
            sys.exit("\nThere is nothing left for me to tell you.")

        self.allZones = []
        self.zones = []
        for name, zone_config in zones_config.iteritems():
            zone = Zone(self, name, zone_config)
            self.allZones.append(zone)
            if not self.args.zones or name in self.args.zones:
                self.zones.append(zone)

        # Analyse
        if self.args.analyse:
            for zone in self.zones:
                print "\n= Analyse: %s =" % zone.name
                # Download OSM data, compare with open data
                # and produce output files
                zone.analyse()

        # Update map
        if self.args.update_map:
            for zone in self.zones:
                print "\n= Update map data: %s =" % zone.name
                zone.update_map_data()

        # Update JSON file with list of zones
        self.update_zones_info_file()

        end = time.time()
        print "\nExecution time: ", end - start, "seconds."

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
            # Read zones info from zones_info.json
            if not os.path.exists(self.ZONESINFOFILE):
                zones_info = {"zones": []}
            else:
                with open(self.ZONESINFOFILE, "r") as fp:
                    zones_info = json.load(fp)
            new_zone = True
            for oldzone in zones_info["zones"]:
                if oldzone["name"] == name:
                    new_zone = False
                    bbox = oldzone["bbox"]
                    center = oldzone["center"]
                    analysis_time = oldzone["analysis_time"]
                    break
            if new_zone:
                (bbox, center, analysis_time) = ("", "", "")
            zones_config[name]["bbox"] = bbox
            zones_config[name]["center"] = center
            zones_config[name]["analysis_time"] = analysis_time

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

    def update_zones_info_file(self):
        zones_info = {"zones": []}
        for zone in self.allZones:
            zones_info["zones"].append({"name": zone.name,
                                        "bbox": zone.bbox,
                                        "center": zone.center,
                                        "output": zone.output,
                                        "analysis_time": zone.analysis_time
                                        })
        with open(self.ZONESINFOFILE, "w") as fp:
            fp.write(json.dumps(zones_info,
                                sort_keys=True,
                                indent=4,
                                separators=(',', ': ')))

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
