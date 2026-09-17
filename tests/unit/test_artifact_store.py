from pathlib import Path

import pytest

from career_harness.core.evidence.models import ArtifactClass
from career_harness.storage import ArtifactStore


def test_artifact_store_is_content_addressed_and_deduplicated(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    first = store.put(b"same content", ArtifactClass.PERSONAL)
    second = store.put(b"same content", ArtifactClass.PERSONAL)

    assert first == second
    assert store.read(first.sha256) == b"same content"
    assert len(list((tmp_path / "artifacts").rglob(first.sha256))) == 1


def test_credential_session_is_rejected(tmp_path: Path) -> None:
    store = ArtifactStore(tmp_path / "artifacts")

    with pytest.raises(ValueError, match="credential/session"):
        store.put(b"cookie", ArtifactClass.CREDENTIAL_SESSION)

