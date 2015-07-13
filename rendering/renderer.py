#! /usr/bin/python
import mapnik
from generate_tiles import render_tiles
import os
import jinja2


class Renderer:
    def __init__(self, zone, status, shapefile, geometry_type):
        self.zone = zone
        stylesheet_template = ('rendering/templates/'
                               'style_%s.xml') % geometry_type
        self.stylesheet = 'rendering/style_%s.xml' % geometry_type

        self.image = os.path.join(zone.map_data_dir_png, '%s.png' % (
                                  status))
        self.tiles_dir = os.path.join(self.zone.map_data_dir_tiles,
                                      status) + "/"
        os.makedirs(self.tiles_dir)

        # Generate Mapnik style
        template_loader = jinja2.FileSystemLoader(searchpath="./")
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
        render_tiles(self.zone.bbox, self.stylesheet,
                     self.tiles_dir, self.zone.min_zoom,
                     self.zone.max_zoom)

        # Delete empty folders
        self.remove_empty_directories(self.tiles_dir)
        print "Empty directories deleted."

        # Optimize pngs
        # call(("find . -name \"%s*.png\""
        #      " -exec optipng {} \;") % self.zone.tiles_directory,
        #                                shell=True)

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
