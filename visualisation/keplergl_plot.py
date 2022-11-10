
from keplergl import KeplerGl
import json

# --------------------------------------------------------
# [TEMP] Copenhagen: reference locations
# --------------------------------------------------------

# København (Axel Towers)
axel_towers = Point(12.565886448579562, 55.675641285999056)

# København (SAS Radison)
sas_radison = Point(12.563763249599585, 55.675006335236190)

# --------------------------------------------------------
# Interactive map (using Kepler.gl)
# --------------------------------------------------------

cph_map = KeplerGl()

with open('./visualisation/keplergl_config.json') as f:
    config = json.load(f)

_buildings = buildings.copy()
_shadows = shadows.copy()
_tree = trees_small.copy()
_tree_shadows = tree_shadows.copy()
cph_map.add_data(data=_buildings, name='Buildings')
cph_map.add_data(data=_shadows, name='Shadows')
cph_map.add_data(data=_tree, name='Trees')
cph_map.add_data(data=_tree_shadows, name='Tree shadows')
cph_map.config = config
cph_map.save_to_html(file_name='cph_buildings.html')
