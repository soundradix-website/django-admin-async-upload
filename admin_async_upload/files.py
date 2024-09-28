# -*- coding: utf-8 -*-
import os.path
import fnmatch
import tempfile

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import FileSystemStorage, default_storage
from django.utils.module_loading import import_string


class ResumableFile(object):
    """
    Handles file saving and processing.
    It must only have access to chunk storage where it saves file chunks.
    When all chunks are uploaded it collects and merges them returning temporary file pointer
    that can be used to save the complete file to persistent storage.

    Chunk storage should preferably be some local storage to avoid traffic
    as files usually must be downloaded to server as chunks and re-uploaded as complete files.
    """

    def __init__(self, field, user, params):
        self.field = field
        self.user = user
        self.params = params
        self.chunk_suffix = "_part_"
        chunk_storage_class = getattr(settings, 'ADMIN_RESUMABLE_CHUNK_STORAGE', None)
        if chunk_storage_class is None:
            self.chunk_storage = FileSystemStorage()
        else:
            self.chunk_storage = import_string(chunk_storage_class)()
        self.field_storage = self.field.storage or default_storage

    @property
    def storage_filename(self):
        if isinstance(self.field.upload_to, str):
            return self.field_storage.generate_filename(os.path.join(self.field.upload_to, self.filename))
        else:
            # Note that there isn't really any way to have a valid instance
            # here so the upload file naming should not rely on it.
            unique_name = self.field.upload_to(None, self.filename)
            return self.field_storage.generate_filename(unique_name)

    @property
    def chunk_exists(self):
        """
        Checks if the requested chunk exists.
        """
        return self.chunk_storage.exists(self.current_chunk_name) and \
               self.chunk_storage.size(self.current_chunk_name) == int(self.params.get('resumableCurrentChunkSize', 0))

    @property
    def chunk_names(self):
        """
        Iterates over all stored chunks.
        """
        chunks = []
        files = sorted(self.chunk_storage.listdir('')[1])
        for file in files:
            if fnmatch.fnmatch(file, '%s%s*' % (self.filename,
                                                self.chunk_suffix)):
                chunks.append(file)
        return chunks

    @property
    def current_chunk_name(self):
        # TODO: add user identifier to chunk name
        return "%s%s%s" % (
            self.filename,
            self.chunk_suffix,
            self.params.get('resumableChunkNumber').zfill(4)
        )

    def chunks(self):
        """
        Iterates over all stored chunks.
        """
        # TODO: add user identifier to chunk name
        files = sorted(self.chunk_storage.listdir('')[1])
        for file in files:
            if fnmatch.fnmatch(file, '%s%s*' % (self.filename,
                                                self.chunk_suffix)):
                yield self.chunk_storage.open(file, 'rb').read()

    def delete_chunks(self):
        [self.chunk_storage.delete(chunk) for chunk in self.chunk_names]

    @property
    def file(self):
        """
        Merges file and returns its file pointer.
        """
        if not self.is_complete:
            raise Exception('Chunk(s) still missing')
        outfile = tempfile.NamedTemporaryFile("w+b")
        for chunk in self.chunk_names:
            outfile.write(self.chunk_storage.open(chunk).read())
        return outfile

    @property
    def filename(self):
        """
        Gets the filename.
        """
        # TODO: add user identifier to chunk name
        filename = self.params.get('resumableFilename')
        if '/' in filename:
            raise Exception('Invalid filename')
        value = "%s_%s" % (self.params.get('resumableTotalSize'), filename)
        return value

    @property
    def is_complete(self):
        """
        Checks if all chunks are already stored.
        """
        return int(self.params.get('resumableTotalSize')) == self.size

    def process_chunk(self, file):
        """
        Saves chunk to chunk storage.
        """
        if self.chunk_storage.exists(self.current_chunk_name):
            self.chunk_storage.delete(self.current_chunk_name)
        self.chunk_storage.save(self.current_chunk_name, file)

    @property
    def size(self):
        """
        Gets size of all chunks combined.
        """
        size = 0
        for chunk in self.chunk_names:
            size += self.chunk_storage.size(chunk)
        return size

    def collect(self):
        file_data = UploadedFile(
            self.file,
            name=self.params.get('resumableFilename'),
            content_type=self.params.get('resumableType', 'text/plain'),
            size=self.params.get('resumableTotalSize', 0))
        actual_filename = self.field_storage.save(self.storage_filename, file_data)
        self.delete_chunks()
        return actual_filename
