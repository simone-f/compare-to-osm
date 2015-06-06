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
from zone import Zone


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
                                           ("Zone", shapefile)):
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
        print "\n= Zones ="
        for name, zone_config in zones_config.iteritems():
            print "name:", name
            print "admin_level:", zone_config["admin_level"]
            print "boundaries shapefile:", zone_config["boundaries"]
            print "highways shapefile:", zone_config["shapefile"]
            print "output:", zone_config["output"]
            print


if __name__ == "__main__":
    app = App()
