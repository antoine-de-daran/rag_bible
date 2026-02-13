import numpy as np
import pytest

from config import EMBEDDING_DIMENSION


@pytest.mark.unit
def test_encode_texts_shape_with_mock(sample_texts: list[str]) -> None:
    """encode_texts returns array with correct shape."""
    from embeddings import encode_texts

    class FakeModel:
        def encode(self, texts: list[str], **kwargs: object) -> np.ndarray:
            return (
                np.random.default_rng(42)
                .random((len(texts), EMBEDDING_DIMENSION))
                .astype(np.float32)
            )

    result = encode_texts(FakeModel(), sample_texts, show_progress=False)  # type: ignore[arg-type]
    assert result.shape == (len(sample_texts), EMBEDDING_DIMENSION)


@pytest.mark.unit
def test_encode_texts_replaces_newlines() -> None:
    """Newlines in text are replaced with spaces before encoding."""
    from embeddings import encode_texts

    captured: list[list[str]] = []

    class SpyModel:
        def encode(self, texts: list[str], **kwargs: object) -> np.ndarray:
            captured.append(list(texts))
            return np.zeros((len(texts), EMBEDDING_DIMENSION), dtype=np.float32)

    encode_texts(SpyModel(), ["hello\nworld"], show_progress=False)  # type: ignore[arg-type]
    assert captured[0] == ["hello world"]


@pytest.mark.integration
def test_load_embedding_model_returns_sentence_transformer() -> None:
    """load_embedding_model returns a SentenceTransformer instance."""
    from sentence_transformers import SentenceTransformer

    from embeddings import load_embedding_model

    model = load_embedding_model()
    assert isinstance(model, SentenceTransformer)


@pytest.mark.integration
def test_load_embedding_model_custom_name() -> None:
    """load_embedding_model accepts a custom model name."""
    from sentence_transformers import SentenceTransformer

    from embeddings import load_embedding_model

    model = load_embedding_model("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    assert isinstance(model, SentenceTransformer)


@pytest.mark.integration
def test_encode_texts_shape(sample_texts: list[str]) -> None:
    """encode_texts returns array with correct shape using real model."""
    from embeddings import encode_texts, load_embedding_model

    model = load_embedding_model()
    result = encode_texts(model, sample_texts, show_progress=False)
    assert result.shape == (len(sample_texts), EMBEDDING_DIMENSION)


@pytest.mark.integration
def test_encode_texts_normalized(sample_texts: list[str]) -> None:
    """Embeddings are L2-normalized (norm ~1.0)."""
    from embeddings import encode_texts, load_embedding_model

    model = load_embedding_model()
    result = encode_texts(model, sample_texts, show_progress=False)
    norms = np.linalg.norm(result, axis=1)
    np.testing.assert_allclose(norms, 1.0, atol=1e-5)


@pytest.mark.integration
def test_load_cross_encoder_returns_cross_encoder() -> None:
    """load_cross_encoder returns a CrossEncoder instance."""
    from sentence_transformers import CrossEncoder

    from embeddings import load_cross_encoder

    model = load_cross_encoder()
    assert isinstance(model, CrossEncoder)
