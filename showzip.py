#!/usr/bin/env python
"""
Small script to just print a list of what's in a zip archive using the ZipInfoRISCOS object.
"""

import sys
import zipfile

import rozipinfo

if len(sys.argv[1]) < 0:
    sys.exit("Syntax: {} <zip file>".format(sys.argv[0]))

zip_filename = sys.argv[1]

with zipfile.ZipFile(zip_filename, 'r') as zh:

    for index, zi in enumerate(zh.infolist()):
        zi = rozipinfo.ZipInfoRISCOS(zipinfo=zi)
        print("File #{}".format(index))
        print("  Unix filename:         {!r}".format(zi.filename))
        print("  Unix date/time:        {!r}".format(zi.date_time))
        print("  MS DOS flags:          0x{:02x}".format(zi.external_attr & 0xFF))
        print("  Unix mode:             0o{:05o}".format(zi.external_attr>>16))

        print("  RISC OS filename:      {!r}".format(zi.riscos_filename))
        print("  RISC OS date/time:     {!r}".format(zi.riscos_date_time))
        print("  RISC OS load/exec:     0x{:08x}/0x{:08x}".format(zi.riscos_loadaddr, zi.riscos_execaddr))
        if zi.riscos_filetype == -1:
            print("  RISC OS filetype:      unset")
        else:
            print("  RISC OS filetype:      0x{:03x}".format(zi.riscos_filetype))
        print("  RISC OS attributes:    0x{:02x}".format(zi.riscos_attr))
        print("  RISC OS object type:   {}".format(zi.riscos_objtype))
        print("")
