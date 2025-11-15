"""Embedding generation using BGE-M3 and OpenAI."""

from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import AsyncOpenAI
import torch
import structlog

from paperpulse.config.settings import settings

logger = structlog.get_logger()


class EmbeddingGenerator:
    """Base class for embedding generators."""

    async def generate(self, text: str) -> np.ndarray:
        """Generate embedding for text."""
        raise NotImplementedError

    async def generate_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Generate embeddings for multiple texts."""
        raise NotImplementedError


class BGEEmbeddingGenerator(EmbeddingGenerator):
    """Generate embeddings using BGE-M3 model."""

    def __init__(self):
        self.model_name = settings.BGE_MODEL_NAME
        self.device = settings.BGE_DEVICE
        self.max_length = settings.BGE_MAX_LENGTH

        logger.info(
            "loading_bge_model",
            model=self.model_name,
            device=self.device,
        )

        self.model = SentenceTransformer(
            self.model_name,
            device=self.device,
        )

        logger.info("bge_model_loaded", model=self.model_name)

    async def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text.

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.model.get_sentence_embedding_dimension())

        try:
            # Truncate if too long
            if len(text) > self.max_length:
                text = text[: self.max_length]

            # Generate embedding
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

            return embedding

        except Exception as e:
            logger.error(
                "bge_embedding_generation_failed",
                error=str(e),
                text_length=len(text),
            )
            raise

    async def generate_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            # Filter empty texts and truncate long ones
            processed_texts = []
            for text in texts:
                if text and text.strip():
                    if len(text) > self.max_length:
                        text = text[: self.max_length]
                    processed_texts.append(text)
                else:
                    processed_texts.append("")  # Placeholder for empty

            # Generate embeddings in batch
            embeddings = self.model.encode(
                processed_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False,
            )

            logger.info(
                "bge_batch_embedding_completed",
                count=len(texts),
            )

            return list(embeddings)

        except Exception as e:
            logger.error(
                "bge_batch_embedding_failed",
                error=str(e),
                count=len(texts),
            )
            raise

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension."""
        return self.model.get_sentence_embedding_dimension()


class OpenAIEmbeddingGenerator(EmbeddingGenerator):
    """Generate embeddings using OpenAI API."""

    def __init__(self):
        self.model = settings.OPENAI_EMBEDDING_MODEL
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.max_tokens = 8192

        logger.info("openai_embedding_generator_initialized", model=self.model)

    async def generate(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text using OpenAI.

        Args:
            text: Input text

        Returns:
            Embedding vector as numpy array
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return np.zeros(self.get_embedding_dimension())

        try:
            # Truncate if too long (approximate token count)
            if len(text) > self.max_tokens * 4:  # ~4 chars per token
                text = text[: self.max_tokens * 4]

            response = await self.client.embeddings.create(
                model=self.model,
                input=text,
            )

            embedding = np.array(response.data[0].embedding)

            return embedding

        except Exception as e:
            logger.error(
                "openai_embedding_generation_failed",
                error=str(e),
                text_length=len(text),
            )
            raise

    async def generate_batch(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts using OpenAI.

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            # Filter and truncate
            processed_texts = []
            for text in texts:
                if text and text.strip():
                    if len(text) > self.max_tokens * 4:
                        text = text[: self.max_tokens * 4]
                    processed_texts.append(text)
                else:
                    processed_texts.append("")

            # OpenAI supports batch embedding
            response = await self.client.embeddings.create(
                model=self.model,
                input=processed_texts,
            )

            embeddings = [np.array(item.embedding) for item in response.data]

            logger.info(
                "openai_batch_embedding_completed",
                count=len(texts),
            )

            return embeddings

        except Exception as e:
            logger.error(
                "openai_batch_embedding_failed",
                error=str(e),
                count=len(texts),
            )
            raise

    def get_embedding_dimension(self) -> int:
        """Get embedding dimension for the model."""
        # text-embedding-3-small: 1536
        # text-embedding-3-large: 3072
        if "small" in self.model:
            return 1536
        elif "large" in self.model:
            return 3072
        else:
            return 1536  # default


class HybridEmbeddingGenerator:
    """
    Hybrid embedding generator that can switch between models.

    Uses BGE-M3 by default, falls back to OpenAI if needed.
    """

    def __init__(self, prefer_model: str = "bge"):
        self.prefer_model = prefer_model

        # Initialize both generators
        try:
            self.bge_generator = BGEEmbeddingGenerator()
            self.has_bge = True
        except Exception as e:
            logger.warning("bge_initialization_failed", error=str(e))
            self.has_bge = False

        self.openai_generator = OpenAIEmbeddingGenerator()

    async def generate(
        self, text: str, model: Optional[str] = None
    ) -> np.ndarray:
        """
        Generate embedding using preferred or specified model.

        Args:
            text: Input text
            model: Model to use ("bge" or "openai"), defaults to preferred

        Returns:
            Embedding vector
        """
        model = model or self.prefer_model

        try:
            if model == "bge" and self.has_bge:
                return await self.bge_generator.generate(text)
            else:
                return await self.openai_generator.generate(text)

        except Exception as e:
            logger.error(
                "embedding_generation_failed",
                model=model,
                error=str(e),
            )

            # Try fallback
            if model == "bge" and self.has_bge:
                logger.info("falling_back_to_openai")
                return await self.openai_generator.generate(text)
            elif model == "openai" and self.has_bge:
                logger.info("falling_back_to_bge")
                return await self.bge_generator.generate(text)
            else:
                raise

    async def generate_batch(
        self, texts: List[str], model: Optional[str] = None
    ) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            model: Model to use ("bge" or "openai")

        Returns:
            List of embedding vectors
        """
        model = model or self.prefer_model

        try:
            if model == "bge" and self.has_bge:
                return await self.bge_generator.generate_batch(texts)
            else:
                return await self.openai_generator.generate_batch(texts)

        except Exception as e:
            logger.error(
                "batch_embedding_generation_failed",
                model=model,
                error=str(e),
            )

            # Try fallback
            if model == "bge" and self.has_bge:
                logger.info("falling_back_to_openai")
                return await self.openai_generator.generate_batch(texts)
            elif model == "openai" and self.has_bge:
                logger.info("falling_back_to_bge")
                return await self.bge_generator.generate_batch(texts)
            else:
                raise

    def get_embedding_dimension(self, model: Optional[str] = None) -> int:
        """Get embedding dimension for specified model."""
        model = model or self.prefer_model

        if model == "bge" and self.has_bge:
            return self.bge_generator.get_embedding_dimension()
        else:
            return self.openai_generator.get_embedding_dimension()
