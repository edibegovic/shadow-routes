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

## TODO
# Import external config (json)
config = {
    "version": "v1",
    "config": {
        "mapState": {
            "latitude": axel_towers.y,
            "longitude": axel_towers.x,
            "zoom": 14.5,
            "dragRotate": True,
        },
         "mapStyle": {
            "styleType": "satellite",
        },
        'visState': {'filters': [],
            'layers': [{
                'id': '348zwa8',
                'type': 'geojson',
                'config': {
                    'dataId': 'Buildings',
                    'label': 'Buildings',
                    'columns': {'geojson': 'geometry'},
                    'isVisible': True,
                    'visConfig': {
                        'elevationScale': 0.07,
                        'filled': True,
                        'enable3d': True,
                        'wireframe': True
                    },
                    'hidden': False,
                },
                'visualChannels': {
                    'heightField': {'name': 'height', 'type': 'real'},
                    'heightScale': 'linear',
                }
            }, 
            {
                'id': '448ksi9',
                'type': 'geojson',
                'config': {
                    'dataId': 'Shadows',
                    'label': 'Shadows',
                    'color': [30, 30, 30],
                    'columns': {'geojson': 'geometry'},
                    'isVisible': True,
                    'visConfig': {
                        'filled': True,
                        'stroked': False,
                    },
                    'hidden': False,
                },
            }],
        },
    }
}

_buildings = buildings.copy()
_shadows = shadows.copy()
cph_map.add_data(data=_buildings, name='Buildings')
cph_map.add_data(data=_shadows, name='Shadows')
cph_map.config = config
cph_map.save_to_html(file_name='cph_buildings.html')
