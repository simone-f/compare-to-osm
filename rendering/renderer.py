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

import mapnik
from generate_tiles import render_tiles
import os
import jinja2


class Renderer:
    def __init__(self, task, status, shapefile, geometry_type):
        self.task = task
        stylesheet_template = "style_%s.xml" % geometry_type
        self.stylesheet = os.path.join(task.app.directory,
                                       "rendering",
                                       "style_%s.xml" % geometry_type)

        self.image = os.path.join(str(task.map_data_dir_png),
                                  '%s.png' % status)
        self.tiles_dir = os.path.join(self.task.map_data_dir_tiles,
                                      status) + "/"
        os.makedirs(self.tiles_dir)

        # Generate Mapnik style
        template_loader = jinja2.FileSystemLoader(os.path.join(
            task.app.directory, "rendering", "templates"))
        template_env = jinja2.Environment(loader=template_loader)
        template = template_env.get_template(stylesheet_template)
        template_vars = {"status": status,
                         "shapefile": shapefile}
        output_text = template.render(template_vars)
        style_file = open(self.stylesheet, "w")
        style_file.write(output_text)
        style_file.close()

        # Generate PNG image
        self.generate_img()

        # Generate tiles
        self.execute_generate_tiles()

    def generate_img(self):
        print "\n- Render image"
        m = mapnik.Map(600, 300)
        mapnik.load_map(m, self.stylesheet)
        m.zoom_all()
        mapnik.render_to_file(m, self.image)
        print "rendered image to '%s'" % self.image

    def execute_generate_tiles(self):
        print "\n- Render tiles"

        # Render
        print self.task.bbox, self.task.database
        render_tiles(self.task.bbox, self.stylesheet,
                     str(self.tiles_dir), self.task.min_zoom,
                     self.task.max_zoom)

        # Delete empty folders
        self.remove_empty_directories(self.tiles_dir)
        print "Empty directories deleted."

    def remove_empty_directories(self, path):
        # Credit: http://dev.enekoalonso.com/2011/
        # 08/06/python-script-remove-empty-folders/
        if not os.path.isdir(path):
            return

        # remove empty subfolders
        files = os.listdir(path)
        if len(files):
            for f in files:
                fullpath = os.path.join(path, f)
                if os.path.isdir(fullpath):
                    self.remove_empty_directories(fullpath)

        # if folder empty, delete it
        files = os.listdir(path)
        if len(files) == 0:
            # print "Removing empty folder:", path
            os.rmdir(path)


if __name__ == "__main__":
    renderer = Renderer()
