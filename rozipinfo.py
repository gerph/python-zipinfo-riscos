"""
Management of the extension fields for RISC OS in ZipInfo objects.

ZipInfo objects hold the information extracted from the Zip archives for a file.
RISC OS extra fields in this ZipInfo are extractable using the ZipInfoRISCOS object.
This object provides 
"""

import datetime
import struct
import sys
import zipfile


unix_epoch_to_riscos_epoch = int(int(70*365.25) * 24*60*60)
datetime_epochtime = datetime.datetime(1970, 1, 1, tzinfo=None)


def quin_to_epochtime(quin):
    if not quin:
        return None
    return (quin / 100.0) - unix_epoch_to_riscos_epoch


def quin_to_datetime(quin):
    if not quin:
        return None
    return datetime.datetime.fromtimestamp(quin_to_epochtime(quin))


def tuple_to_datetime(date_time_tuple):
    """
    Convert a broken down datetime to a quin (either zipinfo format or RISC OS format)
    """
    if len(date_time_tuple) == 6:
        dt = datetime.datetime(date_time_tuple[0],
                               date_time_tuple[1],
                               date_time_tuple[2],
                               date_time_tuple[3],
                               date_time_tuple[4],
                               date_time_tuple[5])
    elif len(date_time_tuple) == 7:
        dt = datetime.datetime(date_time_tuple[0],
                               date_time_tuple[1],
                               date_time_tuple[2],
                               date_time_tuple[3],
                               date_time_tuple[4],
                               date_time_tuple[5],
                               date_time_tuple[6] * 1000)
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
        execaddr = loadexec[0]
    if loadaddr and (loadaddr & 0xFFF00000) == 0xFFF00000:
        return ((loadaddr & 0xFF) << 32) | execaddr
    return None


def quin_to_loadexec(quin, filetype=0xFFF):
    """
    Return the load/exec for a given quin and filetype
    """
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

    def __init__(self, filename="NoName", date_time=(1980, 1, 1, 0, 0, 0), zipinfo=None, nfs_encoding=True):
        """
        Construct a new ZipInfoRISCOS object, either based on an existing zip_info or from scratch.

        @param filename:        Filename this refers to in the archive
        @param date_time:       Tuple of the date-time (6 values)
        @param zipinfo:         ZipInfo to base this object on
        @param nfs_encoding:    Whether zip filenames should use the NFS filename encoding of:
                                    * `,xxx` => filetype
                                    * `,llllllll,eeeeeeee` => load and exec address
        """
        super(ZipInfoRISCOS, self).__init__(filename, date_time)
        if zipinfo:
            # They wanted to pre-populate from an existing ZipInfo object.
            # Use the __slots__ element because this gives all the fields it supports.
            # If the implmentation changes, more consideration to reading the source
            # object will be required.
            for field in zipinfo.__class__.__slots__:
                if field != 'extra':
                    setattr(self, field, getattr(zipinfo, field, None))
            # Always populate the extra field last, as this modifies the existing fields
            # based on what the RISC OS extra field contains
            self.extra = zipinfo.extra

        self._nfs_encoding = nfs_encoding

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

        # We either have the index we need to modify, OR we know that we need to append it.
        new_data = struct.pack('<IIIII', self.riscos_loadaddr, self.riscos_execaddr, self.riscos_attr, 0)
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
        #   4 bytes: exec address (little endian)
        #   4 bytes: load address (little endian)
        #   4 bytes: attributes (little endian)
        #   4 bytes: length (little endian)
        #   4 bytes: reserved for future expansion, 0 on write (little endian)

        chunks = self.extract_extra_fields(value or b'')
        for (header_id, data) in chunks:
            if header_id == self.header_id_riscos:
                # This is a RISC OS chunk we may need to process
                (riscos_type,) = struct.unpack('<I', data[:4])
                if riscos_type == self.header_id_riscos_spark:
                    (loadaddr, execaddr, attr, zero) = struct.unpack('<IIII', data[4:])
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
            self.date_time = (dt.year, dt.month, dt.day,
                              dt.hour, dt.minute, dt.second)
            self.riscos_date_time = (dt.year, dt.month, dt.day,
                                     dt.hour, dt.minute, dt.second, (dt.microsecond / 1000))

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
            dirname, _ = self.filename.rsplit('/')
            if '/' in dirname:
                dirname, _ = dirname.split('/', 1)
            filetype = self.filetype_parentdir_mappings.get(dirname.lower())
            if filetype is not None:
                return filetype

        return None

    ################ NFS encoding setting
    @property
    def nfs_encoding(self):
        return self._nfs_encoding

    @nfs_encoding.setter
    def nfs_encoding(self, value):
        if self._nfs_encoding != bool(value):
            # FIXME: Update fields if necessary
            pass
        self._nfs_encoding = bool(value)

    ################ Filename
    @property
    def riscos_filename(self):
        # FIXME: Convert filename to RISC OS format
        return self.filename

    @riscos_filename.setter
    def riscos_filename(self, value):
        # FIXME: Convert filename from RISC OS format to format for zipfile
        pass

    ################ Date/time
    @property
    def riscos_date_time(self):
        # FIXME: Convert date_time object to RISC OS format
        if self._riscos_loadaddr is not None:
            quin = loadexec_to_quin(self._riscos_loadaddr, self._riscos_execaddr or 0)
            dt = quin_to_datetime(quin)

            return (dt.year, dt.month, dt.day,
                    dt.hour, dt.minute, dt.second, (dt.microsecond / 1000))

        # Fall back to the standard format, with 0 for centiseconds
        return tuple(list(self.date_time) + [0])

    @riscos_date_time.setter
    def riscos_date_time(self, value):
        # Convert timestamp from RISC OS format to format for zipfile
        self._riscos_date_time = value
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
            if (self._riscos_loadaddr & 0xFFF00000) == 0xFFF00000:
                # Can replace into the current load address
                loadaddr = (self._riscos_loadaddr & 0xFFF000FF) | (self.riscos_filetype << 8)
                return loadaddr

        # No load address given; so we have to generate one from the date_time
        dt = tuple_to_datetime(self.riscos_date_time)
        quin = datetime_to_quin(dt)
        (loadaddr, _) = quin_to_loadexec(quin, filetype=self.riscos_filetype)
        return loadaddr

    @riscos_loadaddr.setter
    def riscos_loadaddr(self, value):
        self._riscos_loadaddr = value

        if self._riscos_objtype == 1:
            # If this is a file, we can update the filetype
            if self._riscos_loadaddr is not None and \
               (self._riscos_loadaddr & 0xFFF00000) == 0xFFF00000:
                # This object has a filetype
                self._riscos_filetype = (value >> 8) & 0xFFF
        self._update_date_time()

        self._riscos_present = True

    ################ Exec address
    @property
    def riscos_execaddr(self):
        # Convert time/filetype to RISC OS format
        if self._riscos_execaddr is not None:
            # Exec address exists.
            return self._riscos_execaddr

        # No exec address given; so we have to generate one from the date_time
        dt = tuple_to_datetime(self.riscos_date_time)
        quin = datetime_to_quin(dt)
        (_, execaddr) = quin_to_loadexec(quin)
        return execaddr

    @riscos_execaddr.setter
    def riscos_execaddr(self, value):
        self._riscos_execaddr = value
        # FIXME: Update the date_time and filetype
        self._riscos_present = True

    ################ File attributes
    @property
    def riscos_attr(self):
        # FIXME: Convert attributes to RISC OS file attributes
        return self._riscos_attr

    @riscos_attr.setter
    def riscos_attr(self, value):
        # FIXME: Convert file attributes from RISC OS format to format for zipfile
        pass

    ################ File type
    @property
    def riscos_filetype(self):
        # FIXME: Convert information to RISC OS file type
        if self._riscos_filetype is None:
            # No filetype currently set, so we'll infer one.

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
        return self._riscos_filetype

    @riscos_filetype.setter
    def riscos_filetype(self, value):
        # FIXME: Convert filetype from RISC OS format to format for zipfile
        # FIXME: Update the load/exec
        pass

    @property
    def riscos_objtype(self):
        # FIXME: Convert information to RISC OS file type
        if self._riscos_objtype:
            return self._riscos_objtype

        if self.external_attr & self.external_attr_msdos_directory:
            return 2;
        return 1

    @riscos_objtype.setter
    def riscos_objtype(self, value):
        # Convert object type from RISC OS format to format for zipfile
        if self._riscos_objtype == 2:
            if self._riscos_filetype is not None:
                self._riscos_filetype = 0x1000

        if self._riscos_objtype == 2:
            # The external attributes are defined to contain attributes based on the creator type.
            # However, most (all?) implementations treat the lower 8 bits as the MS DOS attributes,
            # with only the top 16 bits being set to the unix mode (which is not defined in the
            # pkzip spec.
            # * InfoZip treats the amiga as special in creating with dedicated Amiga-only attributes.
            # * InfoZip checks if the top 16 bits are consistent with the write and directory
            #   bits, and if so uses them as the file mode.
            # * Python treats the top 16 bits of the external attributes as the file mode if no
            #   bits are set in the whole word.
            # * Zipper treats the MSDOS bit as the directory specifier, regardless of creator.
            self.external_attr |= self.external_attr_msdos_directory
            # * InfoZip expects directories to be terminated by a '/' character; if they're not it
            #   doesn't mind, but the implication is that others may expect it.
            # * Python always generates names with a '/' on the end if they're marked as a directory.
            if not self.filename.endswith('/'):
                self.filename += '/'
        else:
            self.external_attr &= ~self.external_attr_msdos_directory
            if self.filename.endswith('/'):
                self.filename = self.filename[:-1]
