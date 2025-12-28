"""Multi-provider execution service"""
import httpx
import asyncio
import time
from typing import List, Dict, Any

from app.core.config import settings
from app.models.schemas import SubTask, SubTaskResult


class MultiProviderExecutor:
    """Executes tasks across multiple LLM providers via OpenRouter"""

    def __init__(self):
        self.api_key = settings.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"

    async def execute_tasks(
        self,
        subtasks: List[SubTask],
        original_prompt: str,
        context: Dict[str, Any] = None
    ) -> List[SubTaskResult]:
        """
        Execute multiple subtasks in parallel across different models

        Args:
            subtasks: List of subtasks with assigned models
            original_prompt: The original user prompt for context
            context: Additional context

        Returns:
            List of SubTaskResult
        """
        # Execute all subtasks in parallel
        tasks = [
            self._execute_single_task(subtask, original_prompt, context)
            for subtask in subtasks
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to failed results
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(SubTaskResult(
                    subtask_id=subtasks[i].id,
                    model_used=subtasks[i].assigned_model or "unknown",
                    result="",
                    tokens_input=0,
                    tokens_output=0,
                    cost=0.0,
                    latency=0.0,
                    success=False,
                    error=str(result)
                ))
            else:
                final_results.append(result)

        return final_results

    async def _execute_single_task(
        self,
        subtask: SubTask,
        original_prompt: str,
        context: Dict[str, Any] = None
    ) -> SubTaskResult:
        """Execute a single subtask"""
        start_time = time.time()

        model = subtask.assigned_model
        if not model:
            raise ValueError(f"No model assigned to subtask {subtask.id}")

        # Build the prompt for this subtask
        task_prompt = self._build_task_prompt(subtask, original_prompt, context)

        try:
            # Call OpenRouter
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "user", "content": task_prompt}
                        ],
                        "temperature": 0.7,
                    },
                    timeout=60.0
                )
                response.raise_for_status()
                result_data = response.json()

            # Extract result and usage
            result_text = result_data["choices"][0]["message"]["content"]
            usage = result_data.get("usage", {})
            tokens_input = usage.get("prompt_tokens", 0)
            tokens_output = usage.get("completion_tokens", 0)

            # Calculate cost
            cost = self._calculate_cost(model, tokens_input, tokens_output)

            latency = time.time() - start_time

            return SubTaskResult(
                subtask_id=subtask.id,
                model_used=model,
                result=result_text,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost=cost,
                latency=latency,
                success=True
            )

        except Exception as e:
            latency = time.time() - start_time
            return SubTaskResult(
                subtask_id=subtask.id,
                model_used=model,
                result="",
                tokens_input=0,
                tokens_output=0,
                cost=0.0,
                latency=latency,
                success=False,
                error=str(e)
            )

    def _build_task_prompt(
        self,
        subtask: SubTask,
        original_prompt: str,
        context: Dict[str, Any] = None
    ) -> str:
        """Build the prompt for a specific subtask"""
        prompt_parts = [
            f"Original request: {original_prompt}\n",
            f"Your specific task: {subtask.description}\n",
        ]

        if subtask.context_needed:
            prompt_parts.append(f"You may need context from: {', '.join(subtask.context_needed)}\n")

        if context:
            prompt_parts.append(f"Additional context: {context}\n")

        prompt_parts.append("\nProvide a focused response for your specific task.")

        return "\n".join(prompt_parts)

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in cents"""
        model_cost = settings.MODEL_COSTS.get(model, {"input": 100, "output": 300})
        cost = (input_tokens * model_cost["input"] + output_tokens * model_cost["output"]) / 1_000_000
        return cost

    async def calculate_baseline_cost(self, prompt: str) -> float:
        """
        Calculate what this would cost using the baseline model
        Uses estimation since we don't actually call it
        """
        # Estimate tokens (rough: 1 token ≈ 4 characters)
        estimated_input_tokens = len(prompt) // 4
        # Assume output is ~2x input for baseline estimation
        estimated_output_tokens = estimated_input_tokens * 2

        baseline_model = settings.BASELINE_MODEL
        return self._calculate_cost(baseline_model, estimated_input_tokens, estimated_output_tokens)
