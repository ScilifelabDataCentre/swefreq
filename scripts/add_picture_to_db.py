#!/usr/bin/env python3
import argparse
import re
import sys

import peewee

import db

class NoMimetypeException(Exception):
    pass

def infer_mimetype(image):
    if re.search(r"jpe?g$", image):
        return "image/jpeg"
    if re.search(r"png$", image):
        return "image/png"
    if re.search(r"gif$", image):
        return "image/gif"
    raise NoMimetypeException()

def add_image(dataset_pk, image):
    try:
        dataset = db.Dataset.get(db.Dataset.dataset == dataset_pk)
    except peewee.DoesNotExist:
        print("Can't find any dataset with id {}".format(dataset_pk))
        sys.exit(1)

    with open(image, 'rb') as f:
        data = f.read()

    try:
        mimetype = infer_mimetype( image )
    except NoMimetypeException:
        print("Can't find mime type for <{}>".format(image))
        sys.exit(2)

    print(len(data))
    with db.database.atomic():
        db.DatasetLogo.create(
            dataset  = dataset,
            mimetype = mimetype,
            data     = data
        )

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Insert a picture into the database')
    parser.add_argument('--file', help='The picture to add', required=True)
    parser.add_argument('--dataset', help='Dataset id', required=True)
    args = parser.parse_args()
    add_image(args.dataset, args.file)
