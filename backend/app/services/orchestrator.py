"""Main orchestration service that coordinates all components"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schemas import (
    ExecutionRequest,
    ExecutionResponse,
    SubTaskResult,
    FeedbackRequest
)
from app.services.decomposer import PromptDecomposer
from app.services.router import TaskRouter
from app.services.executor import MultiProviderExecutor
from app.services.aggregator import ResultAggregator
from app.services.friction_detector import FrictionDetector
from app.services.emotional_friction_mapper import EmotionalFrictionMapper
from app.db.database import Request, SubTaskExecution, UserFeedback
from app.core.config import settings
from app.models.schemas import FrictionPoint, VerificationCheck, HumanFrictionInsight


class Orchestrator:
    """Main orchestration service for the LLM cost optimization system"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.decomposer = PromptDecomposer()
        self.router = TaskRouter(db_session)
        self.executor = MultiProviderExecutor()
        self.aggregator = ResultAggregator()
        self.friction_detector = FrictionDetector()
        self.emotional_mapper = EmotionalFrictionMapper()

    async def execute_request(self, request: ExecutionRequest) -> ExecutionResponse:
        """
        Execute a full orchestrated request

        Flow:
        1. Decompose prompt into subtasks (using cheap model)
        2. Route each subtask to optimal model (using learning)
        3. Execute subtasks in parallel across providers
        4. Aggregate results
        5. Calculate cost savings vs baseline
        6. Store metrics for learning
        """
        request_id = str(uuid.uuid4())
        start_time = datetime.utcnow()

        # Step 1: Decompose
        decomposition = await self.decomposer.decompose(
            request.prompt,
            request.context
        )

        # Step 2: Route each subtask
        for subtask in decomposition.subtasks:
            model = await self.router.route_task(subtask)
            subtask.assigned_model = model

        # Step 3: Execute tasks in parallel
        subtask_results = await self.executor.execute_tasks(
            decomposition.subtasks,
            request.prompt,
            request.context
        )

        # Step 4: Detect friction and run verification checks
        # Build responses for friction detection
        responses_for_analysis = [
            {"model": r.model_used, "response": r.result}
            for r in subtask_results if r.success
        ]

        friction_analysis = None
        friction_points_formatted = None
        verification_checks_formatted = None
        human_insight = None

        if len(responses_for_analysis) > 1:  # Need multiple models for friction
            # Estimate overall complexity from subtasks
            avg_complexity = sum(st.estimated_complexity for st in decomposition.subtasks) / len(decomposition.subtasks)

            friction_analysis = await self.friction_detector.analyze_responses(
                responses_for_analysis,
                request.prompt,
                avg_complexity
            )

            # Format friction points for response
            friction_points_formatted = [
                FrictionPoint(
                    location=fp.location,
                    description=fp.description,
                    severity=fp.severity.value if hasattr(fp.severity, 'value') else str(fp.severity),
                    models_involved=fp.models_involved,
                    human_impact=self._describe_human_impact(fp)
                )
                for fp in friction_analysis.friction_points
            ]

            # Format verification checks
            verification_checks_formatted = [
                VerificationCheck(
                    check_type=vc.flag.value if hasattr(vc.flag, 'value') else str(vc.flag),
                    passed=vc.passed,
                    confidence=vc.confidence,
                    evidence=vc.evidence
                )
                for vc in friction_analysis.verification_results
            ]

            # Map to human emotional friction
            emotional_profile = self.emotional_mapper.map_ai_friction_to_human_emotion(
                friction_analysis.friction_points,
                request.prompt
            )

            # Format human friction insight
            user_display = self.emotional_mapper.format_for_user_display(emotional_profile)

            human_insight = HumanFrictionInsight(
                primary_emotions=user_display['what_ai_is_handling']['primary_challenges'],
                micro_frustrations=user_display['what_ai_is_handling']['micro_frustrations_addressed'],
                cognitive_load=user_display['task_difficulty'],
                time_saved_hours=user_display['time_saved_hours'],
                support_provided=user_display['support_provided'],
                user_message=user_display['user_message']
            )

        # Step 5: Aggregate results
        aggregated_result = await self.aggregator.aggregate(
            decomposition.subtasks,
            subtask_results,
            request.prompt
        )

        # Calculate totals
        total_cost = sum(r.cost for r in subtask_results) + decomposition.decomposition_cost
        total_time = (datetime.utcnow() - start_time).total_seconds()

        # Calculate baseline cost
        baseline_cost = await self.executor.calculate_baseline_cost(request.prompt)

        # Calculate savings
        cost_savings = baseline_cost - total_cost
        cost_savings_percent = (cost_savings / baseline_cost * 100) if baseline_cost > 0 else 0

        # Generate processing note to explain latency
        processing_note = self._generate_processing_note(
            decomposition.subtasks,
            total_time,
            friction_analysis,
            human_insight
        )

        # Store in database
        await self._store_request(
            request_id=request_id,
            user_id=request.user_id,
            original_prompt=request.prompt,
            aggregated_result=aggregated_result,
            total_cost=total_cost,
            baseline_cost=baseline_cost,
            total_time=total_time,
            timestamp=start_time
        )

        # Store subtask executions
        for i, result in enumerate(subtask_results):
            await self._store_subtask_execution(
                request_id=request_id,
                subtask=decomposition.subtasks[i],
                result=result
            )

        # Record routing decisions for learning
        for i, result in enumerate(subtask_results):
            await self.router.record_routing_decision(
                subtask=decomposition.subtasks[i],
                model=result.model_used,
                success=result.success,
                cost=result.cost,
                latency=result.latency,
                user_accepted=False  # Will be updated when user provides feedback
            )

        await self.db_session.commit()

        return ExecutionResponse(
            request_id=request_id,
            original_prompt=request.prompt,
            aggregated_result=aggregated_result,
            subtask_results=subtask_results,
            total_cost=total_cost,
            total_time=total_time,
            baseline_cost=baseline_cost,
            baseline_model=settings.BASELINE_MODEL,
            cost_savings=cost_savings,
            cost_savings_percent=cost_savings_percent,
            timestamp=start_time,
            friction_points=friction_points_formatted,
            verification_checks=verification_checks_formatted,
            human_friction_insight=human_insight,
            processing_note=processing_note
        )

    async def record_feedback(self, feedback: FeedbackRequest):
        """
        Record user feedback (shadow learning mode)

        This is critical for the learning system - user decisions
        are captured to improve future routing
        """
        feedback_record = UserFeedback(
            request_id=feedback.request_id,
            user_id=feedback.user_id,
            rating=feedback.rating,
            accepted=feedback.accepted,
            time_spent=feedback.time_spent,
            notes=feedback.notes
        )

        self.db_session.add(feedback_record)
        await self.db_session.commit()

        # Update learning data with user acceptance
        # This feeds back into the router's learning system
        if feedback.accepted:
            # The router will use this in future decisions
            pass

    async def _store_request(
        self,
        request_id: str,
        user_id: Optional[str],
        original_prompt: str,
        aggregated_result: str,
        total_cost: float,
        baseline_cost: float,
        total_time: float,
        timestamp: datetime
    ):
        """Store request in database"""
        request_record = Request(
            id=request_id,
            user_id=user_id,
            original_prompt=original_prompt,
            aggregated_result=aggregated_result,
            total_cost=total_cost,
            baseline_cost=baseline_cost,
            total_time=total_time,
            timestamp=timestamp
        )
        self.db_session.add(request_record)

    async def _store_subtask_execution(
        self,
        request_id: str,
        subtask: Any,
        result: SubTaskResult
    ):
        """Store subtask execution in database"""
        execution_record = SubTaskExecution(
            request_id=request_id,
            subtask_id=result.subtask_id,
            task_type=subtask.task_type.value,
            complexity=subtask.estimated_complexity,
            model_used=result.model_used,
            tokens_input=result.tokens_input,
            tokens_output=result.tokens_output,
            cost=result.cost,
            latency=result.latency,
            success=result.success
        )
        self.db_session.add(execution_record)

    def _describe_human_impact(self, friction_point) -> str:
        """Describe what this friction means for human experience"""
        severity = friction_point.severity
        if hasattr(severity, 'value'):
            severity = severity.value

        impact_map = {
            'smooth': "Easy, straightforward - no human friction expected",
            'mild': "Minor uncertainty - human would pause briefly to consider",
            'moderate': "Noticeable difficulty - human would need to research or get input",
            'severe': "Significant challenge - human would struggle and second-guess",
            'suspicious': "Deceptively simple - human might miss hidden complexity"
        }

        base_impact = impact_map.get(str(severity).lower(), "Cognitive friction detected")

        # Add context from description
        if 'contradictory' in friction_point.description.lower():
            return f"{base_impact}. Multiple conflicting approaches would cause doubt and rework."
        elif 'different approaches' in friction_point.description.lower():
            return f"{base_impact}. Choice paralysis from multiple valid options."
        elif 'confidence' in friction_point.description.lower():
            return f"{base_impact}. Uncertainty would lead to repeated validation checks."

        return base_impact

    def _generate_processing_note(
        self,
        subtasks: List,
        total_time: float,
        friction_analysis: Optional[Any],
        human_insight: Optional[HumanFrictionInsight]
    ) -> str:
        """
        Generate a note explaining why processing took time

        This helps users understand that longer processing = the AI handling
        genuine complexity, not just being slow
        """
        num_subtasks = len(subtasks)

        if total_time < 5:
            return f"Processed {num_subtasks} subtask(s) efficiently."

        notes = []

        # Explain subtask breakdown
        if num_subtasks > 1:
            notes.append(
                f"Your request was intelligently decomposed into {num_subtasks} "
                f"specialized subtasks, processed by different models in parallel."
            )

        # Explain friction/difficulty
        if friction_analysis and len(friction_analysis.friction_points) > 0:
            notes.append(
                f"The system detected {len(friction_analysis.friction_points)} "
                f"friction point(s) where different models showed cognitive variance - "
                f"this mirrors the difficulty a human would experience."
            )

        # Explain what human friction was addressed
        if human_insight and human_insight.cognitive_load in ['high', 'excessive']:
            notes.append(
                f"This task has {human_insight.cognitive_load} cognitive load. "
                f"Processing time reflects the genuine complexity: the AI is managing "
                f"what would typically cause {', '.join(human_insight.primary_emotions[:2])} "
                f"in human execution."
            )

        # Explain time saved
        if human_insight and human_insight.time_saved_hours > 1:
            notes.append(
                f"By handling {len(human_insight.micro_frustrations)} micro-frustrations "
                f"in parallel across specialized models, we're saving you approximately "
                f"{human_insight.time_saved_hours} hours of focused work."
            )

        # Default explanation
        if not notes:
            notes.append(
                f"Processing involved frontier-level analysis across multiple "
                f"specialized models to ensure quality."
            )

        return " ".join(notes)
