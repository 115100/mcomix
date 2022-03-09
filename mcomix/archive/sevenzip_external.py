# -*- coding: utf-8 -*-

""" 7z archive extractor. """

import os
import subprocess
import tempfile

from mcomix import process
from mcomix import log
from mcomix.archive import archive_base

# Filled on-demand by SevenZipArchive
_7z_executable = -1

class SevenZipArchive(archive_base.ExternalExecutableArchive):
    """ 7z file extractor using the 7z executable. """

    STATE_HEADER, STATE_LISTING, STATE_FOOTER = 1, 2, 3

    class EncryptedHeader(Exception):
        pass

    def __init__(self, archive):
        super(SevenZipArchive, self).__init__(archive)
        self._is_solid = False
        self._is_encrypted =  False
        self._contents = []

    def _get_executable(self):
        return SevenZipArchive._find_7z_executable()

    def _get_password_argument(self):
        if self._is_encrypted:
            self._get_password()
            return '-p' + self._password
        else:
            # Add an empty password anyway, to prevent deadlock on reading for
            # input if we did not correctly detect the archive is encrypted.
            return '-p'

    def _get_list_arguments(self):
        args = [self._get_executable(), 'l', '-slt', '-sccUTF-8']
        args.append(self._get_password_argument())
        args.extend(('--', self.archive))
        return args

    def _get_extract_arguments(self, list_file=None):
        args = [self._get_executable(), 'x', '-so', '-sccUTF-8']
        if list_file is not None:
            args.append('-i@' + list_file)
        args.append(self._get_password_argument())
        args.extend(('--', self.archive))
        return args

    def _parse_list_output_line(self, line):
        """ Start parsing after the first delimiter (bunch of - characters),
        and end when delimiters appear again. Format:
        Date <space> Time <space> Attr <space> Size <space> Compressed <space> Name"""

        if line.startswith('----------'):
            if self._state == self.STATE_HEADER:
                # First delimiter reached, start reading from next line.
                self._state = self.STATE_LISTING
            elif self._state == self.STATE_LISTING:
                # Last delimiter read, stop reading from now on.
                self._state = self.STATE_FOOTER

            return None

        if self._state == self.STATE_HEADER:
            if (line.startswith('Error:') or line.startswith('ERROR:')) and \
               line.endswith(': Can not open encrypted archive. Wrong password?'):
                self._is_encrypted = True
                raise self.EncryptedHeader()
            if 'Solid = +' == line:
                self._is_solid = True

        if self._state == self.STATE_LISTING:
            if line.startswith('Path = '):
                self._path = line[7:]
                return self._path
            if line.startswith('Size = '):
                filesize = int(line[7:])
                if filesize > 0:
                    self._contents.append((self._path, filesize))
            elif 'Encrypted = +' == line:
                self._is_encrypted = True

        return None

    def is_solid(self):
        return self._is_solid

    def iter_contents(self):
        if not self._get_executable():
            return

        # We'll try at most 2 times:
        # - the first time without a password
        # - a second time with a password if the header is encrypted
        for retry_count in range(2):
            #: Indicates which part of the file listing has been read.
            self._state = self.STATE_HEADER
            #: Current path while listing contents.
            self._path = None
            proc = subprocess.run(self._get_list_arguments(),
                stdout=subprocess.PIPE, stderr=process.STDOUT, encoding='utf-8')
            try:
                for line in proc.stdout.splitlines():
                    filename = self._parse_list_output_line(line.rstrip(os.linesep))
                    if filename is not None:
                        yield filename
            except self.EncryptedHeader:
                # The header is encrypted, try again
                # if it was our first attempt.
                if 0 == retry_count:
                    continue
            # Last and/or successful attempt.
            break

        self.filenames_initialized = True

    def extract(self, filename, destination_dir):
        """ Extract <filename> from the archive to <destination_dir>. """
        assert isinstance(filename, str) and \
                isinstance(destination_dir, str)

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        tmplistfile = tempfile.NamedTemporaryFile(prefix='mcomix.7z.', delete=False)
        try:
            desired_filename = self._original_filename(filename)
            if isinstance(desired_filename, str):
                desired_filename = desired_filename.encode('utf-8')

            tmplistfile.write(desired_filename + os.linesep.encode('utf-8'))
            tmplistfile.close()

            output = self._create_file(os.path.join(destination_dir, filename))
            try:
                proc = subprocess.run(
                    self._get_extract_arguments(list_file=tmplistfile.name),
                    stdout=output, stderr=subprocess.PIPE,
                    creationflags=process._get_creationflags())

                if len(proc.stderr) > 0:
                    log.error(_("Extraction of %(archivefile)s might have failed: %(error)s"),
                              {'archivefile': filename, 'error': proc.stderr.decode('utf-8')})
            finally:
                output.close()
        finally:
            os.unlink(tmplistfile.name)

    def iter_extract(self, entries, destination_dir):

        if not self._get_executable():
            return

        if not self.filenames_initialized:
            self.list_contents()

        proc = process.popen(self._get_extract_arguments())
        try:
            wanted = set(entries)
            for filename, filesize in self._contents:
                data = proc.stdout.read(filesize)
                if filename not in wanted:
                    continue
                new = self._create_file(os.path.join(destination_dir, filename))
                new.write(data)
                new.close()
                yield filename
                wanted.remove(filename)
                if 0 == len(wanted):
                    break

        finally:
            proc.stdout.close()
            proc.wait()

    @staticmethod
    def _find_7z_executable():
        """ Tries to start 7z, and returns either '7z' if
        it was started successfully or None otherwise. """
        global _7z_executable
        if _7z_executable == -1:
            _7z_executable = process.find_executable(('7z',))
        return _7z_executable

    @staticmethod
    def is_available():
        return bool(SevenZipArchive._find_7z_executable())


class TarArchive(SevenZipArchive):

    '''Special class for handling tar archives.

       Needed because for XZ archives, the technical listing
       does not contain the archive member name...
    '''

    def __init__(self, archive):
        super(TarArchive, self).__init__(archive)
        self._is_solid = True
        self._is_encrypted =  False

    def _get_extract_arguments(self, list_file=None):
        # Note: we ignore the list_file argument, which
        # contains our made up archive member name.
        return super(TarArchive, self)._get_extract_arguments()

    def iter_contents(self):
        if not self._get_executable():
            return
        self._state = self.STATE_HEADER
        # We make up a name that's guaranteed to be
        # recognized as an archive by MComix.
        self._path = 'archive.tar'
        proc = process.popen(self._get_list_arguments(), stderr=process.STDOUT)
        try:
            for line in proc.stdout:
                self._parse_list_output_line(line.rstrip(os.linesep))
        finally:
            proc.stdout.close()
            proc.wait()
        if self._contents:
            # The archive should not contain more than 1 member.
            assert 1 == len(self._contents)
            yield self._unicode_filename(self._path)
        self.filenames_initialized = True

# vim: expandtab:sw=4:ts=4
