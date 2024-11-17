import fnmatch
import tempfile
from typing import Any, Dict, Generator, List

from admin_async_upload.storage import ResumableStorage
from django.core.files import File
from django.core.files.storage import Storage
from django.utils.functional import cached_property


class ResumableFile:
    """
    Handles file saving and processing for resumable uploads.
    """

    def __init__(self, field: Any, user: Any, params: Dict[str, str]) -> None:
        self.field = field  # A Django FileField or similar
        self.user = user  # Typically a User instance
        self.params = params
        self.chunk_suffix = "_part_"

    @cached_property
    def resumable_storage(self) -> ResumableStorage:
        return ResumableStorage()

    @cached_property
    def persistent_storage(self) -> Storage:
        return self.resumable_storage.get_persistent_storage()

    @cached_property
    def chunk_storage(self) -> Storage:
        return self.resumable_storage.get_chunk_storage()

    @property
    def storage_filename(self) -> str:
        return self.resumable_storage.full_filename(self.filename, self.upload_to)

    @property
    def upload_to(self) -> str:
        if callable(self.field.upload_to):
            return self.field.upload_to(None, self.filename)
        return self.field.upload_to

    @property
    def chunk_exists(self) -> bool:
        """
        Checks if the requested chunk exists.
        """
        return self.chunk_storage.exists(self.current_chunk_name) and self.chunk_storage.size(
            self.current_chunk_name
        ) == int(self.params.get("resumableCurrentChunkSize", "0"))

    @property
    def chunk_names(self) -> List[str]:
        """
        Iterates over all stored chunks.
        """
        files = sorted(self.chunk_storage.listdir("")[1])
        return [file for file in files if fnmatch.fnmatch(file, f"{self.filename}{self.chunk_suffix}*")]

    @property
    def current_chunk_name(self) -> str:
        return f"{self.filename}{self.chunk_suffix}{str(self.params.get('resumableChunkNumber', '0')).zfill(4)}"

    def chunks(self) -> Generator[bytes, None, None]:
        """
        Iterates over all stored chunks.
        """
        for chunk_name in self.chunk_names:
            with self.chunk_storage.open(chunk_name, "rb") as chunk_file:
                yield chunk_file.read()

    def delete_chunks(self) -> None:
        """
        Deletes all stored chunks.
        """
        for chunk in self.chunk_names:
            self.chunk_storage.delete(chunk)

    @property
    def file(self) -> tempfile.NamedTemporaryFile:
        """
        Merges file and returns its file pointer.
        """
        if not self.is_complete:
            raise Exception("Chunk(s) still missing")
        outfile = tempfile.NamedTemporaryFile("w+b")
        for chunk in self.chunks():
            outfile.write(chunk)
        outfile.seek(0)  # Reset the file pointer
        return outfile

    @property
    def filename(self) -> str:
        """
        Gets the filename.
        """
        filename = self.params.get("resumableFilename", "")
        if "/" in filename:
            raise Exception("Invalid filename")
        return f"{self.params.get('resumableTotalSize', '0')}_{filename}"

    @property
    def is_complete(self) -> bool:
        """
        Checks if all chunks are already stored.
        """
        return int(self.params.get("resumableTotalSize", "0")) == self.size

    def process_chunk(self, file: File) -> None:
        """
        Saves chunk to chunk storage.
        """
        if self.chunk_storage.exists(self.current_chunk_name):
            self.chunk_storage.delete(self.current_chunk_name)
        self.chunk_storage.save(self.current_chunk_name, file)

    @property
    def size(self) -> int:
        """
        Gets size of all chunks combined.
        """
        return sum(self.chunk_storage.size(chunk) for chunk in self.chunk_names)

    def collect(self) -> str:
        """
        Collects and saves the file to persistent storage.
        """
        with self.file as merged_file:
            actual_filename = self.persistent_storage.save(self.storage_filename, File(merged_file))
        self.delete_chunks()
        return actual_filename
