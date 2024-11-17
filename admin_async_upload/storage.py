import datetime
import posixpath
from typing import Any

from django.conf import settings
from django.core.files.storage import Storage, storages


class ResumableStorage:
    """
    Handles chunk and persistent storage for resumable uploads.
    """

    def __init__(self) -> None:
        self.persistent_storage_key: str = getattr(settings, "ADMIN_RESUMABLE_STORAGE", "default")
        self.chunk_storage_key: str = getattr(settings, "ADMIN_RESUMABLE_CHUNK_STORAGE", "default")

    def get_chunk_storage(self, *args: Any, **kwargs: Any) -> Storage:
        """
        Returns the chunk storage backend specified in settings.
        Defaults to the default storage if not specified.
        """
        storage = storages[self.chunk_storage_key]
        if not isinstance(storage, Storage):
            raise ValueError(f"{self.chunk_storage_key} is not a valid Storage backend.")
        return storage

    def get_persistent_storage(self, *args: Any, **kwargs: Any) -> Storage:
        """
        Returns the persistent storage backend specified in settings.
        Defaults to the default storage if not specified.
        """
        storage = storages[self.persistent_storage_key]
        if not isinstance(storage, Storage):
            raise ValueError(f"{self.persistent_storage_key} is not a valid Storage backend.")
        return storage

    def full_filename(self, filename: str, upload_to: str) -> str:
        """
        Generates the full filename for the file in persistent storage.
        """
        dirname: str = datetime.datetime.now().strftime(upload_to)
        full_path: str = posixpath.join(dirname, filename)
        return self.get_persistent_storage().generate_filename(full_path)
