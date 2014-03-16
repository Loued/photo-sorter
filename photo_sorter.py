#!/usr/bin/env python
#_*_ coding:utf-8 _*_

"""
    This module take photos in a given directory
    and sort them in another directory by date,
    based on the exif data of the photos.
"""

__author__ = 'Louis-Edouard Riedinger'
__license__ = 'WTFPL'
__date__ = '15/03/2014'
__version__ = '1.0'


import argparse
import csv
import hashlib
import locale
import logging
import os
import shutil
import sys
import time
from PIL import Image
from PIL.ExifTags import TAGS


class HashDatabase:
    """An utility class for storing hash signatures

    Each photo has its sha1 hash and filename stored in a csv file,
    wich is loaded at startup, too enable fast duplicate lookup.
    """

    def __init__(self, filename):
        self.database = {}
        self.load_database(filename)
        self.csv_writer = csv.writer(open(filename, "ab"))

    def get_file_hash(self, filename):
        # Read file by block to avoid using too much memory
        block_size = 2 ** 16  # 64k
        with open(filename, 'rb') as file:
            hash = hashlib.sha1()
            while True:
                data = file.read(block_size)
                if not data:
                    break
                hash.update(data)
            return hash.hexdigest()

    def load_database(self, file_name):
        if not os.path.exists(file_name):
            logging.warning("Hash signature file %s don't exist. Creating.", file_name)
        else:
            try:
                with open(file_name, "rb") as file:
                    reader = csv.reader(file)
                    for row in reader:
                        self.database[row[0]] = row[1]
                    logging.debug("Hash database loaded : %d elements", len(self.database))
            except Exception as ex:
                logging.error("Error while reading %s. Abording", file_name)
                logging.debug(ex)
                sys.exit(0)

    def exist(self, hash):
        return hash in self.database

    def add_hash(self, hash, file_name):
        if hash in self.database:
            logging.error("Duplicated entry : %s", file_name)
        else:
            self.database[hash] = file_name
            self.csv_writer.writerow([hash, file_name])


class PhotoSort:
    def __init__(self, argv):
        # Parse arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("-i", "--input", help="Input directory", required=True)
        parser.add_argument("-o", "--output", default="./", help="Output directory")
        parser.add_argument("-r", "--remove", action="store_true", help="Delete photos after successfull copy")
        self.args = parser.parse_args()

        if not os.path.isdir(self.args.input):
            logging.error("input %s is not a directory", self.args.input)
            sys.exit(0)

        database_file = os.path.join(self.args.output, ".database.csv")
        self.hash_db = HashDatabase(database_file)

        logging.info('Sorting photos from "%s" to "%s" using "%s" database.',
                     self.args.input, self.args.output, database_file)
        logging.info('Delete photos after copy : %s', self.args.remove)

    def get_exif_date(self, filename):
        data = {}
        i = Image.open(filename)
        info = i._getexif()
        if info is None:
            logging.info("No Exif data or file damaged : %s" % (os.path.basename(filename)))
        else:
            for tag, value in info.items():
                decoded = TAGS.get(tag, tag)
                data[decoded] = value
            try:
                # Maybe should we take DateTime or DateTimeDigitized insteed?
                # Date fields format looks like : "2008:12:11 22:47:48"
                return time.strptime(data["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S")
            except KeyError:
                logging.info("No date info in Exif for %s" % (os.path.basename(filename)))
            except Exception:
                logging.warning("Incorrect date info in Exif for %s" % (os.path.basename(filename)))

        # If exif date cannot be read, use file's last modified date
        return time.localtime(os.stat(filename).st_mtime)

    def copy_file(self, input_file, output_directory):
        try:
            # Lower the file extension
            (root, ext) = os.path.splitext(os.path.basename(input_file))
            output_file = os.path.join(output_directory, root + ext.lower())

            if os.path.exists(output_file):
                logging.error("File %s already exist !", output_file)
                return False

            # Create directory if non-existent
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)

            if self.args.remove:
                shutil.move(input_file, output_file)
            else:
                shutil.copy(input_file, output_file)
            return True
        except Exception as ex:
            logging.error("Error while copying %s to %s", input_file, output_directory)
            logging.debug(ex)
            sys.exit(0)

    def sort(self):
        count = 0
        for root, dirs, files in os.walk(self.args.input):
            for file in files:
                file_path = os.path.join(root, file)
                # Check if it is a jpeg file, by checking file extension
                extension = os.path.splitext(file)[1].lower()
                if extension != ".jpg" and extension != ".jpeg":
                    logging.debug("Ignoring %s", file_path)
                    continue

                hash = self.hash_db.get_file_hash(file_path)
                if self.hash_db.exist(hash):
                    logging.info("Duplicated photo : %s", file_path)
                    continue

                date = self.get_exif_date(file_path)
                dir_struct = "{0}/{1}/{2}".format(
                    date.tm_year,
                    time.strftime("%m-%B", date),
                    time.strftime("%d-%A", date))
                logging.debug("Copying %s to %s", file, dir_struct)
                output_directory = os.path.join(self.args.output, dir_struct)
                if self.copy_file(file_path, output_directory):
                    self.hash_db.add_hash(hash, file_path)
                    count += 1

        logging.info("Number of photos sorted : %d", count)


if __name__ == "__main__":
    logging.basicConfig(format='%(levelname)s : %(message)s')
    logging.getLogger().setLevel(logging.DEBUG)
    # Set user's preferred locale
    locale.setlocale(locale.LC_TIME, '')
    photoSort = PhotoSort(sys.argv)
    photoSort.sort()
