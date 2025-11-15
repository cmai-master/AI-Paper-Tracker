"""
BGE-M3 Embedder - Generate dense and sparse embeddings
"""

import logging
import time
from typing import List, Dict, Optional, Tuple
from datetime import datetime

from FlagEmbedding import BGEM3FlagModel

from app.services.embedding.schemas import (
    EmbeddingResult,
    BatchEmbeddingResponse,
)

logger = logging.getLogger(__name__)


class BGEM3Embedder:
    """
    BGE-M3 Embedding Generator

    Supports:
    - Dense vectors (1024-dim)
    - Sparse vectors (lexical matching)
    - Multi-lingual
    - Long context (8192 tokens)
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        use_fp16: bool = True,
        device: str = "cuda",
        batch_size: int = 12,
        max_length: int = 8192,
    ):
        """
        Initialize BGE-M3 embedder

        Args:
            model_name: HuggingFace model name
            use_fp16: Use FP16 for faster inference
            device: Device to use (cuda/cpu)
            batch_size: Batch size for processing
            max_length: Maximum sequence length
        """
        self.model_name = model_name
        self.use_fp16 = use_fp16
        self.device = device
        self.batch_size = batch_size
        self.max_length = max_length
        self.model: Optional[BGEM3FlagModel] = None

        logger.info(f"🔧 Initializing BGE-M3 Embedder: {model_name}")

    def load_model(self):
        """Load the BGE-M3 model"""
        if self.model is not None:
            logger.info("✅ Model already loaded")
            return

        logger.info(f"📥 Loading BGE-M3 model: {self.model_name}")
        start_time = time.time()

        try:
            self.model = BGEM3FlagModel(
                self.model_name,
                use_fp16=self.use_fp16,
                device=self.device,
            )

            load_time = int((time.time() - start_time) * 1000)
            logger.info(f"✅ Model loaded successfully in {load_time}ms")

        except Exception as e:
            logger.error(f"❌ Failed to load model: {e}", exc_info=True)
            raise

    def embed_single(
        self, text: str, return_dense: bool = True, return_sparse: bool = True
    ) -> EmbeddingResult:
        """
        Generate embedding for a single text

        Args:
            text: Input text
            return_dense: Return dense vector
            return_sparse: Return sparse vector

        Returns:
            EmbeddingResult
        """
        if self.model is None:
            self.load_model()

        start_time = time.time()

        # Generate embeddings
        result = self.model.encode(
            [text],
            batch_size=1,
            max_length=self.max_length,
            return_dense=return_dense,
            return_sparse=return_sparse,
            return_colbert_vecs=False,  # We don't need ColBERT vectors for now
        )

        generation_time = int((time.time() - start_time) * 1000)

        # Extract results
        dense_vector = None
        sparse_vector = None

        if return_dense and "dense_vecs" in result:
            dense_vector = result["dense_vecs"][0].tolist()

        if return_sparse and "lexical_weights" in result:
            # Convert sparse dict to our format
            sparse_dict = result["lexical_weights"][0]
            sparse_vector = {
                "indices": list(sparse_dict.keys()),
                "values": list(sparse_dict.values()),
            }

        return EmbeddingResult(
            dense_vector=dense_vector,
            sparse_vector=sparse_vector,
            model_name=self.model_name,
            embedding_version="1.0",
            generation_time_ms=generation_time,
        )

    def embed_batch(
        self,
        texts: List[str],
        return_dense: bool = True,
        return_sparse: bool = True,
        show_progress: bool = True,
    ) -> BatchEmbeddingResponse:
        """
        Generate embeddings for a batch of texts

        Args:
            texts: List of input texts
            return_dense: Return dense vectors
            return_sparse: Return sparse vectors
            show_progress: Show progress bar

        Returns:
            BatchEmbeddingResponse
        """
        if self.model is None:
            self.load_model()

        if not texts:
            return BatchEmbeddingResponse(
                dense_vectors=[],
                sparse_vectors=[],
                total_processed=0,
                total_time_ms=0,
                model_name=self.model_name,
            )

        logger.info(f"🔄 Embedding {len(texts)} texts in batches of {self.batch_size}")
        start_time = time.time()

        try:
            # Generate embeddings
            result = self.model.encode(
                texts,
                batch_size=self.batch_size,
                max_length=self.max_length,
                return_dense=return_dense,
                return_sparse=return_sparse,
                return_colbert_vecs=False,
                show_progress_bar=show_progress,
            )

            total_time = int((time.time() - start_time) * 1000)

            # Extract dense vectors
            dense_vectors = []
            if return_dense and "dense_vecs" in result:
                dense_vectors = [vec.tolist() for vec in result["dense_vecs"]]

            # Extract sparse vectors
            sparse_vectors = []
            if return_sparse and "lexical_weights" in result:
                for sparse_dict in result["lexical_weights"]:
                    sparse_vectors.append(
                        {
                            "indices": list(sparse_dict.keys()),
                            "values": list(sparse_dict.values()),
                        }
                    )

            logger.info(
                f"✅ Embedded {len(texts)} texts in {total_time}ms "
                f"({total_time / len(texts):.1f}ms per text)"
            )

            return BatchEmbeddingResponse(
                dense_vectors=dense_vectors,
                sparse_vectors=sparse_vectors if sparse_vectors else None,
                total_processed=len(texts),
                total_time_ms=total_time,
                model_name=self.model_name,
            )

        except Exception as e:
            logger.error(f"❌ Batch embedding failed: {e}", exc_info=True)
            raise

    def embed_query(self, query: str) -> EmbeddingResult:
        """
        Generate embedding for a search query

        BGE-M3 doesn't require special query prefixes

        Args:
            query: Search query

        Returns:
            EmbeddingResult
        """
        return self.embed_single(query, return_dense=True, return_sparse=True)

    def embed_document(self, document: str) -> EmbeddingResult:
        """
        Generate embedding for a document

        Args:
            document: Document text

        Returns:
            EmbeddingResult
        """
        return self.embed_single(document, return_dense=True, return_sparse=True)

    def compute_similarity(
        self, query_embedding: List[float], document_embeddings: List[List[float]]
    ) -> List[float]:
        """
        Compute cosine similarity between query and documents

        Args:
            query_embedding: Query dense vector
            document_embeddings: List of document dense vectors

        Returns:
            List of similarity scores
        """
        import numpy as np

        query_vec = np.array(query_embedding)
        doc_vecs = np.array(document_embeddings)

        # Cosine similarity
        query_norm = np.linalg.norm(query_vec)
        doc_norms = np.linalg.norm(doc_vecs, axis=1)

        similarities = np.dot(doc_vecs, query_vec) / (doc_norms * query_norm)

        return similarities.tolist()

    def get_model_info(self) -> Dict[str, any]:
        """
        Get model information

        Returns:
            Model metadata
        """
        return {
            "model_name": self.model_name,
            "device": self.device,
            "use_fp16": self.use_fp16,
            "batch_size": self.batch_size,
            "max_length": self.max_length,
            "dense_dim": 1024,
            "loaded": self.model is not None,
        }

    def unload_model(self):
        """Unload model from memory"""
        if self.model is not None:
            logger.info("🗑️ Unloading BGE-M3 model")
            del self.model
            self.model = None

            # Clear CUDA cache if using GPU
            if "cuda" in self.device:
                try:
                    import torch

                    torch.cuda.empty_cache()
                    logger.info("🧹 Cleared CUDA cache")
                except ImportError:
                    pass


# Global embedder instance (lazy loading)
_embedder: Optional[BGEM3Embedder] = None


def get_embedder(
    model_name: str = "BAAI/bge-m3",
    use_fp16: bool = True,
    device: str = "cuda",
) -> BGEM3Embedder:
    """
    Get or create global embedder instance

    Args:
        model_name: Model name
        use_fp16: Use FP16
        device: Device to use

    Returns:
        BGEM3Embedder instance
    """
    global _embedder

    if _embedder is None:
        _embedder = BGEM3Embedder(
            model_name=model_name, use_fp16=use_fp16, device=device
        )

    return _embedder


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Initialize embedder
    embedder = BGEM3Embedder(device="cpu")  # Use CPU for testing
    embedder.load_model()

    # Test single embedding
    text = "Attention is all you need for transformer models"
    result = embedder.embed_single(text)

    print(f"\n{'='*60}")
    print(f"Single Embedding Test")
    print(f"{'='*60}")
    print(f"Text: {text}")
    print(f"Dense vector dim: {len(result.dense_vector) if result.dense_vector else 0}")
    print(
        f"Sparse vector size: {len(result.sparse_vector['indices']) if result.sparse_vector else 0}"
    )
    print(f"Generation time: {result.generation_time_ms}ms")

    # Test batch embedding
    texts = [
        "Deep learning has revolutionized computer vision",
        "Natural language processing uses transformer architectures",
        "Reinforcement learning trains agents through rewards",
    ]

    batch_result = embedder.embed_batch(texts, show_progress=False)

    print(f"\n{'='*60}")
    print(f"Batch Embedding Test")
    print(f"{'='*60}")
    print(f"Texts: {len(texts)}")
    print(f"Dense vectors: {len(batch_result.dense_vectors)}")
    print(
        f"Sparse vectors: {len(batch_result.sparse_vectors) if batch_result.sparse_vectors else 0}"
    )
    print(f"Total time: {batch_result.total_time_ms}ms")
    print(f"Time per text: {batch_result.total_time_ms / len(texts):.1f}ms")

    # Test similarity
    query = "What are transformers in NLP?"
    query_result = embedder.embed_query(query)

    similarities = embedder.compute_similarity(
        query_result.dense_vector, batch_result.dense_vectors
    )

    print(f"\n{'='*60}")
    print(f"Similarity Search Test")
    print(f"{'='*60}")
    print(f"Query: {query}")
    for i, (text, score) in enumerate(zip(texts, similarities)):
        print(f"{i+1}. [{score:.4f}] {text}")

    print(f"\n{'='*60}")
    print(f"Model Info")
    print(f"{'='*60}")
    for key, value in embedder.get_model_info().items():
        print(f"{key}: {value}")
