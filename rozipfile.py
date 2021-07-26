#!/usr/bin/env python
"""
Manage a ZipFile for RISC OS zip archives.

The RISCOSZipFile class is similar to that of the system ZipFile class. It provides the
means by which a Zip archive can be created, extracted or listed.

Used as a tool, this module is intended to be used to extract RISC OS archives on Unix
systems, for use with emulators and RISC OS Pyromaniac. It may also create archives
from the filenames encoded in NFS encoding format.

Command line tool allows:

    * `--create <archive> <filename>*`
      Creation of a RISC OS Zip archive from a collection of unix files.
    * `--extract <archive> <filenames>*`
      Extraction of files from a RISC OS Zip archive to unix files (with NFS extensions).
    * `--list <archive>`
      Listing of a RISC OS Zip archive as if it was a RISC OS archive.
"""

import argparse
import os
import sys
import zipfile

import rozipinfo


class RISCOSZipFile(object):
    named_types = {
            0xFFF: 'Text',
            0xFFE: 'Command',
            0xFFD: 'Data',
            0xFFC: 'Utility',
            0xFFB: 'BASIC',
            0xFFA: 'Module',
            0xFF9: 'Sprite',
            0xFF8: 'Absolute',
            0xFF7: 'BBC font',
            0xFF6: 'Font',
            0xFF5: 'PoScript',
            0xFF4: 'Printout',
            0xFF2: 'Config',
            0xFF0: 'TIFF',
            0xFD1: 'BasicTxt',
            0xFED: 'Palette',
            0xFEC: 'Template',
            0xFEB: 'Obey',
            0xFEA: 'Desktop',
            0xFE6: 'Unix Ex',
            0xFE5: 'EPROM',
            0xFDC: 'SoftLink',
            0xFD3: 'DebImage',
            0xFCA: 'Squash',
            0xFC9: 'SunRastr',
            0xFAF: 'HTML',
            0xFAE: 'Resource',
            0xF89: 'GZip',
            0xD94: 'ArtWork',
            0xC85: 'JPEG',
            0xBBC: 'BBC ROM',
            0xB61: 'XBM',
            0xB60: 'PNG',
            0xB2F: 'WMF',
            0xAFF: 'DrawFile',
            0xA91: 'Zip',
            0xA66: 'WebP',
            0xA65: 'JPEG2000',
            0x69E: 'PNM',
            0x69D: 'Targa',
            0x69C: 'BMP',
            0x697: 'PCX',
            0x695: 'GIF',
            0x690: 'Clear',
            0x1C9: 'DiagData',
            0x132: 'ICO',
        }

    def __init__(self, zip_filename, mode='r', base_dir='.'):
        self.zip_filename = zip_filename
        self.mode = mode
        self.zh = zipfile.ZipFile(zip_filename, mode)
        self.base_dir = os.path.abspath(base_dir)
        self._fileslist = None
        self._namesdict = None

    def close(self):
        self.zh.close()
        self.zh = None

    def verbose(self, message):
        if 'r' in self.mode:
            prefix = 'Zip decompress: '
        else:
            prefix = 'Zip compress: '
        print("{}{}".format(prefix, message))

    def verbose_object(self, zi):
        if zi.riscos_objtype == 2:
            self.verbose('Directory {!r}'.format(zi.filename))
        else:
            if zi.riscos_filetype != -1:
                filetype = 'type &{:03X}'.format(zi.riscos_filetype)
            else:
                filetype = 'load/exec &{:08X}/&{:08X}'.format(zi.riscos_loadaddr, zi.riscos_execaddr)
            self.verbose('File {!r}, size {} bytes, {}'.format(zi.riscos_filename,
                                                                     zi.file_size,
                                                                     filetype))

    def add_file(self, filename, verbose=False):
        zipname = os.path.relpath(filename, self.base_dir)
        zi = rozipinfo.ZipInfoRISCOS.from_file(filename=filename, arcname=zipname, nfs_encoding=True)
        zi.nfs_encoding = False
        if verbose:
            self.verbose_object(zi)
        with open(filename, 'r') as fh:
            data = fh.read()
        self.zh.writestr(zi, data)


    def add_dir(self, filename, verbose=False):
        zipname = os.path.relpath(filename, self.base_dir)
        zi = rozipinfo.ZipInfoRISCOS.from_file(filename=filename, arcname=zipname, nfs_encoding=True)
        zi.nfs_encoding = False
        self.zh.writestr(zi, b'')

        if verbose:
            self.verbose_object(zi)

        # Having written this directory, we now need to write each of the objects within it.
        for name in os.listdir(filename):
            new_filename = os.path.join(filename, name)
            self.add_to_zipfile(new_filename)

    def add_to_zipfile(self, filename, verbose=False):
        if os.path.isfile(filename):
            # This is a simple file
            self.add_file(filename, verbose=verbose)

        elif os.path.isdir(filename):
            # This is a directory, so we want to add everything within it
            self.add_dir(filename, verbose=verbose)

        else:
            raise RuntimeError("Cannot add '{}' as it is not a file or directory".format(filename))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, value, tb):
        self.close()

    def infolist(self):
        """
        Return ZipInfo items for each member of the archive.
        """
        if self._fileslist is None:
            self._fileslist = [rozipinfo.ZipInfoRISCOS(zipinfo=zi, nfs_encoding=False) for zi in self.zh.infolist()]

        return self._fileslist

    def namesdict(self):
        """
        Return a dictionary of the names to the ZipInfoRISCOS.
        """
        if self._namesdict is None:
            self._namesdict = dict((zi.riscos_filename, zi) for zi in self.infolist())

        return self._namesdict

    def namelist(self):
        """
        Return a list of the names.
        """
        return [zi.riscos_filename for zi in self.infolist()]

    def _describe_attributes(self, attr, objtype):
        label = []
        if objtype & 2:
            label.append('D')
        if attr & rozipinfo.ZipInfoRISCOS._riscos_attr_locked:
            label.append('L')
        if attr & rozipinfo.ZipInfoRISCOS._riscos_attr_write:
            label.append('W')
        if attr & rozipinfo.ZipInfoRISCOS._riscos_attr_read:
            label.append('R')
        label.append('/')
        if attr & rozipinfo.ZipInfoRISCOS._riscos_attr_public_locked:
            label.append('L')
        if attr & rozipinfo.ZipInfoRISCOS._riscos_attr_public_write:
            label.append('W')
        if attr & rozipinfo.ZipInfoRISCOS._riscos_attr_public_read:
            label.append('R')

        return ''.join(label)

    def _describe_filetype(self, filetype, objtype):
        if objtype == 2:
            return 'Directory'

        if filetype == -1:
            return 'Untyped'

        val = self.named_types.get(filetype, None)
        if not val:
            val = '&{:3X}'.format(filetype)
        return val

    def _describe_datetime(self, dt):
        """
        Describe a datetime from the RISC OS system usably.

        @param dt: date and time tuple
        """
        dt = rozipinfo.tuple_to_datetime(dt)
        # RISC OS format string is: '%24:%MI:%SE %DY-%M3-%CE%YR'
        # strftime format string is: '%H:%M%:%S %d-%b-%Y'
        return dt.strftime('%H:%M%:%S %d-%b-%Y')

    def _describe_filesize(self, value, fixed=False):
        """
        Describe the size of the files.
        """
        units = ''
        if value > 1024 * 1024:
            value = int(value / 1024 / 1024)
            units = 'M'
        elif value > 1024:
            value = int(value / 1024)
            units = 'K'

        if fixed:
            units = units or ' '
            filesize = '%4s%sbytes' % (value, units)
        else:
            filesize = '%s%sbytes' % (value, units)

        return filesize

    def _describe_loadexec(self, loadaddr, execaddr):
        """
        Describe the load and exec addresses.
        """
        return "{:08X} {:08X}".format(loadaddr, execaddr)

    def printdir(self):
        """
        Print the files from the archive.
        """
        files = self.infolist()
        dirs = {}
        longest_name = 10

        for zi in files:
            if '.' in zi.riscos_filename:
                dirname, leafname = zi.riscos_filename.rsplit('.', 1)
            else:
                dirname = ''
                leafname = zi.riscos_filename
            if dirname not in dirs:
                dirs[dirname] = {}
            dirs[dirname][leafname] = zi
            longest_name = max(len(zi.riscos_filename), longest_name)

        # Now print them in order
        for dirname, items in sorted(dirs.items(), key=lambda d: d[0].lower()):
            for leafname, zi in sorted(items.items(), key=lambda l: l[0].lower()):
                # Example '*ex' format:
                #   tests/txt              WR/WR Text        23:08:07 17-May-2020   293 bytes
                if (zi.riscos_loadaddr & 0xFFF00000) != 0xFFF00000:
                    loadexec_datetime = self._describe_loadexec(zi.riscos_loadaddr, zi.riscos_execaddr)
                else:
                    loadexec_datetime = self._describe_datetime(zi.riscos_date_time)
                print("{:{}} {:9} {:<10} {:>20} {}".format(zi.riscos_filename,
                                                           longest_name,
                                                           self._describe_attributes(zi.riscos_attr, zi.riscos_objtype),
                                                           self._describe_filetype(zi.riscos_filetype, zi.riscos_objtype),
                                                           loadexec_datetime,
                                                           self._describe_filesize(zi.file_size, fixed=True)))

    def printdir_verbose(self):
        """
        Long form of the files in the archive
        """
        for index, zi in enumerate(self.infolist()):
            print("File #{}".format(index))
            print("  Unix filename:         {!r}".format(zi.filename))
            print("  Unix date/time:        {!r}".format(zi.date_time))
            print("  MS DOS flags:          &{:02x}".format(zi.external_attr & 0xFF))
            print("  Unix mode:             8_{:05o}".format(zi.external_attr>>16))

            print("  RISC OS filename:      {}".format(zi.riscos_filename.decode('latin-1')))
            print("  RISC OS date/time:     {!r}".format(zi.riscos_date_time))
            print("  RISC OS load/exec:     &{:08x}/&{:08x}".format(zi.riscos_loadaddr, zi.riscos_execaddr))
            if zi.riscos_filetype == -1:
                print("  RISC OS filetype:      unset")
            else:
                print("  RISC OS filetype:      &{:03x}".format(zi.riscos_filetype))
            print("  RISC OS attributes:    &{:02x}".format(zi.riscos_attr))
            print("  RISC OS object type:   {}".format(zi.riscos_objtype))
            print("")

    def getinfo(self, name):
        return self.namesdict()[name]

    def read(self, member):
        if isinstance(member, str):
            zi = self.getinfo(member)
        else:
            zi = member
        return self.zh.read(zi)

    def extract(self, member, path=None, verbose=False):
        if isinstance(member, str):
            zi = self.getinfo(member)
        else:
            if isinstance(member, rozipinfo.ZipInfoRISCOS):
                zi = member
            else:
                zi = rozipinfo.ZipInfoRISCOS(zipinfo=member)

        # Ensure that we'll extract in NFS encoding format
        zi.nfs_encoding = True

        if not path:
            path = '.'

        filename = os.path.join(path, zi.filename)
        if verbose:
            self.verbose_object(zi)
        if zi.riscos_objtype == 2:
            if not os.path.isdir(filename):
                os.makedirs(filename)
        else:
            content = self.read(zi)
            with open(filename, 'wb') as fh:
                fh.write(content)

            # Set the timestamp
            dt = rozipinfo.tuple_to_datetime(zi.riscos_date_time)
            epoch = rozipinfo.datetime_to_epochtime(dt)
            os.utime(filename, (epoch, epoch))

    def extractall(self, path=None, members=None, verbose=False):
        if members is None:
            members = self.namelist()

        if path and not os.path.isdir(path):
            os.makedirs(path)

        for member in members:
            self.extract(member, path, verbose=verbose)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true',
                        help="Output more information during processing")
    parser.add_argument('-C', '--chdir', default='.',
                        help="Base directory for the reading or writing files")
    parser.add_argument('-c', '--create', action='store_true',
                        help="Create a RISC OS zip archive, from files with NFS encoding")
    parser.add_argument('-e', '--extract', action='store_true',
                        help="Extract files from a RISC OS zip archive, to files with NFS encoding")
    parser.add_argument('-l', '--list', action='store_true',
                        help="List the contents of a RISC OS zip archive")
    parser.add_argument('zipfile',
                        help="Zip archive to create")
    parser.add_argument('content', nargs='*',
                        help="Files/directories to add to the archive")

    options = parser.parse_args()

    zip_filename = os.path.abspath(options.zipfile)

    if options.create:
        with RISCOSZipFile(zip_filename, 'w', base_dir=options.chdir) as rzh:

            options.chdir = os.path.abspath(options.chdir)
            for filename in options.content:
                rzh.add_to_zipfile(filename, verbose=options.verbose)

    elif options.list:
        with RISCOSZipFile(zip_filename, 'r') as zh:
            if options.verbose:
                zh.printdir_verbose()
            else:
                zh.printdir()

    elif options.extract:
        with RISCOSZipFile(zip_filename, 'r') as zh:
            zh.extractall(path=options.chdir, verbose=options.verbose,
                          members=options.content if options.content else None)

    else:
        print("No action specified")
        sys.exit(1)


if __name__ == '__main__':
    main()
