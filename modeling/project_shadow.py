
import pybdshadow

date = pd.to_datetime('2022-07-01 14:45:33.95979')\
    .tz_localize('Europe/Copenhagen')\
    .tz_convert('UTC')

buildings_s = buildings.copy()
buildings_s = buildings_s.dissolve(by='osmid', aggfunc='max')
buildings_s = buildings_s.loc[buildings_s.geometry.geometry.type=='Polygon']

buildings_s['building_id'] = buildings_s.index
shadows = pybdshadow.bdshadow_sunlight(buildings_s, date)
shadows = shadows.set_crs('epsg:4326')
