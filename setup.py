#!/usr/bin/env python

from distutils.core import setup

setup(name='gbif_downloader',
      version='1.0',
      description='Python interface for the GBIF API, with a focus on downloading images',
      author='Callum T-C',
      author_email='email@example.com',
      url='https://github.com/callum-jpg/gbif_downloader',
      install_requires=[
        "urllib3",
        "requests",
        "pandas",
        "Pillow"
      ]
     )