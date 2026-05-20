"""Tests for the SQLite catalog."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from forgemaster.catalog import Catalog, GPUProfile
from forgemaster.scanner import ModelInfo


@pytest.fixture
def catalog():
    """Create an in-memory catalog for testing."""
    cat = Catalog(":memory:")
    yield cat
    cat.close()


@pytest.fixture
def persistent_catalog():
    """Create a file-based catalog for testing persistence."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        cat = Catalog(str(db_path))
        yield cat
        cat.close()


class TestCatalog:
    def test_create_catalog(self, catalog):
        assert catalog.conn is not None

    def test_add_model(self, catalog):
        model = ModelInfo(
            name="llama-7b",
            path="/models/llama-7b.gguf",
            size_bytes=4200000000,
            format="gguf",
            architecture="llama",
            parameters=7_000_000_000,
            quantization="Q4_0",
            vram_required_gb=5.2,
        )
        model_id = catalog.add_model(model)
        assert model_id > 0

    def test_get_model(self, catalog):
        model = ModelInfo(
            name="llama-7b",
            path="/models/llama-7b.gguf",
            size_bytes=4200000000,
            format="gguf",
            architecture="llama",
        )
        model_id = catalog.add_model(model)

        result = catalog.get_model(model_id)
        assert result is not None
        assert result["name"] == "llama-7b"
        assert result["format"] == "gguf"
        assert result["architecture"] == "llama"
        assert result["size_bytes"] == 4200000000

    def test_get_model_not_found(self, catalog):
        result = catalog.get_model(9999)
        assert result is None

    def test_list_models(self, catalog):
        models = [
            ModelInfo(name="llama-7b", path="/m1", format="gguf", architecture="llama"),
            ModelInfo(name="mistral-7b", path="/m2", format="gguf", architecture="mistral"),
            ModelInfo(
                name="sd-v1.5",
                path="/m3",
                format="safetensors",
                architecture="stable-diffusion",
            ),
        ]
        for m in models:
            catalog.add_model(m)

        all_models = catalog.list_models()
        assert len(all_models) == 3

    def test_list_models_filter_format(self, catalog):
        models = [
            ModelInfo(name="llama-7b", path="/m1", format="gguf"),
            ModelInfo(name="sd-v1.5", path="/m2", format="safetensors"),
        ]
        for m in models:
            catalog.add_model(m)

        gguf_models = catalog.list_models(fmt="gguf")
        assert len(gguf_models) == 1
        assert gguf_models[0]["format"] == "gguf"

    def test_list_models_filter_architecture(self, catalog):
        models = [
            ModelInfo(name="llama-7b", path="/m1", architecture="llama"),
            ModelInfo(name="mistral-7b", path="/m2", architecture="mistral"),
        ]
        for m in models:
            catalog.add_model(m)

        llama_models = catalog.list_models(architecture="llama")
        assert len(llama_models) == 1
        assert llama_models[0]["architecture"] == "llama"

    def test_list_models_pagination(self, catalog):
        for i in range(5):
            catalog.add_model(ModelInfo(name=f"model-{i}", path=f"/m{i}"))

        page1 = catalog.list_models(limit=2, offset=0)
        assert len(page1) == 2

        page2 = catalog.list_models(limit=2, offset=2)
        assert len(page2) == 2

    def test_search_models(self, catalog):
        models = [
            ModelInfo(name="llama-7b-chat", path="/m1", architecture="llama"),
            ModelInfo(name="mistral-7b", path="/m2", architecture="mistral"),
            ModelInfo(name="llama-13b", path="/m3", architecture="llama"),
        ]
        for m in models:
            catalog.add_model(m)

        results = catalog.search_models("llama")
        assert len(results) == 2

    def test_search_models_by_path(self, catalog):
        model = ModelInfo(name="test", path="/models/llama/chat/model.gguf")
        catalog.add_model(model)

        results = catalog.search_models("chat")
        assert len(results) == 1

    def test_delete_model(self, catalog):
        model = ModelInfo(name="to-delete", path="/m1")
        model_id = catalog.add_model(model)

        assert catalog.delete_model(model_id) is True
        assert catalog.get_model(model_id) is None

    def test_delete_model_not_found(self, catalog):
        assert catalog.delete_model(9999) is False

    def test_add_model_with_tags_and_notes(self, catalog):
        model = ModelInfo(name="tagged-model", path="/m1")
        model_id = catalog.add_model(
            model,
            tags={"type": "chat", "language": "en"},
            notes="My favorite model",
        )

        result = catalog.get_model(model_id)
        assert result["tags"] == {"type": "chat", "language": "en"}
        assert result["notes"] == "My favorite model"

    def test_count_models(self, catalog):
        assert catalog.count_models() == 0

        for i in range(3):
            catalog.add_model(ModelInfo(name=f"model-{i}", path=f"/m{i}"))

        assert catalog.count_models() == 3

    def test_total_size_bytes(self, catalog):
        assert catalog.total_size_bytes() == 0

        catalog.add_model(ModelInfo(name="m1", path="/m1", size_bytes=1000))
        catalog.add_model(ModelInfo(name="m2", path="/m2", size_bytes=2000))

        assert catalog.total_size_bytes() == 3000


class TestGPUProfile:
    def test_add_gpu_profile(self, catalog):
        profile = GPUProfile(name="RTX 4090", vram_total_gb=24.0, vram_available_gb=22.0)
        profile_id = catalog.add_gpu_profile(profile)
        assert profile_id > 0

    def test_get_gpu_profiles(self, catalog):
        profile1 = GPUProfile(name="RTX 4090", vram_total_gb=24.0, vram_available_gb=22.0)
        profile2 = GPUProfile(name="RTX 3090", vram_total_gb=24.0, vram_available_gb=22.0)

        catalog.add_gpu_profile(profile1)
        catalog.add_gpu_profile(profile2)

        profiles = catalog.get_gpu_profiles()
        assert len(profiles) == 2
        assert all(isinstance(p, GPUProfile) for p in profiles)
        assert profiles[0].name == "RTX 3090"  # alphabetical

    def test_gpu_profile_defaults(self):
        profile = GPUProfile()
        assert profile.id is None
        assert profile.name == ""
        assert profile.vram_total_gb == 0.0
        assert profile.vram_available_gb == 0.0


class TestPersistentCatalog:
    def test_persistence(self, persistent_catalog):
        model = ModelInfo(name="persistent-model", path="/m1", format="gguf")
        model_id = persistent_catalog.add_model(model)

        # Close and reopen
        persistent_catalog.close()
        cat2 = Catalog(persistent_catalog.db_path)
        result = cat2.get_model(model_id)
        assert result is not None
        assert result["name"] == "persistent-model"
        cat2.close()
