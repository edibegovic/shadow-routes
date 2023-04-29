from keplergl import KeplerGl
import json
import webbrowser

import os

ROOT_DIR = os.path.dirname(__file__)

class Vis(object):
    def __init__(self):
        self.kepler = KeplerGl()
        self.output_file = ROOT_DIR + '/../cph_buildings.html'

    def __add_data(self, sources):
        """
        This is due to a bug in the latest version on KeplerGL that 
        directly modifies the contents of a provided GeoDataFrame.
        To circumvent this, we instaed provide a copy of the original 
        data source.
        """
        for gdf, name in sources:
            self.kepler.add_data(gdf.copy(), name=name)

    def save_to_html(self, data_sources, output_file=None):
        with open(ROOT_DIR + '/../visualisation/keplergl_config.json') as f:
            config = json.load(f)

        self.__add_data(data_sources)
        self.kepler.config = config

        if output_file:
            self.output_file = output_file
        self.kepler.save_to_html(file_name=self.output_file)

    def display(self):
        webbrowser.open(self.output_file)
