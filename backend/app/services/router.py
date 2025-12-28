"""Task router with learning capabilities (shadow mode)"""
import numpy as np
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.schemas import SubTask, ModelTier, TaskType
from app.core.config import settings
from app.db.database import LearningData


class TaskRouter:
    """Routes tasks to optimal models based on learning from user feedback"""

    # Model tiers with example models
    MODEL_TIERS = {
        ModelTier.BASIC: [
            "anthropic/claude-3-haiku",
            "openai/gpt-3.5-turbo",
        ],
        ModelTier.INTERMEDIATE: [
            "openai/gpt-4o",
            "anthropic/claude-3-5-sonnet",
        ],
        ModelTier.ADVANCED: [
            "openai/gpt-4-turbo",
            "anthropic/claude-3-5-sonnet",
        ],
        ModelTier.FRONTIER: [
            "anthropic/claude-opus-4-5",
            "openai/o1",
        ],
    }

    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db_session = db_session
        self.learning_enabled = True

    async def route_task(self, subtask: SubTask) -> str:
        """
        Route a subtask to the optimal model

        Uses learning data if available, otherwise falls back to rule-based routing
        """
        # Try learning-based routing first
        if self.learning_enabled and self.db_session:
            learned_model = await self._learning_based_routing(subtask)
            if learned_model:
                return learned_model

        # Fallback to rule-based routing
        return self._rule_based_routing(subtask)

    async def _learning_based_routing(self, subtask: SubTask) -> Optional[str]:
        """
        Use historical learning data to route tasks
        Shadow mode: learns from user decisions and patterns
        """
        if not self.db_session:
            return None

        # Query learning data for similar tasks
        query = select(LearningData).where(
            LearningData.task_type == subtask.task_type.value,
            LearningData.user_accepted == True,
            LearningData.success == True
        ).order_by(LearningData.timestamp.desc()).limit(10)

        result = await self.db_session.execute(query)
        learning_records = result.scalars().all()

        if not learning_records:
            return None

        # Find records with similar complexity
        similar_records = [
            r for r in learning_records
            if abs(r.complexity - subtask.estimated_complexity) < 0.2
        ]

        if not similar_records:
            similar_records = learning_records

        # Weight by recency and success
        model_scores: Dict[str, float] = {}
        for record in similar_records:
            model = record.model_used
            # Score based on: success, user acceptance, and inverse cost
            score = 1.0
            if record.user_accepted:
                score += 2.0
            if record.cost < 0.01:  # Cheap
                score += 1.0
            if record.latency < 5.0:  # Fast
                score += 0.5

            model_scores[model] = model_scores.get(model, 0) + score

        # Return highest scoring model
        if model_scores:
            best_model = max(model_scores.items(), key=lambda x: x[1])[0]
            return best_model

        return None

    def _rule_based_routing(self, subtask: SubTask) -> str:
        """
        Rule-based routing based on task type and complexity
        Fallback when learning data is insufficient
        """
        complexity = subtask.estimated_complexity
        task_type = subtask.task_type

        # Determine tier based on complexity and task type
        if complexity >= 0.8:
            tier = ModelTier.FRONTIER
        elif complexity >= 0.6:
            # Reasoning and coding need better models
            if task_type in [TaskType.REASONING, TaskType.CODING]:
                tier = ModelTier.ADVANCED
            else:
                tier = ModelTier.INTERMEDIATE
        elif complexity >= 0.3:
            if task_type == TaskType.CODING:
                tier = ModelTier.INTERMEDIATE
            else:
                tier = ModelTier.BASIC
        else:
            tier = ModelTier.BASIC

        # Special cases
        if task_type == TaskType.SIMPLE_QA:
            tier = ModelTier.BASIC
        elif task_type == TaskType.CREATIVE and complexity > 0.5:
            tier = ModelTier.ADVANCED

        # Select model from tier
        models = self.MODEL_TIERS.get(tier, self.MODEL_TIERS[ModelTier.BASIC])

        # For now, just pick the first model in the tier
        # Future: can add load balancing, cost optimization
        subtask.assigned_tier = tier
        return models[0]

    async def record_routing_decision(
        self,
        subtask: SubTask,
        model: str,
        success: bool,
        cost: float,
        latency: float,
        user_accepted: bool = False
    ):
        """
        Record a routing decision for learning (shadow mode)
        Auto-tags patterns for future use
        """
        if not self.db_session:
            return

        # Auto-tag features from the task
        features = {
            "has_code": "code" in subtask.description.lower(),
            "has_data": "data" in subtask.description.lower() or "analyze" in subtask.description.lower(),
            "is_question": "?" in subtask.description,
            "word_count": len(subtask.description.split()),
            "complexity_bucket": self._complexity_bucket(subtask.estimated_complexity)
        }

        learning_record = LearningData(
            task_type=subtask.task_type.value,
            complexity=subtask.estimated_complexity,
            model_used=model,
            success=success,
            user_accepted=user_accepted,
            cost=cost,
            latency=latency,
            features=features
        )

        self.db_session.add(learning_record)
        await self.db_session.commit()

    @staticmethod
    def _complexity_bucket(complexity: float) -> str:
        """Bucket complexity for easier pattern matching"""
        if complexity < 0.3:
            return "simple"
        elif complexity < 0.7:
            return "moderate"
        else:
            return "complex"
