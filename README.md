Photo sorter
============

This simple script will allow you to sort a directory full of unordered photos into a nice date layout *year/month/day*.
It tries to extract the date by looking at the EXIF data, and fallback to the file modification attribute if that fail.

    usage: photo_sorter.py [-h] -i INPUT [-o OUTPUT] [-r]

    optional arguments:
      -i INPUT, --input INPUT
                            Input directory
      -o OUTPUT, --output OUTPUT
                            Output directory
      -r, --remove          Delete photos after successfull copy
