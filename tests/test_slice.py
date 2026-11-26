import json

from evidenceai.constants import REGISTERED_SEED
from evidenceai.evaluation import evaluate
from evidenceai.frames import FRAMES, TEMPORAL_FRAME
from evidenceai.investigate import build_answer
from evidenceai.pipeline import RegistrationDeviation, run_slice
from evidenceai.readmodel import latest_claims, object_text
from evidenceai.store import Database, rows
from evidenceai.synth import generate_corpus


def test_generated_lines_match_at_most_one_frame(tmp_path) -> None:
    manifest = generate_corpus(tmp_path)
    assert manifest["document_count"] == 50
    assert manifest["corpus_label"] == "synthetic"
    for document in manifest["documents"]:
        text = (tmp_path / document["filename"]).read_text(encoding="utf-8")
        assert "NOT A REAL TRIAL" in text
        for line in text.splitlines():
            hits = [frame.frame_id for frame in FRAMES if frame.regex().match(line)]
            temporal = TEMPORAL_FRAME.regex().match(line) is not None
            assert len(hits) + int(temporal) <= 1


def test_slice_acceptance(tmp_path) -> None:
    first = run_slice(tmp_path / "slice", system_time="2026-11-26T16:30:00+00:00")
    second = run_slice(tmp_path / "slice", system_time="2026-11-26T16:30:00+00:00")
    assert first["event_count"] == second["event_count"]
    assert first["counts"]["documents"] == 50
    assert first["counts"]["quarantined_files"] == 0

    db = Database(first["db_path"], readonly=True)
    try:
        for version in rows(
            db.conn,
            """
            SELECT v.content_hash, s.char_start, s.char_end, s.text
            FROM spans s
            JOIN document_versions v ON v.document_version_id = s.document_version_id
            """,
        ):
            text = object_text(db.path, version["content_hash"])
            assert text[version["char_start"] : version["char_end"]] == version["text"]
        raw_tokens = {row["raw_token"] for row in latest_claims(db.conn)}
        assert "24" not in raw_tokens
        assert "0.61" not in raw_tokens
        assert "0.89" not in raw_tokens
        summary = evaluate(db)
        supported = build_answer(db.conn, "What sample size was reported for SYNTH-001?")
        contradicted = build_answer(db.conn, "What sample size was reported for SYNTH-005?")
        insufficient = build_answer(
            db.conn, "What all-cause mortality count was reported for SYNTH-001?"
        )
        as_of = build_answer(
            db.conn,
            "What sample size was reported for SYNTH-005?",
            assertion_time_lte="2022-01-01",
        )
    finally:
        db.close()

    assert summary["extraction"]["unexpected_misses"] == 0
    assert summary["extraction"]["false_extractions"] == 0
    assert summary["extraction"]["value_mismatches"] == 0
    assert summary["extraction"]["known_unsupported_frames"] == 1
    assert summary["extraction"]["unsupported_frames_accidentally_extracted"] == 0
    assert summary["pairs"]["unassessed"] == 0
    assert summary["directional_expectation_met"] is True
    assert summary["rule_false_positives_at_least_one"] is True
    assert supported["state"] == "supported"
    assert contradicted["state"] == "contradicted"
    assert insufficient["state"] == "insufficient"
    assert as_of["state"] == "supported"
    assert "latent" not in json.dumps(supported)
    assert "latent" not in json.dumps(contradicted)
    for quotation in contradicted["quotations"]:
        assert quotation["verifier_pass"] is True
        assert quotation["content_hash"]

    db = Database(first["db_path"])
    try:
        before = db.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        db.rebuild()
        after = db.conn.execute("SELECT COUNT(*) FROM claims").fetchone()[0]
        assert before == after
        assert before > 0
    finally:
        db.close()


def test_seed_other_than_registered_is_refused(tmp_path) -> None:
    try:
        run_slice(tmp_path / "slice", seed=REGISTERED_SEED + 1)
    except RegistrationDeviation:
        return
    raise AssertionError("A non-registered seed was accepted.")
