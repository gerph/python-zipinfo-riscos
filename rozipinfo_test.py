#!/usr/bin/env python
"""
Test that the RISC OS ZipInfo object works properly.

SUT:    rozipinfo
Area:   API
Class:  Functional
Type:   Unit test
"""

# pylint: disable=no-self-use

import os
import sys
import unittest
import zipfile

import nose


rozipinfo = None


# Ensure that the Coverage module is configured to instrument the package we
# care about (and to play nice with other people)
if os.environ.get('NOSE_WITH_COVERAGE') or '--with-coverage' in sys.argv:
    package = os.environ.get('NOSE_COVER_PACKAGE', '').split(',')
    package = set(pkg for pkg in package if pkg != '')
    package.add('rozipinfo')
    os.environ['NOSE_COVER_PACKAGE'] = ",".join(sorted(package))


class BaseTestCase(unittest.TestCase):

    longMessage = True


class Test01Import(BaseTestCase):

    def test_000_import(self):
        global rozipinfo  # pylint: disable=global-statement
        import rozipinfo as rozipinfo  # pylint: disable=redefined-outer-name


class Test10Construct(BaseTestCase):

    def test_001_empty(self):
        # Check that it works as when given nothing
        original = zipfile.ZipInfo()
        zi = rozipinfo.ZipInfoRISCOS()
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)

    def test_002_filename(self):
        # Check that it works when given a filename
        original = zipfile.ZipInfo(filename='myfile')
        zi = rozipinfo.ZipInfoRISCOS(filename='myfile')
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)

    def test_003_datetime(self):
        # Check that it works when given a datetime
        original = zipfile.ZipInfo(date_time=(2020, 5, 5, 12, 24, 56))
        zi = rozipinfo.ZipInfoRISCOS(date_time=(2020, 5, 5, 12, 24, 56))
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)

    def test_004_zipinfo(self):
        # Check that it works when given a zipinfo
        original = zipfile.ZipInfo(filename='myfile', date_time=(2020, 5, 5, 12, 24, 56))
        zi = rozipinfo.ZipInfoRISCOS(zipinfo=original)
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)


if __name__ == '__main__':
    __name__ = os.path.basename(sys.argv[0][:-3])  # pylint: disable=redefined-builtin
    env = os.environ
    env['NOSE_WITH_XUNIT'] = '1'
    env['NOSE_VERBOSE'] = '1'
    exit(nose.runmodule(env=env))
