
import os
import requests
import numpy as np
import threading
import json
import re
import cv2
from datetime import datetime

def download_tile(url, headers, channels):
    response = requests.get(url, headers=headers)
    arr =  np.asarray(bytearray(response.content), dtype=np.uint8)

    if channels == 3:
        return cv2.imdecode(arr, 1)
    return cv2.imdecode(arr, -1)


def project_with_scale(lat, lon, scale):
    siny = np.sin(lat * np.pi / 180)
    siny = min(max(siny, -0.9999), 0.9999)
    x = scale * (0.5 + lon / 360)
    y = scale * (0.5 - np.log((1 + siny) / (1 - siny)) / (4 * np.pi))
    return x, y


def download_image(lat1: float, lon1: float, lat2: float, lon2: float,
                   zoom: int, url: str, headers: dict, tile_size: int = 256, channels: str = 3) -> np.ndarray:
    scale = 1 << zoom

    # Find the pixel coordinates and tile coordinates of the corners
    tl_proj_x, tl_proj_y = project_with_scale(lat1, lon1, scale)
    br_proj_x, br_proj_y = project_with_scale(lat2, lon2, scale)

    tl_pixel_x = int(tl_proj_x * tile_size)
    tl_pixel_y = int(tl_proj_y * tile_size)
    br_pixel_x = int(br_proj_x * tile_size)
    br_pixel_y = int(br_proj_y * tile_size)

    tl_tile_x = int(tl_proj_x)
    tl_tile_y = int(tl_proj_y)
    br_tile_x = int(br_proj_x)
    br_tile_y = int(br_proj_y)

    img_w = abs(tl_pixel_x - br_pixel_x)
    img_h = br_pixel_y - tl_pixel_y
    img = np.ndarray((img_h, img_w, channels), np.uint8)

    def build_row(row_number):
        for j in range(tl_tile_x, br_tile_x + 1):
            tile = download_tile(url.format(x=j, y=row_number, z=zoom), headers, channels)

            # Find the pixel coordinates of the new tile relative to the image
            tl_rel_x = j * tile_size - tl_pixel_x
            tl_rel_y = row_number * tile_size - tl_pixel_y
            br_rel_x = tl_rel_x + tile_size
            br_rel_y = tl_rel_y + tile_size

            # Define where the tile will be placed on the image
            i_x_l = max(0, tl_rel_x)
            i_x_r = min(img_w + 1, br_rel_x)
            i_y_l = max(0, tl_rel_y)
            i_y_r = min(img_h + 1, br_rel_y)

            # Define how border tiles are cropped
            cr_x_l = max(0, -tl_rel_x)
            cr_x_r = tile_size + min(0, img_w - br_rel_x)
            cr_y_l = max(0, -tl_rel_y)
            cr_y_r = tile_size + min(0, img_h - br_rel_y)

            img[i_y_l:i_y_r, i_x_l:i_x_r] = tile[cr_y_l:cr_y_r, cr_x_l:cr_x_r]

    threads = []
    for i in range(tl_tile_y, br_tile_y + 1):
        thread = threading.Thread(target=build_row, args=[i])
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    return img


def image_size(lat1: float, lon1: float, lat2: float,
               lon2: float, zoom: int, tile_size: int = 256):
    """ Calculates the size of an image without downloading it. Returns a `(width, height)` tuple. """

    scale = 1 << zoom
    tl_proj_x, tl_proj_y = project_with_scale(lat1, lon1, scale)
    br_proj_x, br_proj_y = project_with_scale(lat2, lon2, scale)

    tl_pixel_x = int(tl_proj_x * tile_size)
    tl_pixel_y = int(tl_proj_y * tile_size)
    br_pixel_x = int(br_proj_x * tile_size)
    br_pixel_y = int(br_proj_y * tile_size)

    return abs(tl_pixel_x - br_pixel_x), br_pixel_y - tl_pixel_y


def take_input(messages):
    inputs = []
    print('Enter "r" to reset or "q" to exit.')
    for message in messages:
        inp = input(message)
        if inp == 'q' or inp == 'Q':
            return None
        if inp == 'r' or inp == 'R':
            return take_input(messages)
        inputs.append(inp)
    return inputs


def get_tile(bounds:[tuple], zoom:int=19, output_dir:str="./images") -> str:
    """
    Downloads a satellite image of the given bounds and saves it to the given directory.

    :bounds: A list of tuples containing the top-left and bottom-right coordinates of the image.
    CRS: WGS84
    """

    # Check if output directory exists
    if not os.path.isdir(os.path.dirname(output_dir)):
        os.makedirs(os.path.dirname(output_dir))

    lat1, lon1 = bounds[0]
    lat2, lon2 = bounds[1]

    # zoom = int(prefs['zoom'])
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
    channels = 3
    url = "https://mt.google.com/vt/lyrs=s&x={x}&y={y}&z={z}"

    headers = {
        "cache-control": "max-age=0",
        "sec-ch-ua": "\" Not A;Brand\";v=\"99\", \"Chromium\";v=\"99\", \"Google Chrome\";v=\"99\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.82 Safari/537.36"
    }

    img = download_image(lat1, lon1, lat2, lon2, zoom, url,
                         headers, 256, channels)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    name = f'tile_{int(lat1*1000)}_{int(lon1*1000)}_{int(lat2*1000)}_{int(lon2*1000)}.png'
    path = os.path.join(output_dir, name)
    cv2.imwrite(path, img)
    print(f'Saved as {name}')
    return path 


