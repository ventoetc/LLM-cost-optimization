"""Main orchestration service that coordinates all components"""
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
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
from app.db.database import Request, SubTaskExecution, UserFeedback
from app.core.config import settings


class Orchestrator:
    """Main orchestration service for the LLM cost optimization system"""

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.decomposer = PromptDecomposer()
        self.router = TaskRouter(db_session)
        self.executor = MultiProviderExecutor()
        self.aggregator = ResultAggregator()

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

        # Step 4: Aggregate results
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
            timestamp=start_time
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
