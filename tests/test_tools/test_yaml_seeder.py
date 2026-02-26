"""Tests for the YAML-to-KB seeder."""

import pytest
from pathlib import Path
from tools.processors.yaml_seeder import seed_from_yaml


@pytest.fixture
def fzj80_yaml():
    return Path(__file__).parent.parent.parent / "config" / "vehicles" / "fzj80.yaml"


class TestYAMLSeeder:
    """Test YAML config to document extraction."""

    def test_seed_produces_documents(self, fzj80_yaml):
        docs = seed_from_yaml(fzj80_yaml)
        assert len(docs) > 0

    def test_all_docs_have_required_fields(self, fzj80_yaml):
        docs = seed_from_yaml(fzj80_yaml)
        for doc in docs:
            assert "source" in doc
            assert "source_id" in doc
            assert "content" in doc
            assert "category" in doc
            assert doc["source"] == "yaml"
            assert len(doc["content"]) > 10

    def test_categories_valid(self, fzj80_yaml):
        from backend.services.rag import COLLECTION_CATEGORIES
        docs = seed_from_yaml(fzj80_yaml)
        for doc in docs:
            assert doc["category"] in COLLECTION_CATEGORIES, \
                f"Invalid category: {doc['category']}"

    def test_engine_specs_extracted(self, fzj80_yaml):
        docs = seed_from_yaml(fzj80_yaml)
        engine_docs = [d for d in docs if d["category"] == "engine"]
        assert len(engine_docs) >= 3  # specs + fluids + maintenance
        # Should contain engine code
        assert any("1FZ-FE" in d["content"] for d in engine_docs)
        # Should contain oil capacity
        assert any("6.8" in d["content"] for d in engine_docs)

    def test_common_issues_extracted(self, fzj80_yaml):
        docs = seed_from_yaml(fzj80_yaml)
        issue_docs = [d for d in docs if d["category"] == "forum_troubleshoot"]
        assert len(issue_docs) >= 3  # head gasket, birfield, charcoal, frame rust, PS pump
        assert any("Head gasket" in d["content"] or "HEAD_GASKET" in d["content"] for d in issue_docs)

    def test_modifications_extracted(self, fzj80_yaml):
        docs = seed_from_yaml(fzj80_yaml)
        mod_docs = [d for d in docs if d["category"] == "forum_mods"]
        assert len(mod_docs) >= 5
        assert any("OME" in d["content"] or "Old Man Emu" in d["content"] for d in mod_docs)

    def test_drivetrain_extracted(self, fzj80_yaml):
        docs = seed_from_yaml(fzj80_yaml)
        dt_docs = [d for d in docs if d["category"] == "drivetrain"]
        assert len(dt_docs) >= 3  # transmission, transfer case, axles
        assert any("A442F" in d["content"] for d in dt_docs)

    def test_jsonl_output(self, fzj80_yaml, tmp_path):
        import json
        output = tmp_path / "test.jsonl"
        docs = seed_from_yaml(fzj80_yaml, output_jsonl=output)
        assert output.exists()

        # Parse back and verify
        lines = output.read_text().strip().split("\n")
        assert len(lines) == len(docs)
        for line in lines:
            parsed = json.loads(line)
            assert "source" in parsed
            assert "content" in parsed
