from coolroutes import terrain, geometry, tier
import time

def main():
    times = []
    times.append(time.time())

    # terrain.save_geotiff()
    # times.append(time.time())
    # print(f"Terrain data loaded in {int(times[-1]-times[-2])} seconds.")

    # geometry.Buildings().load_osm().save_geojson()
    # times.append(time.time())
    # print(f"Buildings data loaded in {int(times[-1]-times[-2])} seconds.")

    # geometry.Trees().load_municipality_dataset().save_geojson()
    # times.append(time.time())
    # print(f"Terrain data loaded in {int(times[-1]-times[-2])} seconds.")

    # geometry.Network().load_osm().save_geojson()
    # times.append(time.time())
    # print(f"Terrain data loaded in {int(times[-1]-times[-2])} seconds.")

    tier.save_rides()
    times.append(time.time())
    print(f"Rides data loaded in {int(times[-1]-times[-2])} seconds.")

if __name__ == "__main__":
    main()
