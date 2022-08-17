# Python ZipInfo processing for RISC OS archives

This repository contains a pair of modules for handling the Zip archives with RISC OS information present.

The `rozipinfo` module provides a subclass of ZipInfo which is able to both parse the extra field used by RISC OS Zip archives, and generate these extra fields. This allows RISC OS archives to be worked with on non-RISC OS systems (or on RISC OS, if needed).

The `rozipfile` module builds on the `rozipinfo` module to allow the files to be extracted or created as a simple operation. It provide both a programatic and command line interface.

## Installing

The modules may be installed by copying them to where you need them, or through the package
manager:

    pip install rozipinfo

## `rozipinfo`

The `rozipinfo` module provides decoding for the RISC OS specific extra fields in the Zip Archives.
It can be used standalone as a module to convert the standard `zipfile.ZipInfo` objects into objects that have RISC OS properties extracted from the Zip file's extra field.

### Features

* Supports reading RISC OS style file properties, synthesised if necessary:
    * `riscos_filename`: RISC OS format filename, a `bytes` object in the configured encoding
    * `riscos_date_time`: tuple like `date_time`, but with centiseconds on the end
    * `riscos_objtype`: File or directory object type
    * `riscos_loadaddr`: Load address
    * `riscos_execaddr`: Exec address
    * `riscos_filetype`: RISC OS filetype number
    * `riscos_attr`: RISC OS attributes value
* Forces the `filename` to be unicode, having been decoded using the archive's encoding.
* All properties are mutable, and cause the extra field to be regenerated, updating the base properties as needed.
* Supports reading and writing the extra field, or using the NFS filename encoding format for transfer to other platforms.
* Configurable (by subclassing) encoding used for RISC OS filenames.
* Configurable (by subclassing) filetype inferrence rules, using extension, and parent directory name.
* Configurable (by subclassing) use of MimeMap module on RISC OS (not currently implemented, but the stub is there for overriding).

### Examples

The example code `showzip.py` demonstrates the use of the `ZipInfoRISCOS` module for reading zip archives.

For reading, it is expected that users will either enumerate objects in a zipfile and create a list of `ZipInfo` objects with `ZipFile.infolist()`, which they can then pass to `ZipInfoRISCOS` to handle the RISC OS specific extensions.

For writing, it is expected that users will create new `ZipInfoRISCOS` objects and pass these directly to the `ZipFile.writestr()` method.


## `rozipfile`

The rozipfile module builds upon the `rozipinfo` and works in a similar way to the regular `zipfile`.

### Listing files in the archive

The module allows the files to be listed as they might be in RISC OS:

    with RISCOSZipFile('ro-app.zip, 'r') as zh:
        zh.printdir()

The filenames can can be manually enumerated:

    with RISCOSZipFile('ro-app.zip, 'r') as zh:
        for zi in zh.infolist():
            print(zi.riscos_filename)


### Creating archives

The module allows the creation of archives of files on unix systems which are extractable on RISC OS with filetypes.

Creating a new zip archive containing an application directory and some files from the filesystem:

    with RISCOSZipFile('newzip.zip', 'w', base_dir='.') as rzh:
        rzh.add_dir('!MyApp')
        rzh.add_file('!MyApp/!Run,feb')
        rzh.add_file('!MyApp/!Sprites,ff9')
        rzh.add_file('!MyApp/!RunImage,ffb')

Or the files can be automatically traversed:

    with RISCOSZipFile('newzip.zip', 'w', base_dir='.') as rzh:
        rzh.add_to_zipfile('!MyApp')


### Extracting files from an archive

The module allows extracting the files from the RISC OS format archive, using the NFS filename
encoding.

    with RISCOSZipFile('ro-app.zip, 'r') as zh:
        zh.extractall(path='new-directory')

Individual files can alco be extracted, but filenames are in RISC OS format:

    with RISCOSZipFile('ro-app.zip, 'r') as zh:
        zh.extractall(path='!MyApp')


## Command line usage

The `rozipfile` module can be used to extract and create archives from the command line.

Listing an archive:

    python -m rozipfile --list <archive>

Creating an archive:

    python -m rozipfile [--chdir <dir>] --create <archive> <files>*

Extracting an archive:

    python -m rozipfile [--chdir <dir>] --extract <archive> <files>*

Producing a list of *SetType commands to restore filetypes from a badly extracted file:

    python -m rozipfile [--chdir <dir>] --settypes <archive>


### Default filetype

The default filetype for files that don't have any RISC OS extension information present (either as NFS-encoding or RISC OS extensions) is &FFD (Data). However, the switch `--default-filetype` can be used to default to a different type. Most commonly you may wish to set the default filetype to Text with `--default-filetype text`.


## Tests

Tests exist to show that the module is working properly, intended for use on GitLab.
Code coverage is about 84% at present; feature coverage is a bit lower, as not all the intended functionality is exercised by the tests.
