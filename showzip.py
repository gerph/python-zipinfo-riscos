#!/usr/bin/env python
"""
Small script to just print a list of what's in a zip archive using the ZipInfoRISCOS object.
"""

from __future__ import print_function

import re
import sys
import zipfile

import rozipinfo


escapable_re = re.compile(br'[\x00-\x1f\x7f-\xff]')


def present_unicode(name):
    """
    Presentation format for the Unicode native filenames
    """
    if sys.version_info.major == 2:
        name = name.encode('utf-8')
        value = "'" + name.replace("'", "\\'") + "'"
        return value
    else:
        return "'" + name.replace("'", "\\'") + "'"


def present_riscos(name):
    """
    Presentation format for the RISC OS filenames
    """
    name = name.replace(b'\\', b'\\\\')
    value = escapable_re.sub(lambda s: b'\\x%02x' % (ord(s.group(0))), name)
    if sys.version_info.major == 2:
        return "'" + value.replace("'", "\\'") + "'"
    else:
        return "'" + value.decode('ascii') + "'"


if len(sys.argv[1]) < 0:
    sys.exit("Syntax: {} <zip file>".format(sys.argv[0]))

zip_filename = sys.argv[1]

with zipfile.ZipFile(zip_filename, 'r') as zh:

    for index, zi in enumerate(zh.infolist()):
        zi = rozipinfo.ZipInfoRISCOS(zipinfo=zi)
        print("File #{}".format(index))
        print("  Unix filename:         {}".format(present_unicode(zi.filename)))
        print("  Unix date/time:        {!r}".format(zi.date_time))
        print("  MS DOS flags:          0x{:02x}".format(zi.external_attr & 0xFF))
        print("  Unix mode:             0o{:05o}".format(zi.external_attr>>16))

        print("  RISC OS filename:      {}".format(present_riscos(zi.riscos_filename)))
        print("  RISC OS date/time:     {!r}".format(zi.riscos_date_time))
        print("  RISC OS load/exec:     0x{:08x}/0x{:08x}".format(zi.riscos_loadaddr, zi.riscos_execaddr))
        if zi.riscos_filetype == -1:
            print("  RISC OS filetype:      unset")
        else:
            print("  RISC OS filetype:      0x{:03x}".format(zi.riscos_filetype))
        print("  RISC OS attributes:    0x{:02x}".format(zi.riscos_attr))
        print("  RISC OS object type:   {}".format(zi.riscos_objtype))
        print("")
