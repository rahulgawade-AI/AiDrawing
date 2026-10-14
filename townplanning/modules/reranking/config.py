from __future__ import annotations

import torch


class RerankingConfig:
    """
    Configuration for the reranking module.
    """

    # Cross Encoder model
    MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # Candidate retrieval
    DEFAULT_SEARCH_TOP_K = 50

    # Final results after reranking
    DEFAULT_RERANK_TOP_K = 8

    # Ignore weak matches
    MIN_SCORE = -100.0

    # Batch inference
    BATCH_SIZE = 32

    # Lazy loading
    LAZY_LOAD = True

    # Device selection
    if torch.cuda.is_available():
        DEVICE = "cuda"
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        DEVICE = "mps"
    else:
        DEVICE = "cpu"