import pickle
from transformers import AutoFeatureExtractor, MaskFormerForInstanceSegmentation, AutoImageProcessor
from PIL import Image
import numpy as np
import torch
import pickle
import sys
import os

# read first sys argument as image path
fn = sys.argv[1]
with open(fn, "rb") as f:
    image = pickle.load(f)


extractor = AutoFeatureExtractor.from_pretrained("thiagohersan/maskformer-satellite-trees", use_auth_token=True)
model = MaskFormerForInstanceSegmentation.from_pretrained("thiagohersan/maskformer-satellite-trees")

inputs = extractor(images=image, return_tensors="pt")
outputs = model(**inputs)

class_queries_logits = outputs.class_queries_logits
masks_queries_logits = outputs.masks_queries_logits

predicted_mask = extractor.post_process_semantic_segmentation(
    outputs, target_sizes=[image.size[::-1]]
)[0]

# extract the number from the filename
num = int(fn.split("_")[-1].split(".")[0])


np.save(f"temp_masks/mask_{num}.npy", predicted_mask)
