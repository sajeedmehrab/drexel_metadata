import math
import json
import re
import sys
import os
from torch.multiprocessing import Pool
import pandas as pd
import numpy as np
import nrrd
from PIL import Image
from functools import partial
import matplotlib.pyplot as plt
import pprint
from copy import copy
from random import shuffle

import torch

import pycocotools
import detectron2.structures as structures
import detectron2.data.datasets.coco as coco
from detectron2.data.datasets import register_coco_instances
from detectron2.data import DatasetCatalog, MetadataCatalog,\
        build_detection_train_loader,\
        build_detection_test_loader
from detectron2.engine.defaults import DefaultTrainer,\
        default_argument_parser
from detectron2.engine import launch
import detectron2.data.transforms as T
from detectron2.data import DatasetMapper
from detectron2.config import get_cfg
from detectron2.checkpoint import DetectionCheckpointer
from detectron2.modeling import build_model
from detectron2.engine import DefaultPredictor
from detectron2.data import Metadata
from detectron2.utils.visualizer import Visualizer

import cv2

from skimage import filters
from skimage.morphology import flood_fill

import pytesseract as tess
import enchant

def init_model():
    cfg = get_cfg()
    cfg.merge_from_file("config/mask_rcnn_R_50_FPN_3x.yaml")
    # NOTE THIS SETTING
    # was 5 when I trained current model so has to stay 5 unless retrained
    cfg.MODEL.ROI_HEADS.NUM_CLASSES = 5
    cfg.MODEL.WEIGHTS = os.path.join(cfg.OUTPUT_DIR, "model_final.pth")
    cfg.MODEL.ROI_HEADS.SCORE_THRESH_TEST = 0.3
    predictor = DefaultPredictor(cfg)
    return predictor

def gen_metadata(names, file_plus_name):
    file_path, sci_name = file_plus_name
    sci_name = sci_name.lower()
    predictor = init_model()
    im = cv2.imread(file_path)
    metadata = Metadata(evaluator_type='coco', image_root='.',
            json_file='',
            name='metadata',
            thing_classes=['label'],
            thing_dataset_id_to_contiguous_id=
                {1: 0}
            )
    output = predictor(im)
    insts = output['instances']
    label = insts[0]

    visualizer = Visualizer(im[:, :, ::-1], metadata=metadata, scale=1.0)
    vis = visualizer.draw_instance_predictions(insts.to('cpu'))
    os.makedirs('images', exist_ok=True)
    file_name = file_path.split('/')[-1]
    print(f'{file_name}: {sci_name}')#\n-------------')
    cv2.imwrite(f'images/check_labels_prediction_{file_name}.png',
            vis.get_image()[:, :, ::-1])
    bbox = [round(x) for x in label.pred_boxes.tensor.cpu().
            numpy().astype('float64')[0]]
    im_crop = im[bbox[1]:bbox[3],bbox[0]:bbox[2],...]
    text = tess.image_to_string(Image.fromarray(im_crop)).lower()
    #print(text)
    result = sci_name in text
    #print(f'Matches metadata exactly: {result}')
    if not result:
        lines = [re.sub(r"[^A-Za-z ]+", '', i).strip() for i in text.split('\n') if i]
        lines = [i for i in lines if len(i) > 9]
        min_dist = math.inf
        min_name = sci_name
        min_line = ''
        for line in lines:
            curr_dist = enchant.utils.levenshtein(sci_name, line)
            if curr_dist < min_dist and curr_dist <= int(.75 * len(line)):
                min_dist = curr_dist
                min_line = line
        result = min_dist < 2
        #print(f'Off by one character: {result}')
        if not result:
            for name in names:
                for line in lines:
                    curr_dist = enchant.utils.levenshtein(line, name.lower())
                    if curr_dist < min_dist and curr_dist <= int(.5 * len(line)):
                        min_name = name.lower()
                        min_dist = curr_dist
                        min_line = line
            if min_name == sci_name:
                result = True
    else:
        min_dist = 0
        min_name = sci_name
        min_line = sci_name
    #print(min_dist)
    #print(min_name)
    #exit(0)
    return {file_name: {'matched_metadata': result, 'name_in_tag': min_line,
        'best_name': min_name, 'lev_dist': min_dist, 'metadata_name': sci_name}}

def gen_metadata_safe(file_plus_name):
    try:
        return gen_metadata(file_plus_name)
    except Exception as e:
        print(f'{file_path}: Errored out ({e})')
        return {file_path: {'errored': True}}


def main():
    direct = sys.argv[1]
    if os.path.isdir(direct):
        files = [entry.path for entry in os.scandir(direct)]
        if len(sys.argv) > 2:
            files = files[:int(sys.argv[2])]
    else:
        files = [direct]
    csv_df = pd.read_csv('datasets/image_metadata.csv')
    files_names = [
            (file, csv_df[csv_df['oldFileName']==
                file.split('/')[-1]]['ScientificName'].item())
            for file in files]
    #pprint.pprint(files_names)
    #exit(0)
    names = [i.strip() for i in csv_df['ScientificName'].unique() if ' ' in i.strip()]
    f = partial(gen_metadata, names)
    with Pool(4) as p:
        results = p.map(f, files_names)
        #results = p.map(gen_metadata_safe, files_names)
    #results = map(gen_metadata, files)
    output = {}
    for i in results:
        output[list(i.keys())[0]] = list(i.values())[0]
    #print(output)
    if len(output) > 1:
        with open('check_labels.json', 'w') as f:
            json.dump(output, f)
    else:
        pprint.pprint(output)

if __name__ == '__main__':
    #gen_metadata(sys.argv[1])
    main()
