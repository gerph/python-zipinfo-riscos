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


# Constants
BASEDATE = (1980, 1, 1, 0, 0, 0)
RISCOS_BASEDATE = (1980, 1, 1, 0, 0, 0, 0)
LOADADDR_BASEDATE = 0xfffffd3a
EXECADDR_BASEDATE = 0xc7524200

TESTDATE = (2020, 5, 5, 12, 24, 56)
LOADADDR_TESTDATE = 0xfffffd58
EXECADDR_TESTDATE = 0x6be0ff60

FILETYPE_TEXT = 0xFFF
FILETYPE_DATA = 0xFFD
FILETYPE_SPRITE = 0xFF9
FILETYPE_ZIP = 0xA91

OBJTYPE_FILE = 1
OBJTYPE_DIRECTORY = 2

ATTR_RW = 0x33


# Ensure that the Coverage module is configured to instrument the package we
# care about (and to play nice with other people)
if os.environ.get('NOSE_WITH_COVERAGE') or '--with-coverage' in sys.argv:
    package = os.environ.get('NOSE_COVER_PACKAGE', '').split(',')
    package = set(pkg for pkg in package if pkg != '')
    package.add('rozipinfo')
    os.environ['NOSE_COVER_PACKAGE'] = ",".join(sorted(package))


def build_loadexec(loadaddr, execaddr, filetype=None):
    if filetype is not None:
        loadaddr = (loadaddr & 0xFFF000FF) | filetype << 8
    return (loadaddr, execaddr)


class BaseTestCase(unittest.TestCase):

    longMessage = True

    def checkRISCOS(self, zi, filename=None, loadexec=None, filetype=None, objtype=None, attr=None, date_time=None):
        if filename is not None:
            self.assertEqual(zi.riscos_filename, filename)

        if filetype is not None:
            self.assertEqual(hex(zi.riscos_filetype), hex(filetype))

        if loadexec is not None:
            self.assertEqual((hex(zi.riscos_loadaddr), hex(zi.riscos_execaddr)), (hex(loadexec[0]), hex(loadexec[1])))

        if attr is not None:
            self.assertEqual(zi.riscos_attr, attr)
            self.assertEqual(zi.riscos_attr, attr)

        if objtype is not None:
            self.assertEqual(zi.riscos_objtype, objtype)

        if date_time is not None:
            self.assertEqual(zi.riscos_date_time, date_time)


class Test01Import(BaseTestCase):

    def test_000_import(self):
        global rozipinfo  # pylint: disable=global-statement
        import rozipinfo as rozipinfo  # pylint: disable=redefined-outer-name


class Test10ConstructOriginalFeatures(BaseTestCase):

    def test_001_empty(self):
        # Check that it works as when given nothing
        original = zipfile.ZipInfo()
        zi = rozipinfo.ZipInfoRISCOS()
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)
        self.assertEqual(zi.internal_attr, original.internal_attr)
        self.assertEqual(zi.external_attr, original.external_attr)

    def test_002_filename(self):
        # Check that it works when given a filename
        original = zipfile.ZipInfo(filename='myfile')
        zi = rozipinfo.ZipInfoRISCOS(filename='myfile')
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)
        self.assertEqual(zi.internal_attr, original.internal_attr)
        self.assertEqual(zi.external_attr, original.external_attr)

    def test_003_datetime(self):
        # Check that it works when given a datetime
        original = zipfile.ZipInfo(date_time=TESTDATE)
        zi = rozipinfo.ZipInfoRISCOS(date_time=TESTDATE)
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)
        self.assertEqual(zi.internal_attr, original.internal_attr)
        self.assertEqual(zi.external_attr, original.external_attr)

    def test_004_zipinfo(self):
        # Check that it works when given a zipinfo
        original = zipfile.ZipInfo(filename='myfile', date_time=TESTDATE)
        zi = rozipinfo.ZipInfoRISCOS(zipinfo=original)
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)
        self.assertEqual(zi.internal_attr, original.internal_attr)
        self.assertEqual(zi.external_attr, original.external_attr)

    def test_010_directory(self):
        # Check that it works when given a filename
        original = zipfile.ZipInfo(filename='directory/')
        zi = rozipinfo.ZipInfoRISCOS(filename='directory/')
        self.assertIsNotNone(zi)
        self.assertEqual(zi.filename, original.filename)
        self.assertEqual(zi.date_time, original.date_time)
        self.assertEqual(zi.extra, original.extra)
        self.assertEqual(zi.comment, original.comment)
        self.assertEqual(zi.internal_attr, original.internal_attr)
        self.assertEqual(zi.external_attr, original.external_attr)


class Test11ConstructRISCOSFeatures(BaseTestCase):

    def test_001_empty(self):
        # Check that it works as when given nothing
        original = zipfile.ZipInfo()
        zi = rozipinfo.ZipInfoRISCOS()
        self.assertIsNotNone(zi)
        self.checkRISCOS(zi,
                         filename=original.filename,
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_002_filename(self):
        # Check that it works when given a filename
        original = zipfile.ZipInfo(filename='myfile')
        zi = rozipinfo.ZipInfoRISCOS(filename='myfile')
        self.checkRISCOS(zi,
                         filename=original.filename,
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_003_datetime(self):
        # Check that it works when given a datetime
        original = zipfile.ZipInfo(date_time=TESTDATE)
        zi = rozipinfo.ZipInfoRISCOS(date_time=TESTDATE)
        self.checkRISCOS(zi,
                         filename=original.filename,
                         loadexec=build_loadexec(LOADADDR_TESTDATE, EXECADDR_TESTDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_004_zipinfo(self):
        # Check that it works when given a zipinfo
        original = zipfile.ZipInfo(filename='myfile', date_time=TESTDATE)
        zi = rozipinfo.ZipInfoRISCOS(zipinfo=original)
        self.checkRISCOS(zi,
                         filename=original.filename,
                         loadexec=build_loadexec(LOADADDR_TESTDATE, EXECADDR_TESTDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_010_directory(self):
        # Check that it works when given a filename
        original = zipfile.ZipInfo(filename='directory/')
        zi = rozipinfo.ZipInfoRISCOS(filename='directory/')
        self.checkRISCOS(zi,
                         filename='directory',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)


class Test20FilenamePathFiletype(BaseTestCase):
    """
    Effects of changing the filename.
    """

    def test_001_extension_mapping_zip(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='file.zip')
        self.checkRISCOS(zi,
                         filename='file/zip',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_ZIP),
                         filetype=FILETYPE_ZIP,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_002_extension_mapping_txt(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='file.txt')
        self.checkRISCOS(zi,
                         filename='file/txt',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_050_directory_mapping_c(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/source')
        self.checkRISCOS(zi,
                         filename='c.source',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_051_directory_mapping_c_subdir(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='myapp/c/source')
        self.checkRISCOS(zi,
                         filename='myapp.c.source',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_052_directory_mapping_s(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='s/assembly')
        self.checkRISCOS(zi,
                         filename='s.assembly',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_053_directory_mapping_s_deep(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='this/that/myapp/s/assembly')
        self.checkRISCOS(zi,
                         filename='this.that.myapp.s.assembly',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_060_directory_mapping_not_s(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='nots/assembly')
        self.checkRISCOS(zi,
                         filename='nots.assembly',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DATA),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)


class Test21FilenameNFSEncoding(BaseTestCase):
    """
    Using the NFS Encoding to set filetypes and load/exec
    """

    def test_001_filetype_suffix(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='file,ff9')
        self.assertEqual(zi.filename, 'file,ff9')
        self.checkRISCOS(zi,
                         filename='file',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_SPRITE),
                         filetype=FILETYPE_SPRITE,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_002_filetype_suffix_invalid(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='file,fft')
        self.assertEqual(zi.filename, 'file,fft')
        self.checkRISCOS(zi,
                         filename='file,fft',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DATA),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_003_filetype_suffix_before_pathname(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/file,ff9')
        self.assertEqual(zi.filename, 'c/file,ff9')
        self.checkRISCOS(zi,
                         filename='c.file',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_SPRITE),
                         filetype=FILETYPE_SPRITE,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_004_loadexec_suffix(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/file,fffff93a,c7524201') # Note intentional + 1 to check it's real
        self.assertEqual(zi.filename, 'c/file,fffff93a,c7524201')
        self.checkRISCOS(zi,
                         filename='c.file',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE + 1, filetype=FILETYPE_SPRITE),
                         filetype=FILETYPE_SPRITE,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_005_loadexec_suffix_untyped(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/file,12345678,87654321')
        self.assertEqual(zi.filename, 'c/file,12345678,87654321')
        self.checkRISCOS(zi,
                         filename='c.file',
                         loadexec=build_loadexec(0x12345678, 0x87654321),
                         filetype=-1,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)


if __name__ == '__main__':
    __name__ = os.path.basename(sys.argv[0][:-3])  # pylint: disable=redefined-builtin
    env = os.environ
    env['NOSE_WITH_XUNIT'] = '1'
    env['NOSE_VERBOSE'] = '1'
    exit(nose.runmodule(env=env))
