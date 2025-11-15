"""
Entity Extraction Module
Extracts entities (concepts, authors, datasets, etc.) from research papers
"""
import re
import logging
from typing import List, Dict
from datetime import datetime

try:
    import spacy
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

from src.core.models import Entity, EntityType, ProcessedDocument, Author

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Entity extractor for research papers"""

    def __init__(self):
        """Initialize entity extractor"""
        # Load scientific NER model if available
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_sci_lg")  # SciBERT-based
                logger.info("Loaded en_core_sci_lg model")
            except OSError:
                try:
                    self.nlp = spacy.load("en_core_web_lg")
                    logger.info("Loaded en_core_web_lg model")
                except OSError:
                    self.nlp = None
                    logger.warning("No spaCy model available")
        else:
            self.nlp = None
            logger.warning("spaCy not installed")

        # ML/AI patterns
        self.ml_patterns = self._load_ml_patterns()

    def extract_entities(self, paper: ProcessedDocument) -> List[Entity]:
        """Extract entities from a paper"""
        entities = []

        # Combine title and abstract for entity extraction
        text = f"{paper.title}\n\n{paper.abstract}"

        # 1. Extract using spaCy NER if available
        if self.nlp:
            spacy_entities = self._extract_with_spacy(text)
            entities.extend(spacy_entities)

        # 2. Pattern-based extraction
        pattern_entities = self._extract_by_patterns(text)
        entities.extend(pattern_entities)

        # 3. Extract datasets
        dataset_entities = self._extract_datasets(text)
        entities.extend(dataset_entities)

        # 4. Extract authors
        author_entities = self._extract_authors(paper)
        entities.extend(author_entities)

        # 5. Extract metrics
        metric_entities = self._extract_metrics(text)
        entities.extend(metric_entities)

        # Deduplicate entities
        entities = self._deduplicate_entities(entities)

        return entities

    def _extract_with_spacy(self, text: str) -> List[Entity]:
        """Extract entities using spaCy NER"""
        entities = []
        doc = self.nlp(text)

        for ent in doc.ents:
            if ent.label_ in ["PRODUCT", "ORG", "GPE", "TECH", "NORP"]:
                entities.append(Entity(
                    id=self._normalize_entity_id(ent.text),
                    entity_type=EntityType.CONCEPT,
                    entity_id=self._normalize_entity_id(ent.text),
                    entity_name=ent.text,
                    properties={"label": ent.label_, "source": "spacy"},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _extract_by_patterns(self, text: str) -> List[Entity]:
        """Extract entities using regex patterns"""
        entities = []

        for pattern_name, pattern_regex in self.ml_patterns.items():
            matches = re.findall(pattern_regex, text, re.IGNORECASE)

            for match in matches:
                entity_text = match if isinstance(match, str) else match[0]
                entities.append(Entity(
                    id=self._normalize_entity_id(entity_text),
                    entity_type=EntityType.CONCEPT,
                    entity_id=self._normalize_entity_id(entity_text),
                    entity_name=entity_text,
                    properties={"pattern": pattern_name, "source": "pattern"},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _load_ml_patterns(self) -> Dict[str, str]:
        """Load ML/AI related regex patterns"""
        return {
            "architecture": r'\b(?:[A-Z][a-z]+)?(?:Net|Former|GAN|VAE|RNN|LSTM|GRU|CNN|Transformer|BERT|GPT)\b',
            "technique": r'\b(?:attention|self-attention|cross-attention|multi-head|pooling)\s+(?:mechanism|layer)?\b',
            "algorithm": r'\b(?:gradient\s+descent|backpropagation|dropout|batch\s+normalization|layer\s+normalization)\b',
            "optimization": r'\b(?:Adam|SGD|RMSprop|AdaGrad|AdamW|LAMB)\s*(?:optimizer)?\b',
            "loss": r'\b(?:cross-entropy|MSE|MAE|contrastive|triplet|focal)\s+loss\b',
            "task": r'\b(?:classification|regression|segmentation|detection|generation|translation)\b',
        }

    def _extract_datasets(self, text: str) -> List[Entity]:
        """Extract well-known datasets"""
        known_datasets = [
            "ImageNet", "COCO", "MNIST", "CIFAR-10", "CIFAR-100",
            "SQuAD", "GLUE", "SuperGLUE", "WikiText", "Penn Treebank",
            "MS-COCO", "Pascal VOC", "ADE20K", "OpenImages",
            "WMT", "Common Crawl", "Wikipedia", "BookCorpus",
            "LibriSpeech", "AudioSet", "Kinetics", "UCF101"
        ]

        entities = []
        for dataset in known_datasets:
            if re.search(rf'\b{re.escape(dataset)}\b', text, re.IGNORECASE):
                entities.append(Entity(
                    id=f"dataset_{self._normalize_entity_id(dataset)}",
                    entity_type=EntityType.DATASET,
                    entity_id=self._normalize_entity_id(dataset),
                    entity_name=dataset,
                    properties={"source": "known_dataset"},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _extract_authors(self, paper: ProcessedDocument) -> List[Entity]:
        """Extract author entities"""
        entities = []

        for author in paper.authors:
            entities.append(Entity(
                id=f"author_{self._normalize_entity_id(author.name)}",
                entity_type=EntityType.AUTHOR,
                entity_id=self._normalize_entity_id(author.name),
                entity_name=author.name,
                properties={
                    "affiliation": author.affiliation,
                    "email": author.email,
                    "source": "paper_metadata"
                },
                first_seen_at=datetime.utcnow(),
                last_updated_at=datetime.utcnow()
            ))

        return entities

    def _extract_metrics(self, text: str) -> List[Entity]:
        """Extract evaluation metrics"""
        known_metrics = [
            "accuracy", "precision", "recall", "F1 score", "F1-score",
            "BLEU", "ROUGE", "METEOR", "perplexity", "AUC", "mAP", "IoU",
            "MRR", "NDCG", "Top-1", "Top-5", "WER", "CER"
        ]

        entities = []
        for metric in known_metrics:
            if re.search(rf'\b{re.escape(metric)}\b', text, re.IGNORECASE):
                entities.append(Entity(
                    id=f"metric_{self._normalize_entity_id(metric)}",
                    entity_type=EntityType.METRIC,
                    entity_id=self._normalize_entity_id(metric),
                    entity_name=metric,
                    properties={"source": "known_metric"},
                    first_seen_at=datetime.utcnow(),
                    last_updated_at=datetime.utcnow()
                ))

        return entities

    def _normalize_entity_id(self, text: str) -> str:
        """Normalize entity text to create ID"""
        normalized = text.lower().strip()
        normalized = re.sub(r'\s+', '_', normalized)
        normalized = re.sub(r'[^\w_-]', '', normalized)
        return normalized

    def _deduplicate_entities(self, entities: List[Entity]) -> List[Entity]:
        """Remove duplicate entities"""
        seen_ids = set()
        unique_entities = []

        for entity in entities:
            if entity.id not in seen_ids:
                seen_ids.add(entity.id)
                unique_entities.append(entity)
            else:
                # Update occurrence count
                existing = next(e for e in unique_entities if e.id == entity.id)
                existing.occurrence_count += 1

        return unique_entities
