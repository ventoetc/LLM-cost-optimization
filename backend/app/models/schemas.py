"""Pydantic models for API requests/responses"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class TaskType(str, Enum):
    """Types of subtasks"""
    RESEARCH = "research"
    CODING = "coding"
    SUMMARIZATION = "summarization"
    REASONING = "reasoning"
    ANALYSIS = "analysis"
    CREATIVE = "creative"
    SIMPLE_QA = "simple_qa"


class ModelTier(str, Enum):
    """Model capability tiers"""
    BASIC = "basic"  # Cheapest models
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    FRONTIER = "frontier"  # Most expensive


class SubTask(BaseModel):
    """Individual subtask from decomposition"""
    id: str
    description: str
    task_type: TaskType
    estimated_complexity: float = Field(ge=0, le=1, description="0=simple, 1=complex")
    context_needed: List[str] = Field(default_factory=list)
    assigned_model: Optional[str] = None
    assigned_tier: Optional[ModelTier] = None


class DecompositionRequest(BaseModel):
    """Request to decompose a prompt"""
    prompt: str
    context: Optional[Dict[str, Any]] = None


class DecompositionResponse(BaseModel):
    """Response from prompt decomposition"""
    original_prompt: str
    subtasks: List[SubTask]
    decomposition_cost: float
    decomposition_time: float


class ExecutionRequest(BaseModel):
    """Request to execute a full orchestrated query"""
    prompt: str
    context: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None


class SubTaskResult(BaseModel):
    """Result from executing a subtask"""
    subtask_id: str
    model_used: str
    result: str
    tokens_input: int
    tokens_output: int
    cost: float
    latency: float
    success: bool
    error: Optional[str] = None


class ExecutionResponse(BaseModel):
    """Response from full orchestrated execution"""
    request_id: str
    original_prompt: str
    aggregated_result: str
    subtask_results: List[SubTaskResult]
    total_cost: float
    total_time: float
    baseline_cost: float
    baseline_model: str
    cost_savings: float
    cost_savings_percent: float
    timestamp: datetime


class FeedbackRequest(BaseModel):
    """User feedback on a request"""
    request_id: str
    user_id: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    accepted: bool
    time_spent: Optional[float] = None
    notes: Optional[str] = None


class MetricsSummary(BaseModel):
    """High-level metrics summary"""
    total_requests: int
    total_cost: float
    total_baseline_cost: float
    total_savings: float
    average_savings_percent: float
    average_response_time: float
    user_satisfaction: Optional[float] = None


class MetricsDetail(BaseModel):
    """Detailed metrics breakdown"""
    summary: MetricsSummary
    requests: List[ExecutionResponse]
    model_usage: Dict[str, int]
    task_type_distribution: Dict[str, int]
    cost_over_time: List[Dict[str, Any]]
