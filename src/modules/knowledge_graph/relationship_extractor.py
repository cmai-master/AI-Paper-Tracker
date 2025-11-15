"""
Relationship Extraction Module
Extracts relationships between entities using LLM
"""
import json
import logging
from typing import List
from datetime import datetime

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from src.core.models import (
    Entity,
    Relationship,
    RelationType,
    EntityType,
    ProcessedDocument
)

logger = logging.getLogger(__name__)


class RelationshipExtractor:
    """Extract relationships between entities"""

    def __init__(self, api_key: str = None):
        """Initialize relationship extractor"""
        if OPENAI_AVAILABLE and api_key:
            self.client = OpenAI(api_key=api_key)
            self.llm_available = True
        else:
            self.client = None
            self.llm_available = False
            logger.warning("OpenAI client not available, relationship extraction will be limited")

    def extract_relationships(
        self,
        paper: ProcessedDocument,
        entities: List[Entity]
    ) -> List[Relationship]:
        """Extract relationships from paper"""
        relationships = []

        # 1. Citation relationships (straightforward)
        citation_rels = self._extract_citation_relationships(paper)
        relationships.extend(citation_rels)

        # 2. Author collaboration relationships
        author_entities = [e for e in entities if e.entity_type == EntityType.AUTHOR]
        if len(author_entities) >= 2:
            author_rels = self._extract_author_relationships(author_entities)
            relationships.extend(author_rels)

        # 3. Paper-Dataset relationships
        dataset_entities = [e for e in entities if e.entity_type == EntityType.DATASET]
        for dataset_entity in dataset_entities:
            relationships.append(Relationship(
                source_entity_id=f"paper_{paper.paper_id}",
                target_entity_id=dataset_entity.id,
                relationship_type=RelationType.EVALUATED_ON,
                weight=1.0,
                confidence=0.9,
                paper_id=paper.paper_id,
                created_at=datetime.utcnow()
            ))

        # 4. Concept relationships (using LLM if available)
        if self.llm_available:
            concept_entities = [e for e in entities if e.entity_type == EntityType.CONCEPT]
            if len(concept_entities) >= 2:
                concept_rels = self._extract_concept_relationships(
                    paper,
                    concept_entities
                )
                relationships.extend(concept_rels)

        return relationships

    def _extract_citation_relationships(
        self,
        paper: ProcessedDocument
    ) -> List[Relationship]:
        """Extract citation relationships"""
        relationships = []

        for reference in paper.references:
            if reference.get("linked_paper_id"):
                relationships.append(Relationship(
                    source_entity_id=f"paper_{paper.paper_id}",
                    target_entity_id=f"paper_{reference['linked_paper_id']}",
                    relationship_type=RelationType.CITES,
                    weight=1.0,
                    confidence=1.0,
                    paper_id=paper.paper_id,
                    created_at=datetime.utcnow()
                ))

        return relationships

    def _extract_author_relationships(
        self,
        authors: List[Entity]
    ) -> List[Relationship]:
        """Extract author collaboration relationships"""
        relationships = []

        # Authors on the same paper collaborate
        for i, author1 in enumerate(authors):
            for author2 in authors[i+1:]:
                relationships.append(Relationship(
                    source_entity_id=author1.id,
                    target_entity_id=author2.id,
                    relationship_type=RelationType.COLLABORATES_WITH,
                    weight=1.0,
                    confidence=1.0,
                    created_at=datetime.utcnow()
                ))

        return relationships

    def _extract_concept_relationships(
        self,
        paper: ProcessedDocument,
        concepts: List[Entity]
    ) -> List[Relationship]:
        """Extract concept relationships using LLM"""
        if not self.llm_available:
            return []

        # Limit to top 10 concepts to avoid token limits
        concept_names = [c.entity_name for c in concepts[:10]]

        prompt = f"""Given a research paper abstract and a list of concepts,
identify relationships between these concepts.

Abstract: {paper.abstract[:500]}

Concepts: {', '.join(concept_names)}

For each pair of related concepts, specify the relationship type:
- IMPROVES: concept A improves concept B
- BUILDS_ON: concept A builds on concept B
- RELATED_TO: concepts are related but no clear dependency

Respond in JSON format:
{{"relationships": [{{"source": "concept1", "target": "concept2", "type": "IMPROVES", "confidence": 0.9}}, ...]}}
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )

            result = json.loads(response.choices[0].message.content)
            relationships = []

            for rel_data in result.get("relationships", []):
                source_concept = next(
                    (c for c in concepts if c.entity_name == rel_data["source"]),
                    None
                )
                target_concept = next(
                    (c for c in concepts if c.entity_name == rel_data["target"]),
                    None
                )

                if source_concept and target_concept:
                    try:
                        rel_type = RelationType(rel_data["type"])
                    except ValueError:
                        rel_type = RelationType.RELATED_TO

                    relationships.append(Relationship(
                        source_entity_id=source_concept.id,
                        target_entity_id=target_concept.id,
                        relationship_type=rel_type,
                        weight=1.0,
                        confidence=rel_data.get("confidence", 0.7),
                        context=paper.abstract[:200],
                        paper_id=paper.paper_id,
                        created_at=datetime.utcnow()
                    ))

            logger.info(f"Extracted {len(relationships)} concept relationships")
            return relationships

        except Exception as e:
            logger.error(f"LLM relationship extraction failed: {e}")
            return []
