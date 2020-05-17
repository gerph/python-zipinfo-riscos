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
FILETYPE_DIRECTORY = 0x1000

OBJTYPE_FILE = 1
OBJTYPE_DIRECTORY = 2

ATTR_RW = 0x33
ATTR_R = 0x11
ATTR_W = 0x22

EXTRA_TEST_FILE = bytes(bytearray.fromhex('41 43 20 00 41 52 43 30 '    # Header + length + ARC0
                                          '58 fd ff ff '                # Load address
                                          '60 ff e0 6b '                # Exec address
                                          '33 00 00 00 '                # Attributes
                                          '00 00 00 00'))               # Zero


# Ensure that the Coverage module is configured to instrument the package we
# care about (and to play nice with other people)
if os.environ.get('NOSE_WITH_COVERAGE') or '--with-coverage' in sys.argv:
    package = os.environ.get('NOSE_COVER_PACKAGE', '').split(',')
    package = set(pkg for pkg in package if pkg != '')
    package.add('rozipinfo')
    os.environ['NOSE_COVER_PACKAGE'] = ",".join(sorted(package))


def build_loadexec(loadaddr, execaddr, filetype=None):
    if filetype == FILETYPE_DIRECTORY:
        filetype = FILETYPE_DATA  # That's how it's represented in load/exec
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


class Test22FilenameNFSEncodingDisabled(BaseTestCase):
    """
    WITHOUT the NFS Encoding to set filetypes and load/exec
    """

    def test_001_filetype_suffix(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='file,ff9', nfs_encoding=False)
        self.assertEqual(zi.filename, 'file,ff9')
        self.checkRISCOS(zi,
                         filename='file,ff9',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_002_filetype_suffix_invalid(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='file,fft', nfs_encoding=False)
        self.assertEqual(zi.filename, 'file,fft')
        self.checkRISCOS(zi,
                         filename='file,fft',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DATA),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_003_filetype_suffix_before_pathname(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/file,ff9', nfs_encoding=False)
        self.assertEqual(zi.filename, 'c/file,ff9')
        self.checkRISCOS(zi,
                         filename='c.file,ff9',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_004_loadexec_suffix(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/file,fffff93a,c7524201', nfs_encoding=False) # Note intentional + 1 (to match enabled case)
        self.assertEqual(zi.filename, 'c/file,fffff93a,c7524201')
        self.checkRISCOS(zi,
                         filename='c.file,fffff93a,c7524201',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_005_loadexec_suffix_untyped(self):
        zi = rozipinfo.ZipInfoRISCOS(filename='c/file,12345678,87654321', nfs_encoding=False)
        self.assertEqual(zi.filename, 'c/file,12345678,87654321')
        self.checkRISCOS(zi,
                         filename='c.file,12345678,87654321',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)


class Test40BaseProperties(BaseTestCase):
    """
    Setting base properties
    """
    # FIXME: Not yet implemted as tests

    def test_001_filename(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.filename = "another-name"
        self.checkRISCOS(zi,
                         filename='another-name',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_020_datetime(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.date_time = TESTDATE
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_TESTDATE, EXECADDR_TESTDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_040_internalattr_text(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.internal_attr |= 1
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_060_externalattr_directory(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr |= 16
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DIRECTORY,
                         objtype=OBJTYPE_DIRECTORY,
                         attr=ATTR_RW)

    def test_061_externalattr_readonly(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr |= 1
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_R)

    def test_062_externalattr_unixattr_r_r_r_(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o444 << 16  # r--r--r--
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_R)

    def test_063_externalattr_unixattr__w_w_w(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o222 << 16  # -w--w--w-
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_W)

    def test_064_externalattr_unixattr_rwrwrw(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o666 << 16  # rw-rw-rw-
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_065_externalattr_unixattr_r_____(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o400 << 16  # r--------
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_R)


class Test60RISCOSProperties(BaseTestCase):
    """
    Set RISC OS properties
    """

    def test_001_filename(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_filename = "myfile"
        self.assertEqual(zi.filename, 'myfile')
        self.checkRISCOS(zi,
                         filename='myfile',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_020_filetype(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_filetype = FILETYPE_SPRITE
        self.assertEqual(zi.filename, 'NoName,ff9')
        self.assertFalse(bool(zi.internal_attr & 1), "Check for internal text flag")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_SPRITE),
                         filetype=FILETYPE_SPRITE,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_021_filetype_text(self):
        # Text filetype should set the text bit, so not need to have the explicit NFS extension.
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_filetype = FILETYPE_TEXT
        self.assertEqual(zi.filename, 'NoName')
        self.assertTrue(bool(zi.internal_attr & 1), "Check for internal text flag")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_TEXT),
                         filetype=FILETYPE_TEXT,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_022_filetype_default(self):
        # Data filetype should clear the text bit, so not need to have the explicit NFS extension.
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_filetype = FILETYPE_DATA
        self.assertEqual(zi.filename, 'NoName')
        self.assertFalse(bool(zi.internal_attr & 1), "Check for internal text flag")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DATA),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_023_filetype_directory(self):
        # Making it a directory should change the object type and the filename
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_filetype = FILETYPE_DIRECTORY
        self.assertEqual(zi.filename, 'NoName/')
        self.assertTrue(bool(zi.external_attr & 16), "Check for msdos directory bit")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DATA),
                         filetype=FILETYPE_DIRECTORY,
                         objtype=OBJTYPE_DIRECTORY,
                         attr=ATTR_RW)

    def test_040_directory(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_objtype = OBJTYPE_DIRECTORY
        self.assertEqual(zi.filename, 'NoName/')
        self.assertTrue(bool(zi.external_attr & 16), "Check for msdos directory bit")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DIRECTORY),
                         filetype=FILETYPE_DIRECTORY,
                         objtype=OBJTYPE_DIRECTORY,
                         attr=ATTR_RW)

    def test_041_directory_to_file(self):
        # Was a directory, became a file
        zi = rozipinfo.ZipInfoRISCOS(filename='mydir/')
        # Interestingly, if you create a file with the suffix '/', ZipInfo won't imply that the object is a
        # directory, even though it explicitly checks for the '/' and during from_file assigns the bit.
        # So we will force the attribute bit to be set.
        zi.external_attr |= 16
        zi.riscos_objtype = OBJTYPE_FILE
        self.assertEqual(zi.filename, 'mydir')
        self.assertFalse(bool(zi.external_attr & 16), "Check for msdos directory bit")
        self.checkRISCOS(zi,
                         filename='mydir',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE, filetype=FILETYPE_DATA),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_060_attributes_rw_nounix(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_attr = ATTR_RW
        self.assertFalse(bool(zi.external_attr & 1), "Check for msdos read only bit clear")
        mode = zi.external_attr >> 16
        self.assertEqual(mode, 0, "Check for unix mode still unset")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_061_attributes_r_nounix(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_attr = ATTR_R
        self.assertTrue(bool(zi.external_attr & 1), "Check for msdos read only bit set")
        mode = zi.external_attr >> 16
        self.assertEqual(mode, 0, "Check for unix mode still unset")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_R)

    def test_062_attributes_w_nounix(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.riscos_attr = ATTR_W
        self.assertFalse(bool(zi.external_attr & 1), "Check for msdos read only bit clear")
        mode = zi.external_attr >> 16
        self.assertEqual(mode, 0, "Check for unix mode still unset")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_W)

    def test_070_attributes_rw_withunix(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o111 << 16
        zi.riscos_attr = ATTR_RW
        self.assertFalse(bool(zi.external_attr & 1), "Check for msdos read only bit clear")
        mode = zi.external_attr >> 16
        self.assertTrue(bool((mode & 0o222) and mode & (0o444)), "Check for unix mode rw")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)

    def test_071_attributes_r_withunix(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o111 << 16
        zi.riscos_attr = ATTR_R
        self.assertTrue(bool(zi.external_attr & 1), "Check for msdos read only bit set")
        mode = zi.external_attr >> 16
        self.assertTrue(bool(mode & (0o444)), "Check for unix mode r-")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_R)

    def test_072_attributes_w_withunix(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o111 << 16  # Force the external_attr for unix mode to be used
        zi.riscos_attr = ATTR_W
        self.assertFalse(bool(zi.external_attr & 1), "Check for msdos read only bit clear")
        mode = zi.external_attr >> 16
        self.assertTrue(bool(mode & (0o222)), "Check for unix mode -w")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_BASEDATE, EXECADDR_BASEDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_W)


class Test80ExtraFieldReading(BaseTestCase):
    """
    Tests of the extra field
    """

    def test_001_reading(self):
        zi = rozipinfo.ZipInfoRISCOS()
        zi.external_attr = 0o111 << 16  # Force the external_attr for unix mode to be used
        zi.extra = EXTRA_TEST_FILE
        self.assertFalse(bool(zi.external_attr & 1), "Check for msdos read only bit clear")
        mode = zi.external_attr >> 16
        self.assertTrue(bool((mode & 0o222) and mode & (0o444)), "Check for unix mode rw")
        self.checkRISCOS(zi,
                         filename='NoName',
                         loadexec=build_loadexec(LOADADDR_TESTDATE, EXECADDR_TESTDATE),
                         filetype=FILETYPE_DATA,
                         objtype=OBJTYPE_FILE,
                         attr=ATTR_RW)


if __name__ == '__main__':
    __name__ = os.path.basename(sys.argv[0][:-3])  # pylint: disable=redefined-builtin
    env = os.environ
    env['NOSE_WITH_XUNIT'] = '1'
    env['NOSE_VERBOSE'] = '1'
    exit(nose.runmodule(env=env))
