#!/usr/bin/env python

from os import walk, path

import os
from setuptools import setup, find_packages, Command
import subprocess
import sys


LONG_DESCRIPTION = 'Extends Orange to handle spectral and hyperspectral analysis (transitional package to Orange-Spectroscopy).'

KEYWORDS = [
    # [PyPi](https://pypi.python.org) packages with keyword "orange3 add-on"
    # can be installed using the Orange Add-on Manager
    'orange3 add-on',
    'spectroscopy',
    'infrared'
]


if __name__ == '__main__':
    
    setup(
        name="Orange-Infrared",
        description='Extends Orange to handle spectral and hyperspectral analysis (transitional package to Orange-Spectroscopy).',
        long_description=LONG_DESCRIPTION,
        author='Canadian Light Source, Biolab UL, Soleil, Elettra',
        author_email='marko.toplak@gmail.com',
        version="0.3.3",
        package_data={},
        install_requires=[
            'Orange-Spectroscopy',
        ],
        keywords=KEYWORDS,
        include_package_data=True,
        zip_safe=False,
        url="https://github.com/markotoplak/orange-infrared",
    )
