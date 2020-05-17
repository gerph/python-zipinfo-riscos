# Python ZipInfo processing for RISC OS archives

This repository contains a subclass of ZipInfo which is able to both parse the extra field used by RISC OS Zip archives, and generate these extra fields. This allows RISC OS archives to be worked with on non-RISC OS systems (or on RISC OS, if needed).

Features:

* Supports reading RISC OS style file properties, synthesised if necessary:
    * `riscos_filename`: RISC OS format filename
    * `riscos_date_time`: tuple like `date_time`, but with centiseconds on the end
    * `riscos_objtype`: File or directory object type
    * `riscos_loadaddr`: Load address
    * `riscos_execaddr`: Exec address
    * `riscos_filetype`: RISC OS filetype number
    * `riscos_attr`: RISC OS attributes value
* All properties are mutable, and cause the extra field to be regenerated, updating the base properties as needed.
* Supports reading and writing the extra field, or using the NFS filename encoding format for transfer to other platforms.
* Configurable (by subclassing) encoding used for RISC OS filenames.
* Configurable (by subclassing) filetype inferrence rules, using extension, and parent directory name.
* Configurable (by subclassing) use of MimeMap module on RISC OS (not currently implemented, but the stub is there for overriding).


## Usage

The rozipinfo.py module can be imported into projects. It has not been added to PyPI yet.

The example code `showzip.py` demonstrates the use of the ZipInfoRISCOS module for reading zip archives.

For reading, it is expected that users will either enumerate objects in a zipfile and create a list of ZipInfo objects with `ZipFile.infolist()`, which they can then pass to ZipInfoRISCOS to handle the RISC OS specific
extensions.

For writing, it is expected that users will create new ZipInfoRISCOS objects and pass these directly to the `ZipFile.writestr()` method.


## Tests

Tests exist to show that the module is working properly, intended for use on GitLab.
Code coverage is about 84% at present; feature coverage is a bit lower, as not all the intended functionality is exercised by the tests.
