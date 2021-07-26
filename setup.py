#!/usr/bin/env python
"""
Packaging for the RISC OS ZipInfo and ZipFile modules.
"""

from distutils.core import setup
import setuptools  # noqa

from os import path
# io.open is needed for projects that support Python 2.7
# It ensures open() defaults to text mode with universal newlines,
# and accepts an argument to specify the text encoding
# Python 3 only projects can skip this import
from io import open

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()


setup(
    name = 'rozipinfo',
    py_modules = ['rozipfile', 'rozipinfo'],
    version = '1.0',
    license='BSD',
    description = 'Managing Zip archives with RISC OS filetype information present',
    long_description = long_description,
    long_description_content_type = 'text/markdown',
    author = 'Charles Ferguson',
    author_email = 'gerph@gerph.org',
    url = 'https://github.com/gerph/python-zipinfo-riscos',
    keywords = ['zip', 'riscos'],
    install_requires= [
        ],
    classifiers= [
            'Development Status :: 4 - Beta',
            'Intended Audience :: Developers',          # Define that your audience are developers
            'License :: OSI Approved :: BSD License',   # Again, pick a license
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            "Operating System :: OS Independent",
            "Operating System :: RISC OS",
        ],
    python_requires='>=2.7',
)
