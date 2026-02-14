"""Model abstraction layer for embedding and cross-encoder models."""

import numpy as np
from sentence_transformers import CrossEncoder, SentenceTransformer

import config


def load_embedding_model(model_name: str | None = None) -> SentenceTransformer:
    """Load a SentenceTransformer embedding model.

    Parameters
    ----------
    model_name : str or None
        HuggingFace model identifier. Defaults to ``config.EMBEDDING_MODEL``.

    Returns
    -------
    SentenceTransformer
        Loaded embedding model.
    """
    name = model_name or config.EMBEDDING_MODEL
    return SentenceTransformer(name)


def encode_texts(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int = 64,
    show_progress: bool = True,
) -> np.ndarray:
    """Encode texts into L2-normalized embeddings.

    Parameters
    ----------
    model : SentenceTransformer
        Loaded embedding model.
    texts : list[str]
        Texts to encode. Newlines are replaced with spaces.
    batch_size : int
        Encoding batch size.
    show_progress : bool
        Whether to show a progress bar.

    Returns
    -------
    np.ndarray
        Array of shape ``(len(texts), dimension)`` with L2-normalized embeddings.
    """
    cleaned = [t.replace("\n", " ") for t in texts]
    embeddings: np.ndarray = model.encode(
        cleaned,
        batch_size=batch_size,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )
    return embeddings


def load_cross_encoder(model_name: str | None = None) -> CrossEncoder:
    """Load a CrossEncoder reranking model.

    Parameters
    ----------
    model_name : str or None
        HuggingFace model identifier. Defaults to ``config.CROSS_ENCODER_MODEL``.

    Returns
    -------
    CrossEncoder
        Loaded cross-encoder model.
    """
    name = model_name or config.CROSS_ENCODER_MODEL
    model: CrossEncoder = CrossEncoder(name)
    return model
