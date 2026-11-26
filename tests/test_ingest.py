from evidenceai.ingest import ingest_file
from evidenceai.materialize import materialize_extractions
from evidenceai.store import Database


def _run(tmp_path, name: str, payload: bytes, limit: int = 1000) -> Database:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / name).write_bytes(payload)
    db = Database(tmp_path / "evidence.db")
    ingest_file(
        db,
        corpus,
        corpus / name,
        tmp_path / "objects",
        "run_test",
        "2026-11-26T00:00:00+00:00",
        limit,
    )
    db.commit()
    return db


def test_empty_non_utf8_and_suffix_are_quarantined(tmp_path) -> None:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "empty.txt").write_bytes(b"")
    (corpus / "bad.txt").write_bytes(b"\xff\xfe")
    (corpus / "notes.json").write_text("{}", encoding="utf-8")
    db = Database(tmp_path / "evidence.db")
    for name in ("empty.txt", "bad.txt", "notes.json"):
        ingest_file(
            db,
            corpus,
            corpus / name,
            tmp_path / "objects",
            "run_test",
            "2026-11-26T00:00:00+00:00",
            1000,
        )
    db.commit()
    reasons = {
        row[0]
        for row in db.conn.execute(
            "SELECT reason FROM file_observations WHERE status = 'quarantined'"
        )
    }
    documents = db.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    db.close()
    assert reasons == {"empty_file", "not_utf8", "unsupported_suffix"}
    assert documents == 0


def test_exact_duplicate_does_not_create_a_second_document(tmp_path) -> None:
    text = b"Language: en\nDocument type: registry\nTrial: SYNTH-001\n"
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.txt").write_bytes(text)
    (corpus / "b.txt").write_bytes(text)
    db = Database(tmp_path / "evidence.db")
    for name in ("a.txt", "b.txt"):
        ingest_file(
            db,
            corpus,
            corpus / name,
            tmp_path / "objects",
            "run_test",
            "2026-11-26T00:00:00+00:00",
            1000,
        )
    db.commit()
    documents = db.conn.execute("SELECT COUNT(*) FROM documents").fetchone()[0]
    duplicates = db.conn.execute(
        "SELECT COUNT(*) FROM file_observations WHERE status = 'exact_duplicate'"
    ).fetchone()[0]
    db.close()
    assert documents == 1
    assert duplicates == 1


def test_unsupported_language_ingests_without_claims(tmp_path) -> None:
    text = "\n".join(
        [
            "SYNTHETIC DOCUMENT",
            "Language: hi",
            "Document type: registry",
            "Trial: SYNTH-001",
            "Document date: 2021-02-01",
            "Source: Synthetic Registry",
            "",
            "This registry entry records planned enrollment of 240 participants.",
            "",
        ]
    )
    db = _run(tmp_path, "SYNTH-001__registry.txt", text.encode("utf-8"))
    materialize_extractions(db, "run_test", "2026-11-26T00:00:00+00:00")
    db.commit()
    claims = db.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
    warnings = db.conn.execute("SELECT warnings_json FROM document_versions").fetchone()[0]
    db.close()
    assert claims == 0
    assert "language_not_supported" in warnings
