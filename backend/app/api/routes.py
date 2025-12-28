"""API routes"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List
from datetime import datetime, timedelta

from app.db.database import get_session, Request, SubTaskExecution, UserFeedback
from app.models.schemas import (
    ExecutionRequest,
    ExecutionResponse,
    FeedbackRequest,
    MetricsSummary,
    MetricsDetail,
    DecompositionRequest,
    DecompositionResponse
)
from app.services.orchestrator import Orchestrator
from app.services.decomposer import PromptDecomposer

router = APIRouter()


@router.post("/execute", response_model=ExecutionResponse)
async def execute_request(
    request: ExecutionRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Execute a full orchestrated LLM request

    This is the main endpoint - it decomposes the prompt, routes subtasks
    to optimal models, executes in parallel, and returns aggregated results
    with cost comparison.
    """
    orchestrator = Orchestrator(db)
    return await orchestrator.execute_request(request)


@router.post("/decompose", response_model=DecompositionResponse)
async def decompose_prompt(request: DecompositionRequest):
    """
    Decompose a prompt into subtasks (preview mode)

    Useful for seeing how a prompt would be broken down without executing
    """
    decomposer = PromptDecomposer()
    return await decomposer.decompose(request.prompt, request.context)


@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackRequest,
    db: AsyncSession = Depends(get_session)
):
    """
    Submit user feedback on a request

    This is critical for the shadow learning mode - captures user
    decisions to improve future routing
    """
    orchestrator = Orchestrator(db)
    await orchestrator.record_feedback(feedback)
    return {"status": "success", "message": "Feedback recorded"}


@router.get("/metrics/summary", response_model=MetricsSummary)
async def get_metrics_summary(
    days: int = 7,
    db: AsyncSession = Depends(get_session)
):
    """
    Get high-level metrics summary

    Collapsed view showing total costs, savings, and performance
    """
    # Calculate date range
    since = datetime.utcnow() - timedelta(days=days)

    # Query requests
    query = select(Request).where(Request.timestamp >= since)
    result = await db.execute(query)
    requests = result.scalars().all()

    if not requests:
        return MetricsSummary(
            total_requests=0,
            total_cost=0.0,
            total_baseline_cost=0.0,
            total_savings=0.0,
            average_savings_percent=0.0,
            average_response_time=0.0,
            user_satisfaction=None
        )

    # Calculate metrics
    total_requests = len(requests)
    total_cost = sum(r.total_cost for r in requests)
    total_baseline_cost = sum(r.baseline_cost for r in requests)
    total_savings = total_baseline_cost - total_cost
    average_savings_percent = (total_savings / total_baseline_cost * 100) if total_baseline_cost > 0 else 0
    average_response_time = sum(r.total_time for r in requests) / total_requests

    # User satisfaction from feedback
    feedback_query = select(func.avg(UserFeedback.rating)).where(
        UserFeedback.timestamp >= since,
        UserFeedback.rating.isnot(None)
    )
    satisfaction_result = await db.execute(feedback_query)
    user_satisfaction = satisfaction_result.scalar()

    return MetricsSummary(
        total_requests=total_requests,
        total_cost=total_cost,
        total_baseline_cost=total_baseline_cost,
        total_savings=total_savings,
        average_savings_percent=average_savings_percent,
        average_response_time=average_response_time,
        user_satisfaction=user_satisfaction
    )


@router.get("/metrics/detail", response_model=MetricsDetail)
async def get_metrics_detail(
    days: int = 7,
    limit: int = 50,
    db: AsyncSession = Depends(get_session)
):
    """
    Get detailed metrics

    Expanded view with request breakdown, model usage, task distribution
    """
    since = datetime.utcnow() - timedelta(days=days)

    # Get summary
    summary = await get_metrics_summary(days, db)

    # Get recent requests
    query = select(Request).where(
        Request.timestamp >= since
    ).order_by(Request.timestamp.desc()).limit(limit)
    result = await db.execute(query)
    requests = result.scalars().all()

    # Get subtask executions
    exec_query = select(SubTaskExecution).where(
        SubTaskExecution.timestamp >= since
    )
    exec_result = await db.execute(exec_query)
    executions = exec_result.scalars().all()

    # Calculate model usage
    model_usage = {}
    for exec in executions:
        model_usage[exec.model_used] = model_usage.get(exec.model_used, 0) + 1

    # Calculate task type distribution
    task_distribution = {}
    for exec in executions:
        task_distribution[exec.task_type] = task_distribution.get(exec.task_type, 0) + 1

    # Cost over time (daily buckets)
    cost_over_time = []
    for i in range(days):
        day = datetime.utcnow() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        day_requests = [r for r in requests if day_start <= r.timestamp < day_end]
        day_cost = sum(r.total_cost for r in day_requests)
        day_baseline = sum(r.baseline_cost for r in day_requests)

        cost_over_time.append({
            "date": day_start.isoformat(),
            "cost": day_cost,
            "baseline_cost": day_baseline,
            "savings": day_baseline - day_cost
        })

    # Convert requests to ExecutionResponse format (simplified)
    # In a real implementation, you'd reconstruct the full response
    request_summaries = []

    return MetricsDetail(
        summary=summary,
        requests=request_summaries,  # Simplified for now
        model_usage=model_usage,
        task_type_distribution=task_distribution,
        cost_over_time=cost_over_time
    )


@router.get("/requests/{request_id}")
async def get_request(
    request_id: str,
    db: AsyncSession = Depends(get_session)
):
    """Get details of a specific request"""
    query = select(Request).where(Request.id == request_id)
    result = await db.execute(query)
    request = result.scalar_one_or_none()

    if not request:
        raise HTTPException(status_code=404, detail="Request not found")

    # Get subtask executions
    exec_query = select(SubTaskExecution).where(
        SubTaskExecution.request_id == request_id
    )
    exec_result = await db.execute(exec_query)
    executions = exec_result.scalars().all()

    return {
        "request": request,
        "executions": executions
    }
