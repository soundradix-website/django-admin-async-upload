import fnmatch
import os.path
import posixpath
import tempfile

from django.conf import settings
from django.core.files.storage import storages
from django.core.files.uploadedfile import UploadedFile
from django.utils.encoding import force_str


class ResumableFile:
    """
    Handles file saving and processing.
    It must only have access to chunk storage where it saves file chunks.
    When all chunks are uploaded, it collects and merges them, returning a temporary file pointer
    that can be used to save the complete file to persistent storage.
    """

    def __init__(self, field, user, params):
        self.field = field
        self.user = user
        self.params = params
        self.chunk_suffix = "_part_"

        self.chunk_storage_name = getattr(settings, "ADMIN_RESUMABLE_CHUNK_STORAGE", "default")
        self.persistent_storage_name = getattr(settings, "ADMIN_RESUMABLE_STORAGE", "default")
        self.chunks_subdirectory = getattr(settings, "ADMIN_RESUMABLE_CHUNKS_SUBDIRECTORY", "chunks")

        self.chunk_storage = storages[self.chunk_storage_name]
        self.field_storage = storages[self.persistent_storage_name]

    @property
    def storage_filename(self):
        """
        Generates a valid and available filename for the complete file
        in the persistent storage, ensuring proper handling of the upload_to logic.
        """
        if callable(self.field.upload_to):
            # Call the function to determine the path
            raw_path = self.field.upload_to(None, self.filename)
        elif isinstance(self.field.upload_to, str):
            # Use the provided path directly
            raw_path = posixpath.join(self.field.upload_to, self.filename)
        else:
            raise ValueError("`upload_to` must be a string or callable.")

        # Ensure directory structure is preserved, but sanitize the base filename
        directory, base_filename = posixpath.split(raw_path)
        sanitized_filename = self.field_storage.get_valid_name(base_filename)

        # Reassemble the full path
        full_path = posixpath.join(directory, sanitized_filename)

        # Ensure the filename is available in the storage
        available_path = self.field_storage.get_available_name(full_path)

        return available_path

    @property
    def chunk_exists(self):
        """
        Checks if the requested chunk exists.
        """
        expected_size = int(self.params.get("resumableCurrentChunkSize", 0))
        return (
            self.chunk_storage.exists(self.current_chunk_name)
            and self.chunk_storage.size(self.current_chunk_name) == expected_size
        )

    @property
    def chunk_names(self):
        """
        Returns a list of all stored chunks for the current file in the configured 'chunks' subdirectory.
        """
        chunks = []
        directory, _ = posixpath.split(self.current_chunk_name)
        files = self.chunk_storage.listdir(directory)[1]  # [1] gives the list of files
        pattern = f"{self.filename}{self.chunk_suffix}*"
        for file in files:
            if fnmatch.fnmatch(file, pattern):
                chunks.append(posixpath.join(directory, file))
        return sorted(chunks)

    @property
    def current_chunk_name(self):
        """
        Returns the full path for the current chunk, including a configurable subdirectory for chunks.
        """
        user_directory = f"user_{self.user.id}" if self.user else "anonymous"
        chunk_subdirectory = posixpath.join(self.chunks_subdirectory, user_directory)
        chunk_number = self.params.get("resumableChunkNumber", "1").zfill(4)
        return posixpath.join(chunk_subdirectory, f"{self.filename}{self.chunk_suffix}{chunk_number}")

    def chunks(self):
        """
        Iterates over all stored chunks.
        """
        for chunk_name in self.chunk_names:
            with self.chunk_storage.open(chunk_name, "rb") as chunk_file:
                yield chunk_file.read()

    def delete_chunks(self):
        for chunk in self.chunk_names:
            self.chunk_storage.delete(chunk)

    @property
    def file(self):
        """
        Merges file and returns its file pointer.
        """
        if not self.is_complete:
            raise Exception("Chunk(s) still missing")
        outfile = tempfile.NamedTemporaryFile("w+b")
        for chunk_data in self.chunks():
            outfile.write(chunk_data)
        outfile.seek(0)
        return outfile

    @property
    def filename(self):
        """
        Gets the sanitized filename.
        """
        filename = self.params.get("resumableFilename", "")
        filename = os.path.basename(filename)
        if not filename:
            raise Exception("Invalid filename")
        total_size = self.params.get("resumableTotalSize", "0")
        value = f"{total_size}_{filename}"
        return value

    @property
    def is_complete(self):
        """
        Checks if all chunks are already stored.
        """
        return int(self.params.get("resumableTotalSize", 0)) == self.size

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
            name=self.params.get("resumableFilename"),
            content_type=self.params.get("resumableType", "text/plain"),
            size=int(self.params.get("resumableTotalSize", 0)),
        )
        actual_filename = self.field_storage.save(self.storage_filename, file_data)
        self.delete_chunks()
        return actual_filename
