"""
Shared Surya inference manager.

Loads all Surya predictors once and shares them across the
application.

Thread-safe singleton.
"""

from __future__ import annotations

import logging
import threading
from typing import Optional

import torch

from surya.detection import DetectionPredictor
from surya.layout import LayoutPredictor
from surya.recognition import RecognitionPredictor
from surya.table_rec import TableRecPredictor

logger = logging.getLogger(__name__)


class SuryaInferenceManager:
    """
    Singleton responsible for loading and sharing Surya models.

    Models are expensive to initialize, so they should only be
    created once during the application lifetime.
    """

    _instance: Optional["SuryaInferenceManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "SuryaInferenceManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._initialized = False

        self.device = (
            "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )

        self.detection: DetectionPredictor | None = None
        self.recognition: RecognitionPredictor | None = None
        self.layout: LayoutPredictor | None = None
        self.table_rec: TableRecPredictor | None = None

    @property
    def initialized(self) -> bool:
        return self._initialized

    def initialize(self) -> None:
        """
        Load all Surya models.

        Safe to call multiple times.
        """

        if self._initialized:
            return

        logger.info(
            "Loading Surya models on %s...",
            self.device,
        )

        self.detection = DetectionPredictor()

        self.recognition = RecognitionPredictor()

        self.layout = LayoutPredictor()

        self.table_rec = TableRecPredictor()

        self._initialized = True

        logger.info("Surya models loaded successfully.")

    def shutdown(self) -> None:
        """
        Release model references.
        """

        logger.info("Releasing Surya models...")

        self.detection = None
        self.recognition = None
        self.layout = None
        self.table_rec = None

        self._initialized = False

        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info("Surya resources released.")