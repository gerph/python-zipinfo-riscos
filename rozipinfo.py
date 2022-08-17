"""
Management of the extension fields for RISC OS in ZipInfo objects.

ZipInfo objects hold the information extracted from the Zip archives for a file.
RISC OS extra fields in this ZipInfo are extractable using the `ZipInfoRISCOS`
object.
This object provides a way of extracting or storing the RISC OS extension data so
that it can be used with Zip files.

The `ZipInfoRISCOS` object is expected to be used just like the `zipfile.ZipInfo`
object, with the following extensions:

    * If read from a zip file, the extra field will automatically populate the
      `riscos_*` properties.
    * Any `riscos_*` properties which is updated will cause the base properties
      to be updated. For example, updating the riscos_loadaddr will cause the
      date_time property to be updated to hold the new timestamp.
    * If `riscos_*` properties are explicitly set, they will be inferred from
      the base properties.
      * `riscos_filename` is the RISC OS filename. It will be in a form for
        use within RISC OS, encoded using `filename_encoding_name` as the
        encoding. It a bytes (str on Python 2) object, whilst `filename` is
        always a unicode object.
      * `riscos_date_time` contains the Load and Exec timestamps when present,
        or it will be taken from the base `date_time` if no Load and Exec was
        present.
      * `riscos_filetype` contains the filetype, or -1 it none known.
        property, or from the Load and Exec timestamps if they were set.
      * Filetypes will be taken from the text flag, or may be inferred from
        the filename (see the `filetype_parentdir_mappings` and
        `filetype_extension_mappings` dictionaries for direct ways to extend
        this).
      * `riscos_objtype` is the RISC OS object type if present, or synthesised
        from other flags if not present. It will be 1 for files and 2 for
        directories.
      * `riscos_loadaddr` and `riscos_execaddr` contain the Load and Exec
        address if present, or are synthesised from the timestamp and filetype
        if not present.
      * `riscos_attr` contains the RISC OS attributes if present, or
        synthesised from the external attributes if not present
      * MimeMap may be queried before the internal extensions if this
        is implemented (see `filetype_from_extension` method).
      * Object types will be taken from the MS-DOS directory attribute, or
        the existance of a trailing '/' on the filename.
      * File attributes will be taken from the MS-DOS read-only attribute,
        and any unix attributes present in the upper 16bits of the external
        attributes.
    * Once the individual RISC OS properties have been set, changing the
      base properties has no effect. This is largely to keep the number of
      combinations down, and reduce complexity.
    * If `nfs_encoding` is set, the RISC OS extra field will not be written,
      but the filename will be updated to reflect the filetype and load/exec
      addresses, in line with the NFS extension usage. This is supported by
      the MiniZip/MiniUnzip tools, and by the InfoZip tools.
    * RISC OS filenames will have had unix unsafe names stripped from them,
      so filenames like `../evil` will have been made safe as just `evil`.
      To sanitise the `filename` property, assign the `riscos_filename` to
      itself, which will make the RISC OS filename the canonical name.

How to use the `nfs_encoding` switch:

    * When reading an archive, commonly this should be enabled (the default),
      as this will use RISC OS extra field if present, and then fall back to
      using the the NFS encoding information if present, before finally using
      the inferrence from the filename and attributes.

    * When writing an archive, if the archive is intended for use on RISC OS,
      the `nfs_encoding` should be disabled. This will allow the RISC OS extra
      field to be written, as this preserves as much information as possible
      and doesn't require NFS extension translation on RISC OS systems.

    * If the archive is intended for use on non-RISC OS systems, or for safe
      transfer between systems, the nfs_encoding should be enabled. This will
      prevent the use of the RISC OS extra field, and instead encode the
      RISC OS type and date information into the filename and date field.
      When extracted on RISC OS systems, the files will need to be manually
      translated, or use the MiniUnzip tool to extract the file information.

Many of the functions of the processing for the translation to and from
RISC OS formats are provided as separate methods within the ZipInfoRISCOS
class. This should allow their replacement in custom implementations as
necessary.
"""

import datetime
import os
import re
import stat
import struct
import sys
import time
import zipfile


try:
    # Python 3: maketrans is a member of str
    maketrans = bytes.maketrans

except AttributeError:
    # Python 2: maketrans is a member of string
    import string
    maketrans = string.maketrans


try:
    unicode

except NameError:
    # Python 3, make unicode the str type
    unicode = str


unix_epoch_to_riscos_epoch = int(int(70*365.25) * 24*60*60)
datetime_epochtime = datetime.datetime(1970, 1, 1, tzinfo=None)


def quin_to_epochtime(quin):
    if not quin:
        return None
    return (quin / 100.0) - unix_epoch_to_riscos_epoch


def quin_to_datetime(quin):
    if not quin:
        return None
    return datetime.datetime.utcfromtimestamp(quin_to_epochtime(quin))


def tuple_to_datetime(date_time_tuple):
    """
    Convert a broken down datetime to a quin (either zipinfo format or RISC OS format)
    """
    if len(date_time_tuple) == 6:
        dt = datetime.datetime(int(date_time_tuple[0]),
                               int(date_time_tuple[1]),
                               int(date_time_tuple[2]),
                               int(date_time_tuple[3]),
                               int(date_time_tuple[4]),
                               int(date_time_tuple[5]))
    elif len(date_time_tuple) == 7:
        dt = datetime.datetime(int(date_time_tuple[0]),
                               int(date_time_tuple[1]),
                               int(date_time_tuple[2]),
                               int(date_time_tuple[3]),
                               int(date_time_tuple[4]),
                               int(date_time_tuple[5]),
                               int(date_time_tuple[6]) * 1000)
    else:
        dt = None
    return dt


def epochtime_to_quin(epochtime):
    """
    Return a quin for a given epoch time.
    """
    if epochtime is None:
        return None
    cstime = int(epochtime * 100)
    quin = cstime + unix_epoch_to_riscos_epoch * 100
    return quin


def datetime_to_epochtime(dt):
    if not dt:
        return None
    timestamp = (dt - datetime_epochtime).total_seconds()
    return timestamp


def datetime_to_quin(dt):
    epochtime = datetime_to_epochtime(dt)
    quin = epochtime_to_quin(epochtime)
    return quin


def loadexec_to_quin(loadexec=None, loadaddr=None, execaddr=None):
    if loadexec:
        loadaddr = loadexec[0]
        execaddr = loadexec[1]
    if loadaddr and (loadaddr & 0xFFF00000) == 0xFFF00000:
        return ((loadaddr & 0xFF) << 32) | execaddr
    return None


def quin_to_loadexec(quin, filetype=0xFFF):
    """
    Return the load/exec for a given quin and filetype
    """
    if filetype == ZipInfoRISCOS.directory_filetype:
        filetype = ZipInfoRISCOS.directory_filetype_internal
    loadaddr = ((quin >> 32) & 255) | 0xFFF00000 | (filetype << 8)
    execaddr = (quin & 0xFFFFFFFF)
    return (loadaddr, execaddr)


class ZipInfoRISCOS(zipfile.ZipInfo):
    """
    A class providing information on a zip object, with RISC OS information extracted.

    Additional properties we add to the standard object:
        * `riscos_filename`:    Contains the filename, but in the form of a RISC OS filename
        * `riscos_date_time`:   The broken down time (similar to date_time) but accurate to centiseconds
        * `riscos_objtype`:     Object type if present, or synthesised if not present
        * `riscos_loadaddr`:    Load address if present, or synthesised if not present
        * `riscos_execaddr`:    Exec address if present, or synthesised if not present
        * `riscos_filetype`:    Filetype if present, or synthesised if not present
        * `riscos_attr`:        RISC OS attributes if present, or synthesised if not present
        * `riscos_present`:     True if the RISC OS extension is present, or False if not present
        * `nfs_encoding`:       True if the NFS encoding is used instead of the RISC OS extra fields,
                                False if the RISC OS extension will be used.

    Assigning any of these values fixes the RISC OS extension values.
    If the extension values have not been assigned they will be populated from the existing information.
    """
    # Zip extension fields
    header_id_riscos = 0x4341
    header_id_riscos_spark = 0x30435241

    # Filetype to use when none is known, and when the file is marked as text
    default_filetype = 0xFFD
    default_filetype_text = 0xFFF

    # Filetype to use for the directory in the API, and in the loadaddr
    directory_filetype = 0x1000
    directory_filetype_internal = 0xFFD

    # Encoding to use for riscos_filename
    # For use in a wider environment, consider using riscos-latin1 from the python-codecs-riscos module.
    filename_encoding_name = 'latin-1'

    # Encoding used for filenames that come from the zip files we are extracting
    # RISC OS zip archives will be most likely in Latin-1.
    zipfilename_encoding_name = 'latin-1'

    # The characters acceptable to the NFS encoding
    nfs_encoding_hexdigits = '0123456789abcdef'

    # Translation for the string
    exchange_dot_slash = maketrans(b'/.', b'./')

    # Path safety
    sanitise_unix_relative_re = re.compile(br'[^/]+/\.\.(/|$)')

    # Mappings for filename extensions (if no MimeMap implementation is present), lower case.
    filetype_extension_mappings = {
            'txt': 0xFFF,
            'c': 0xFFF,
            'c++': 0xFFF,
            'h': 0xFFF,
            's': 0xFFF,
            'zip': 0xA91,
        }
    # Mappings for the parent directory (if no other information is supplied), lower case
    filetype_parentdir_mappings = {
            # C/C++/Assembler types
            'c': 0xFFF,
            's': 0xFFF,
            'c++': 0xFFF,
            'h': 0xFFF,
            'hdr': 0xFFF,
            # Header/definition formats
            'cmhg': 0xFFF,
            'def': 0xFFF,   # used by OSLib
            # could include 'mh' but this has only ever been seen in old RISC OS source
            # Pascal types
            'p': 0xFFF,
            'imp': 0xFFF,
        }

    # External attributes for MS-DOS
    external_attr_msdos_readonly = (1<<0)
    external_attr_msdos_hidden = (1<<1)
    external_attr_msdos_system = (1<<2)
    external_attr_msdos_label = (1<<3)
    external_attr_msdos_directory = (1<<4)
    external_attr_msdos_archive = (1<<5)
    # Possibly bit 6 => link (according to zipinfo)
    # Possibly bit 7 => exe (according to zipinfo)

    # Internal attributes
    internal_attr_text = (1<<0)
    internal_attr_ebcdic = (1<<1)  # according to zipinfo

    # General file flags
    generalflags_utf8 = (1<<11)

    # RISC OS attributes
    _riscos_attr_read = (1<<0)
    _riscos_attr_write = (1<<1)
    _riscos_attr_locked = (1<<3)
    _riscos_attr_public_read = (1<<4)
    _riscos_attr_public_write = (1<<5)
    _riscos_attr_public_locked = (1<<6)

    _riscos_filename = None
    _riscos_date_time = None
    _riscos_objtype = None
    _riscos_loadaddr = None
    _riscos_execaddr = None
    _riscos_filetype = None
    _riscos_attr = None
    _riscos_present = False

    _nfs_encoding = False

    _extra = None
    _filename = ''

    def __init__(self, filename="NoName", date_time=(1980, 1, 1, 0, 0, 0),
                 zipinfo=None, nfs_encoding=True, zipinfo_fromzip=True):
        """
        Construct a new ZipInfoRISCOS object, either based on an existing zip_info or from scratch.

        @param filename:        Filename this refers to in the archive
        @param date_time:       Tuple of the date-time (6 values)
        @param zipinfo:         ZipInfo to base this object on
        @param nfs_encoding:    Whether zip filenames should use the NFS filename encoding of:
                                    * `,xxx` => filetype
                                    * `,llllllll,eeeeeeee` => load and exec address
        @param zipinfo_fromzip: Whether the ZipInfo passed came from the zip archive.
                                If set to False, the ZipInfo was created manually and
                                contains filenames in unicode format.
        """
        super(ZipInfoRISCOS, self).__init__(filename, date_time)
        if zipinfo:
            # In Python 2:
            #   The filename in a ZipInfo created from the file on disc is in the form
            #   of a raw bytes string which came from the zip archive, unless the
            #   UTF-8 flag is set. Names that came from disc (in native format) will
            #   need to be decoded using the zipfilename_encoding_name.
            #
            #   If the ZipInfo was created manually, it may be in an undetermined
            #   encoding as a str, or prepared unicode. If it's a string, it probably
            #   came from the filesystem, so we'll assume that it's UTF-8.
            #
            # In Python 3:
            #   The filename in a ZipInfo created from the file on disc has been decoded
            #   as if it was 'cp437', unless the UTF-8 flag is set. Names that came from
            #   disc in this format will need to be explicitly converted back to the
            #   form that was on disc (we assume that the conversion to 'cp437' is
            #   lossless), then decoded as the zipfilename_encoding_name.
            #
            #   If the ZipInfo was created manually, it should always be a unicode so
            #   we should trust and not decode from 'cp437'. HOWEVER, it is not possible
            #   to know that the ZipInfo was created manually from the structure, so
            #   the variable zipinfo_fromzip should be False in such cases. Most uses
            #   will be to decode from a zip, so this defaults to True.
            #
            if sys.version_info.major == 2:
                if zipinfo.flag_bits & self.generalflags_utf8:
                    # The filename is already in unicode, so nothing to do.
                    self.filename = zipinfo.filename
                else:
                    if isinstance(zipinfo.filename, unicode):
                        # They supplied it already in unicode format. Nothing to do.
                        self.filename = zipinfo.filename
                    elif zipinfo_fromzip:
                        # The filename is raw from the file, so we need to decode it
                        self.filename = zipinfo.filename.decode(self.zipfilename_encoding_name, 'replace')
                    else:
                        # They created it manually, so assume it's UTF-8
                        self.filename = zipinfo.filename.decode('utf-8', 'replace')
            else:
                if zipinfo.flag_bits & self.generalflags_utf8:
                    # The filename is already in unicode, so nothing to do.
                    self.filename = zipinfo.filename
                else:
                    if zipinfo_fromzip:
                        # The filename has been decoded as cp437 so we need to restore
                        # and redecode it.
                        filename = zipinfo.filename.encode('cp437')
                        self.filename = filename.decode(self.zipfilename_encoding_name, 'replace')
                    else:
                        # This was a manually constructed ZipInfo so the filename is
                        # already in unicode correctly.
                        self.filename = zipinfo.filename

            # They wanted to pre-populate from an existing ZipInfo object.
            # Use the __slots__ element because this gives all the fields it supports.
            # If the implementation changes, more consideration to reading the source
            # object will be required.
            for field in zipinfo.__class__.__slots__:
                if field != 'extra' and field != 'filename':
                    setattr(self, field, getattr(zipinfo, field, None))
            # Always populate the extra field last, as this modifies the existing fields
            # based on what the RISC OS extra field contains.
            self.extra = zipinfo.extra

            # Some archive tools have written the filename ending in a '/' but not marked the
            # file as being a directory. This causes problems when we try to extract because we
            # create a 0 length file, which then cannot be a directory.
            if self.filename.endswith('/'):
                self.external_attr |= self.external_attr_msdos_directory

        self._nfs_encoding = nfs_encoding
        self.create_system = 13  # RISC OS

    def __repr__(self):
        try:
            ro_load = '&{:08x}({})'.format(self.riscos_loadaddr, 'inferred' if self._riscos_loadaddr is None else 'set')
            ro_exec = '&{:08x}({})'.format(self.riscos_execaddr, 'inferred' if self._riscos_execaddr is None else 'set')
        except Exception as exc:
            ro_load = '<load/exec error: {}>'.format(exc)
            ro_exec = '<load/exec error: {}>'.format(exc)
        ro_filetype = self.riscos_filetype
        if ro_filetype == self.directory_filetype:
            ro_filetype = 'dir'
        elif ro_filetype == -1:
            ro_filetype = 'none'
        else:
            ro_filetype = '&{:03x}'.format(ro_filetype)
        ro_filetype = '{}({})'.format(ro_filetype, 'inferred' if self._riscos_filetype is None else 'set')
        ro_objtype = '{}({})'.format(self.riscos_objtype, 'inferred' if self._riscos_objtype is None else 'set')
        ro_attr = '&{:02x}({})'.format(self.riscos_attr, 'inferred' if self._riscos_attr is None else 'set')
        try:
            ro_date_time = '{!r}({})'.format(self.riscos_date_time, 'inferred' if self._riscos_date_time is None else 'set')
        except Exception as exc:
            ro_date_time = '<date error: {}>'.format(exc)

        ro_detail = 'load/exec={}/{}, filetype={}, attr={}, objtype={}, date={}'.format(ro_load,
                                                                                        ro_exec,
                                                                                        ro_filetype,
                                                                                        ro_attr,
                                                                                        ro_objtype,
                                                                                        ro_date_time)
        return '<{}(filename={!r}; RO: {})>'.format(self.__class__.__name__,
                                                    self.filename,
                                                    ro_detail)
    @property
    def filename(self):
        return self._filename

    @filename.setter
    def filename(self, value):
        """
        The filename will always be in unicode format.
        """
        if unicode is not str:
            if isinstance(value, str):
                value = value.decode(self.filename_encoding_name, 'replace')
        self._filename = value
        return value

    @property
    def extra(self):
        """
        Extra expansion field, including RISC OS data.

        Extra expansion field is implemented is a getter/setter so that we can automatically
        populate it with the RISC OS data when it is read.
        """

        # Only populate RISC OS data in the extra field if we had any RISC OS data assigned.
        if not self._riscos_present:
            return self._extra

        # Rebuild any RISC OS data that was present
        riscos_index = None
        chunks = self.extract_extra_fields(self._extra or b'')
        for (index, (header_id, data)) in enumerate(chunks):
            if header_id == self.header_id_riscos:
                (riscos_type,) = struct.unpack('<I', data[:4])
                if riscos_type == self.header_id_riscos_spark:
                    riscos_index = index

        if self.nfs_encoding:
            # We don't want the RISC OS information present, so we need to strip it from the fields.
            if riscos_index is not None:
                del chunks[riscos_index]

        else:
            # We're using RISC OS encoding, so add or modify the existing field
            new_data = struct.pack('<IIIII', self.header_id_riscos_spark, self.riscos_loadaddr, self.riscos_execaddr, self.riscos_attr, 0)
            if riscos_index is None:
                chunks.append((self.header_id_riscos, new_data))
            else:
                chunks[riscos_index] = (self.header_id_riscos, new_data)

        value = self.build_extra_fields(chunks)

        return value

    @extra.setter
    def extra(self, value):
        """
        Populate the extra expansion field.
        """
        # Extract RISC OS information.
        self._extra = value

        # Extension fields take the following form:
        #   2 bytes: header type (little endian)
        #   2 bytes: header length (little endian)
        #
        # The header type 0x4341 is allocated for RISC OS-specific information.
        #
        # The format of RISC OS specific information is held in the following
        # 4-byte word (little endian) of the extra data. The formats currently
        # known are:
        #   0x30435241  SparkFS information (20 bytes)
        #
        # Format 0x30435241 ('ARC0') data:
        #   4 bytes: load address (little endian)
        #   4 bytes: exec address (little endian)
        #   4 bytes: attributes (little endian)
        #   4 bytes: reserved for future expansion, 0 on write (little endian)

        chunks = self.extract_extra_fields(value or b'')
        for (header_id, data) in chunks:
            if header_id == self.header_id_riscos:
                # This is a RISC OS chunk we may need to process
                (riscos_type,) = struct.unpack('<I', data[:4])
                if riscos_type == self.header_id_riscos_spark:
                    (loadaddr, execaddr, attr, zero) = struct.unpack('<IIII', data[4:])
                    if self.riscos_objtype == 2:
                        # If this is a directory, the load address is ALWAYS a timestamp; so we flag it as
                        # such. Some archives are written with all 0s in the upper 24 bits of the word.
                        loadaddr &= 0xFF
                        loadaddr |= 0xFFF00000 | (self.directory_filetype_internal << 8)
                    self.riscos_loadaddr = loadaddr
                    self.riscos_execaddr = execaddr
                    self.riscos_attr = attr

    @staticmethod
    def extract_extra_fields(extra):
        """
        Extract the chunks from the extra fields.

        @param extra:   Extra field data

        @return:    List of tuples of the form (header id, data)
        """
        if not extra:
            return []

        chunks = []
        offset = 0
        while offset < len(extra) - 4:
            (header_id, data_length) = struct.unpack('<HH', extra[offset:offset + 4])
            chunks.append((header_id, extra[offset + 4:offset + 4 + data_length]))
            offset += 4 + data_length

        return chunks

    @staticmethod
    def build_extra_fields(chunks):
        """
        Build the chunks into the extra field.

        @param chunks:  List of tuples of the form (header_id, data) to build into the extra field

        @return:    List of tuples of the form (header id, data)
        """
        extra = []
        for (header_id, data) in chunks:
            extra.append(struct.pack('<HH', header_id, len(data)))
            extra.append(data)

        return b''.join(extra)

    def _update_date_time(self):
        """
        Update the date/time fields
        """
        # This is a RISC OS timestamped object, so we can update the date time
        quin = loadexec_to_quin(loadaddr=self.riscos_loadaddr,
                                execaddr=self.riscos_execaddr)
        dt = quin_to_datetime(quin)
        if dt:
            self.riscos_date_time = (dt.year, dt.month, dt.day,
                                     dt.hour, dt.minute, dt.second, int(dt.microsecond / 1000))

    def _update_nfs_encoding(self):
        """
        Update the filename for the NFS encoded form of the name.
        """
        # Translate the RISC OS layout to unix layout
        name = self.riscos_to_unix(self.riscos_filename)

        # Decode the RISC OS filename into unicode for the Zip
        name = self.decode_from_riscos(name)

        # Only files get the NFS encoding
        if self.riscos_objtype == 1:
            # Now append any NFS extensions as necessary
            name = self.build_nfs_encoding(name, self.riscos_loadaddr, self.riscos_execaddr)

            # Tweak the returned names so that we don't append filetypes unnecessarily
            if self.internal_attr & self.internal_attr_text:
                expected_type = self.default_filetype_text
            else:
                expected_type = self.default_filetype
            if name.endswith(',{:3x}'.format(expected_type)):
                name = name[:-4]
        else:
            # Directories must always end in a '/'
            name += '/'

        self.filename = name

    def filetype_from_extension(self, ext):
        """
        Use MimeMap to lookup the filetype for this file.

        @param ext: Extension to lookup

        @return:    file type if known, or None if nothing known about this filename
        """

        if sys.platform == 'riscos':
            # FIXME: Call MimeMap - dependant on the OS implementations
            # something like:
            # swi('MimeMap_Translate', 'iii', 3, '.' + ext, 0)
            pass

        return None

    def filetype_based_on_filename(self):
        """
        Work out the filetype from the filename (after mimemap)

        @return:    file type if known, or None if nothing known about this filename
        """
        if '.' in self.filename:
            _, ext = self.filename.rsplit('.', 1)
            filetype = self.filetype_extension_mappings.get(ext.lower(), None)
            if filetype is not None:
                return filetype

        if '/' in self.filename:
            dirname, _ = self.filename.rsplit('/', 1)
            if '/' in dirname:
                _, dirname = dirname.rsplit('/', 1)
            filetype = self.filetype_parentdir_mappings.get(dirname.lower())
            if filetype is not None:
                return filetype

        return None

    @classmethod
    def extract_nfs_encoding(cls, name):
        """
        Extract the NFS encoding from the filename to give the bare filename and load/exec or filetype.

        @param name:    Unix-like filename

        @return: tuple of (unix-filename stripped of suffix, load, exec, filetype)
        """
        loadaddr = None
        execaddr = None
        filetype = None

        try:
            if len(name) > 4 and \
               name[-4] == ',' and all(c in cls.nfs_encoding_hexdigits for c in name[-3:]):
                # Filename,xxx format
                filetype = int(name[-3:], 16)
                name = name[:-4]

            elif len(name) > 18 and \
               name[-9] == ',' and name[-18] == ',' and \
               all(c in cls.nfs_encoding_hexdigits for c in name[-8:]) and \
               all(c in cls.nfs_encoding_hexdigits for c in name[-17:-9]):
                # 1+8+1+8 for ,llllllll,eeeeeeee
                loadaddr = int(name[-17:-9], 16)
                execaddr = int(name[-8:], 16)
                name = name[:-18]

                if (loadaddr & 0xFFF00000) == 0xFFF00000:
                    # This is typed, so return the type as well.
                    filetype = (loadaddr >> 8) & 0xFFF

        except (ValueError, IndexError) as exc:
            # Any failures to convert numbers, or reference bad indexes, in here means it's not
            # an NFS extension format.
            return (name, None, None, None)

        return (name, loadaddr, execaddr, filetype)

    @classmethod
    def build_nfs_encoding(cls, name, loadaddr=None, execaddr=None, filetype=None):
        """
        Build the NFS encoded name, using the base unix name and parameters.

        @param name:        Unix-like filename (which may already contain NFS encoded names)
        @param loadaddr:    Load address to use
        @param execaddr:    Exec address to use
        @param filetype:    Filetype

        @return: unix filename
        """
        # Remove any existing NFS encoding information
        (name, _, _, _) = cls.extract_nfs_encoding(name)

        if loadaddr is not None and execaddr is not None:
            # They supplied explicit load and exec addresses.
            # These might be a filetype, which means we can probably just use the filetype
            if (loadaddr & 0xFFF00000) == 0xFFF00000:
                # Filetyped, so actually we just use this filetype
                filetype = (loadaddr >> 8) & 0xFFF
            else:
                return u'{},{:08x},{:08x}'.format(name, loadaddr, execaddr)

        if filetype is not None:
            return u'{},{:03x}'.format(name, filetype)

        return name

    @classmethod
    def encode_to_riscos(cls, name):
        """
        Convert the unicode string supplied to a RISC OS locale encoded string.

        Together with unix_to_riscos(), this provides the filename conversion.

        This is only for the literal encoding of characters, so that the locale is respected.
        See unix_to_riscos to path encoding considerations.

        For example, the implementation may use the standard encode() functions for encoding to
        the RISC OS locale. This may be a poor substitution for some characters which cannot be
        replaced. The LanMan98 encoding of characters could alternatively be used here.

        This implementation uses the filename_encoding_name class property to determine the
        target encoding.
        """

        # Spaces aren't allowed in the filename, and converting them to hard-spaces here
        # meeans they will be correct in whatever locale has been selected.
        name = name.replace(u' ', u'\xa0')

        name = name.encode(cls.filename_encoding_name, 'replace')
        return name

    @classmethod
    def decode_from_riscos(cls, name):
        """
        Convert the RISC OS local encoded string into a unicode string.

        Together with riscos_to_unix(), this provides the filename conversion.

        This is only for the literal encoding of characters, so that the locale is respected.
        See riscos_to_unix to path encoding considerations.

        For example, the implementation may use the standard decode() functions for decoding
        from the RISC OS locale.
        The LanMan98 encoding of characters could also be used here.

        This implementation uses the filename_encoding_name class property to determine the
        target encoding.
        """

        name = name.decode(cls.filename_encoding_name, 'replace')

        # Spaces aren't allowed in the filename, and we've encoded them as hard spaces in
        # RISC OS, so we need to translate them back to regular spaces for unix use.
        name = name.replace(u'\xa0', u' ')
        return name

    @classmethod
    def unix_to_riscos(cls, name):
        """
        Convert the unix layout string to a RISC OS layout string.

        Together with encode_to_riscos(), this provides the filename conversion.

        This deals with the formatting of the file components to make it safe. This implementation
        is specific to the filenames in the Zip file and will attempt to remove any sequences which
        would be unsafe in a RISC OS filename.
        """

        # Sanitise the Unix filename
        name = cls.sanitise_unix(name)

        # Exchange the path/extension separators to be RISC OS format
        name = name.translate(cls.exchange_dot_slash)

        # Make the path name safe for RISC OS
        name = cls.sanitise_riscos(name)
        return name

    @classmethod
    def riscos_to_unix(cls, name):
        """
        Convert the unix layout string to a RISC OS layout string.

        Together with decode_from_riscos(), this provides the filename conversion.

        This deals with the formatting of the file components to make it safe. This implementation
        is specific to the filenames in the Zip file and will attempt to remove any sequences which
        would be unsafe in a RISC OS filename.
        """

        # Make the path name safe for RISC OS
        name = cls.sanitise_riscos(name)

        # Exchange the path/extension separators to be RISC OS format
        name = name.translate(cls.exchange_dot_slash)
        return name

    @classmethod
    def sanitise_unix(cls, name):
        """
        Ensure that the name we use on the unix side side is safe.

        We remove or replace any sequences that would result in non-deterministic behaviour
        on the unix side for the conversions. Essentially that means anchoring and relative
        references.

        @param name:    unix name to translate, as a bytes object

        @return: Safe name to use for unix
        """

        name = name.lstrip(b'/')

        # Multiple path separators are allowed on unix but reduce to a single separator
        while b'//' in name:
            name = name.replace(b'//', b'/')

        # Current directory components are ignorable
        name = name.replace(b'/./', b'/')
        if name.startswith(b'./'):
            name = name[2:]
        if name.endswith(b'/.'):
            name = name[:-2]

        # Leading relative paths are junk.
        while name.startswith(b'../'):
            name = name[3:]

        # Internal relative paths can be processed
        while True:
            (name, count) = cls.sanitise_unix_relative_re.subn(b'', name, count=1)
            if count == 0:
                break

        # Bare directory specifications
        if name == b'.' or name == b'..':
            name = b''

        # If we were left with nothing, give it a name
        if name == b'':
            name = b'root'

        return name

    @classmethod
    def sanitise_riscos(cls, name):
        """
        Ensure that the name we use on the RISC OS side is safe.

        We remove or replace any unsafe characters to build a RISC OS name which is either completely
        valid, or invalid, but never strays outside the target directory.

        @param name:    RISC OS name to translate

        @return: Safe name to use for RISC OS
        """

        # Make any attempt to inject system variables safe
        name = name.replace(b'<', b'(').replace(b'>', b')')

        # Remove any initial anchors
        while name.startswith((b'$.', b'@.', b'%.', b'\\.', b'&.', b'^.')):
            name = name[2:]

        # Strip wildcards
        name = name.replace(b'*', b'(star)').replace(b'?', b'(q)')

        # Strip relative naming
        name = name.replace(b'.^', b'')

        # Other anchors anywhere else in the name will be invalid, so no need to make them safe

        # Prevent disc naming
        name = name.replace(b':', b'--')

        # Quotes aren't allowed in filenames either
        name = name.replace(b'"', b"'")

        # Prevent special field naming (may be overzealous here?)
        name = name.replace(b'#', b'(h)')

        # RISC OS names cannot start or end in a path separator
        if name.startswith(b'.'):
            name = name[1:]
        if name.endswith(b'.'):
            name = name[:-1]

        # At this point the filename will either be invalid, or safe for use without it going outside
        # the target directory.
        return name

    ################ NFS encoding setting
    @property
    def nfs_encoding(self):
        return self._nfs_encoding

    @nfs_encoding.setter
    def nfs_encoding(self, value):
        changed = self._nfs_encoding != bool(value)
        if changed:
            (name, loadaddr, execaddr, filetype) = self.extract_nfs_encoding(self.filename)
            self._nfs_encoding = bool(value)
            if not self._nfs_encoding:
                # We have a unix name, so we can now explicitly clear the RISC OS filename to use that.
                self.filename = name
                self._riscos_filename = None
                if loadaddr:
                    self._riscos_loadaddr = loadaddr
                    self._riscos_execaddr = execaddr
                    self._riscos_filetype = None
                    self._riscos_present = True
                elif filetype:
                    # Unless the extract_nfs_encoding is overridden, this should not happen.
                    self._riscos_loadaddr = None
                    self._riscos_execaddr = None
                    self.riscos_filetype = filetype
            else:
                self._update_nfs_encoding()

    ################ Filename
    @property
    def riscos_filename(self):
        if self._riscos_filename is not None:
            return self._riscos_filename

        if self.nfs_encoding:
            # Convert filename to RISC OS format
            (name, loadaddr, execaddr, filetype) = self.extract_nfs_encoding(self.filename)
            # We don't care about those types here; just that the name has been extracted.
        else:
            name = self.filename
            # WARNING:
            # In Python 2 the filename is a unicode if the UTF-8 flag was set, and a str if not.
            # In Python 3 the filename is always a unicode.
            if not isinstance(name, unicode):
                # Decode from cp437 to match zipfile's handling in Python 3.
                name = name.decode('cp437')

        # The filename is in unicode format for self.filename.
        # RISC OS filename should be in the RISC OS locale, so first we need to encode the
        # filename properly.
        name = self.encode_to_riscos(name)

        # The '.' and '/' characters need to be exchanged, and any other characters made safe.
        name = self.unix_to_riscos(name)
        return name

    @riscos_filename.setter
    def riscos_filename(self, value):
        # Convert filename from RISC OS format to format for zipfile

        # Make it safe for use in the archive.
        riscos_filename = self.sanitise_riscos(value)

        self._riscos_filename = riscos_filename
        self._riscos_present = True

        if self.nfs_encoding:
            # We need to update the filename to reflect new parameters
            self._update_nfs_encoding()
        else:
            # Swap the . and / around, and convert other characters
            name = self.riscos_to_unix(riscos_filename)

            # Change from RISC OS encoding to unicode
            name = self.decode_from_riscos(name)
            self.filename = name

    ################ Date/time
    @property
    def riscos_date_time(self):
        """
        Date and time tuple, with an extra entry for microseconds.
        """
        if self._riscos_date_time is not None:
            return self._riscos_date_time

        if self._riscos_loadaddr is not None:
            quin = loadexec_to_quin(loadaddr=self._riscos_loadaddr, execaddr=self._riscos_execaddr or 0)
            dt = quin_to_datetime(quin)
            if dt:
                return (dt.year, dt.month, dt.day,
                        dt.hour, dt.minute, dt.second, int(dt.microsecond / 1000))

        # Fall back to the standard format, with fractional part for centiseconds
        return tuple([int(x) for x in self.date_time] + [(self.date_time[5] * 100) % 100])

    @riscos_date_time.setter
    def riscos_date_time(self, value):
        # Convert timestamp from RISC OS format to format for zipfile
        self._riscos_date_time = value
        if len(value) == 6:
            self.date_time = tuple(value[0:5] + [value[5] + (value[6] / 100)])
        else:
            self.date_time = tuple(value[0:6])

        # If they had load/exec set, we need to update it with the new timestamp.
        if self._riscos_loadaddr is not None or \
           self._riscos_execaddr is not None:

            dt = tuple_to_datetime(value)
            quin = datetime_to_quin(dt)
            (self._riscos_loadaddr, self._riscos_execaddr) = quin_to_loadexec(quin, filetype=self.riscos_filetype)

    ################ Load address
    @property
    def riscos_loadaddr(self):
        # Convert time/filetype to RISC OS format
        if self._riscos_loadaddr is not None:
            # Load address exists.
            if (self._riscos_loadaddr & 0xFFF00000) == 0xFFF00000 and self.riscos_filetype is not None:
                # Can replace into the current load address
                if self.riscos_filetype == self.directory_filetype:
                    loadaddr = (self._riscos_loadaddr & 0xFFF000FF) | (self.directory_filetype_internal << 8)
                else:
                    loadaddr = (self._riscos_loadaddr & 0xFFF000FF) | (self.riscos_filetype << 8)
                return loadaddr
            else:
                return self._riscos_loadaddr

        if self.riscos_objtype == 1:
            # No load address given explicitly, so try to extract from NFS naming
            if self.nfs_encoding:
                # Convert filename to RISC OS format
                (name, loadaddr, execaddr, filetype) = self.extract_nfs_encoding(self.filename)
                if loadaddr is not None:
                    return loadaddr

        # No load address given; so we have to generate one from the date_time
        dt = tuple_to_datetime(self.riscos_date_time)
        quin = datetime_to_quin(dt)
        (loadaddr, _) = quin_to_loadexec(quin, filetype=self.riscos_filetype)
        return loadaddr

    @riscos_loadaddr.setter
    def riscos_loadaddr(self, value):
        #print("Set loadaddr: %s, %08x" % (value, value))
        self._riscos_loadaddr = value
        self._riscos_filetype = None
        self._update_date_time()

        self._riscos_present = True

    ################ Exec address
    @property
    def riscos_execaddr(self):
        if self._riscos_execaddr is not None:
            # Exec address exists.
            return self._riscos_execaddr

        # No exec address given explicitly, so try to extract from NFS naming
        if self.nfs_encoding:
            # Convert filename to RISC OS format
            (name, loadaddr, execaddr, filetype) = self.extract_nfs_encoding(self.filename)
            if execaddr is not None:
                return execaddr

        # No exec address given; so we have to generate one from the date_time
        dt = tuple_to_datetime(self.riscos_date_time)
        quin = datetime_to_quin(dt)
        (_, execaddr) = quin_to_loadexec(quin)
        return execaddr

    @riscos_execaddr.setter
    def riscos_execaddr(self, value):
        self._riscos_execaddr = value
        self._update_date_time()
        self._riscos_present = True

    ################ File attributes
    @property
    def riscos_attr(self):
        if self._riscos_attr is not None:
            return self._riscos_attr

        # Convert attributes to RISC OS file attributes
        if self.external_attr & 0xFFFF0000:
            # The unix attributes look valid, so we'll use them
            attr = 0x00
            # FIXME: Decide whether we should separate the 'you'/'others' into the
            #        'owner'/'others' permissions.
            if (self.external_attr >> 16) & 0o222:
                # One of the write permissions was set
                attr |= 0x22
            if (self.external_attr >> 16) & 0o444:
                # One of the Read permissions was set
                attr |= 0x11
            return attr

        if self.external_attr & self.external_attr_msdos_readonly:
            # Read only => no write access
            # We /could/ report object locked against deletion, but that's not the same meaning
            return 0x11

        return 0x33

    @riscos_attr.setter
    def riscos_attr(self, value):
        # Convert file attributes from RISC OS format to format for zipfile
        if value & 0x22:
            # Write is enabled, so mark in the MSDOS attributes
            self.external_attr = self.external_attr & ~self.external_attr_msdos_readonly

            if (self.external_attr & 0xFFFF0000):
                # There are unix attributes set in the external_attr flags, so we should update
                # them with the new value - add the write bit.
                self.external_attr |= (0o222<<16)
        else:
            # Set readonly if no write permission
            self.external_attr = self.external_attr | self.external_attr_msdos_readonly

            if (self.external_attr & 0xFFFF0000):
                # There are unix attributes set in the external_attr flags, so we should update
                # them with the new value - remove the write bit.
                self.external_attr &= ~(0o222<<16)

        if value & 0x11:
            # Read flags in unix
            if (self.external_attr & 0xFFFF0000):
                # There are unix attributes set in the external_attr flags, so we should update
                # them with the new value - add the read bit.
                self.external_attr |= (0o444<<16)
        else:
            if (self.external_attr & 0xFFFF0000):
                # There are unix attributes set in the external_attr flags, so we should update
                # them with the new value - remove the read bit.
                self.external_attr &= ~(0o444<<16)

        self._riscos_attr = value
        self._riscos_present = True

    ################ File type
    @property
    def riscos_filetype(self):
        # Convert information to RISC OS file type
        if self.riscos_objtype == 2:
            return self.directory_filetype

        if self._riscos_filetype is not None:
            return self._riscos_filetype

        # No filetype currently set, so we'll infer one.
        if self.nfs_encoding:
            # Convert filename to RISC OS format
            (name, loadaddr, execaddr, filetype) = self.extract_nfs_encoding(self.filename)
            if filetype is not None:
                return filetype
            if loadaddr is not None:
                # A load address was given, which isn't a filetype, so report as no type
                # present.
                return -1

        if self._riscos_loadaddr is not None:
            if (self._riscos_loadaddr & 0xFFF00000) != 0xFFF00000:
                # A load address has been supplied, and it's not a filetype.
                return -1
            else:
                # A load address has been supplied, and it includes a filetype
                return (self._riscos_loadaddr >> 8) & 0xFFF

        # Call out to MimeMap to get the correct filetype for the name.
        if '.' in self.filename:
            _, ext = self.filename.rsplit('.', 1)
            filetype = self.filetype_from_extension(ext)
            if filetype:
                return filetype

        # Now try our internal mappings
        filetype = self.filetype_based_on_filename()
        if filetype:
            return filetype

        if self.internal_attr & self.internal_attr_text:
            return self.default_filetype_text

        return self.default_filetype

    @riscos_filetype.setter
    def riscos_filetype(self, filetype):
        if filetype == self.directory_filetype:
            # They want this to be a directory.
            self._riscos_filetype = None  # Temporary disable to avoid recursion
            self.riscos_objtype = 2
        else:
            # Force this to be a file, if it was a directory
            if self.riscos_objtype != 1:
                self.riscos_objtype = 1

        # Convert filetype from RISC OS format to format for zipfile
        if self._riscos_loadaddr is not None:
            # The load address is set, so we need to override it.
            if (self._riscos_loadaddr & 0xFFF00000) != 0xFFF00000:
                # It contains a type, so we need to replace it.
                if filetype == self.directory_filetype:
                    self._riscos_loadaddr = (self._riscos_loadaddr & 0xFFF000FF) | (self.directory_filetype_internal << 8)
                else:
                    self._riscos_loadaddr = (self._riscos_loadaddr & 0xFFF000FF) | (filetype << 8)
            else:
                # The load address is untyped, so we need to build a new one from the datetime
                dt = tuple_to_datetime(self.riscos_date_time)
                quin = datetime_to_quin(dt)
                (self._riscos_loadaddr, self._riscos_execaddr) = quin_to_loadexec(quin, filetype=filetype)
        else:
            # There was no load/exec specified, so we will let the properties handle that.
            pass

        if filetype == self.default_filetype_text and \
           self.default_filetype_text != self.default_filetype:
            # It's a text filetype (and we're differentiating text and non-text files), so set the correct
            # bit in the internal attributes
            self.internal_attr |= self.internal_attr_text
        else:
            # Not text (or we're not differentiating, so clear the text flag)
            self.internal_attr &= ~self.internal_attr_text

        self._riscos_filetype = filetype
        self._riscos_present = True

        if self.nfs_encoding:
            # We need to update the filename to reflect new parameters
            self._update_nfs_encoding()

    @property
    def riscos_objtype(self):
        # FIXME: Convert information to RISC OS file type
        if self._riscos_objtype:
            return self._riscos_objtype

        if self.external_attr & self.external_attr_msdos_directory:
            return 2
        return 1

    @riscos_objtype.setter
    def riscos_objtype(self, value):
        # Convert object type from RISC OS format to format for zipfile
        if value == 2:
            if self._riscos_filetype is not None:
                self._riscos_filetype = None
            if self._riscos_loadaddr is not None:
                # If a load address was set, we need to reset it to the directory type
                self._riscos_loadaddr = (self._riscos_loadaddr & 0xFFF000FF) | (self.directory_filetype_internal << 8)

        self._riscos_objtype = value
        self._riscos_present = True

        if self.nfs_encoding:
            # We need to update the filename to reflect new parameters
            self._update_nfs_encoding()

        if self._riscos_objtype == 2:
            # The external attributes are defined to contain attributes based on the creator type.
            # However, most (all?) implementations treat the lower 8 bits as the MS DOS attributes,
            # with the top 16 bits being set to the unix mode (which is not defined in the
            # pkzip spec).
            # * InfoZip treats the amiga as special in creating with dedicated Amiga-only attributes.
            # * InfoZip checks if the top 16 bits are consistent with the write and directory
            #   bits, and if so uses them as the file mode.
            # * Python treats the top 16 bits of the external attributes as the file mode if no
            #   bits are set in the whole word.
            # * Zipper treats the MSDOS directory bit as the directory specifier, regardless of creator.
            self.external_attr |= self.external_attr_msdos_directory

            # Need to update the external attributes, if there were any set, to make the directory accessible
            if (self.external_attr & 0xFFFF0000):
                # Convert the 'read' attribute into an 'execute' attribute in the attributes
                self.external_attr |= ((self.external_attr & (0o444<<16)) >> 2)
                # Also make it writeable too; this seems to make sense for a RISC OS directory.
                self.external_attr |= ((self.external_attr & (0o444<<16)) >> 1)

            # * InfoZip expects directories to be terminated by a '/' character; if they're not it
            #   doesn't mind, but the implication is that others may expect it.
            # * Python always generates names with a '/' on the end if they're marked as a directory.
            if not self.filename.endswith('/'):
                self.filename += '/'
        else:
            self.external_attr &= ~self.external_attr_msdos_directory
            if self.filename.endswith('/'):
                self.filename = self.filename[:-1]

    @classmethod
    def from_file(cls, filename, arcname=None, nfs_encoding=False):
        """
        Read the ZipInfo parameters from a file on the filesystem.
        Should be approximately equivalent to the class method with the same name in
        Python 3.
        """
        st = os.stat(filename)
        isdir = stat.S_ISDIR(st.st_mode)
        mtime = time.gmtime(st.st_mtime)
        date_time = mtime[0:6]
        if arcname is None:
            arcname = filename
        arcname = os.path.normpath(os.path.splitdrive(arcname)[1])
        while arcname[0] in (os.sep, os.altsep):
            arcname = arcname[1:]

        if isdir:
            arcname += '/'

        zinfo = cls(arcname, date_time, nfs_encoding=True)
        zinfo.external_attr = (st.st_mode & 0xFFFF) << 16  # Unix attributes
        if isdir:
            zinfo.file_size = 0
            zinfo.external_attr |= 0x10  # MS-DOS directory flag
        else:
            zinfo.file_size = st.st_size

        # Finally set the encoding to the format requested, so that we get the encoding
        # format they want to use.
        zinfo.nfs_encoding = nfs_encoding
        return zinfo
