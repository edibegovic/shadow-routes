from keplergl import KeplerGl
import json

def add_data(_map: KeplerGl, sources):
    """
    This is due to a bug in the latest version on KeplerGL that 
    directly modifies the contents of a provided GeoDataFrame.
    To circumvent this, we instaed provide a copy of the original 
    data source.
    """
    for gdf, name in sources:
        _map.add_data(gdf.copy(), name=name)

def create_html(data_sources):
    cph_map = KeplerGl()

    with open('./visualisation/keplergl_config.json') as f:
        config = json.load(f)

    add_data(cph_map, data_sources)
    cph_map.config = config
    cph_map.save_to_html(file_name='cph_buildings.html')