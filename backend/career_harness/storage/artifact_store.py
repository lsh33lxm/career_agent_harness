from __future__ import annotations

import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

from career_harness.core.evidence.models import ArtifactClass


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    sha256: str
    byte_length: int
    path: Path


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, content: bytes, artifact_class: ArtifactClass) -> StoredArtifact:
        if artifact_class is ArtifactClass.CREDENTIAL_SESSION:
            raise ValueError("credential/session data cannot enter the ordinary artifact store")

        digest = hashlib.sha256(content).hexdigest()
        destination = self.root / digest[:2] / digest[2:4] / digest
        destination.parent.mkdir(parents=True, exist_ok=True)

        if not destination.exists():
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    dir=destination.parent, prefix=".artifact-", delete=False
                ) as handle:
                    handle.write(content)
                    handle.flush()
                    os.fsync(handle.fileno())
                    temporary_path = Path(handle.name)
                temporary_path.replace(destination)
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()

        return StoredArtifact(sha256=digest, byte_length=len(content), path=destination)

    def read(self, sha256: str) -> bytes:
        if len(sha256) != 64 or any(character not in "0123456789abcdef" for character in sha256):
            raise ValueError("invalid SHA-256 digest")
        return (self.root / sha256[:2] / sha256[2:4] / sha256).read_bytes()

