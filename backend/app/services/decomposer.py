"""Prompt decomposition service using a cheap model"""
import httpx
import json
import uuid
import time
from typing import List, Dict, Any

from app.core.config import settings
from app.models.schemas import SubTask, TaskType, DecompositionResponse


class PromptDecomposer:
    """Decomposes complex prompts into subtasks using a cheap model"""

    def __init__(self):
        self.model = settings.DECOMPOSER_MODEL
        self.api_key = settings.OPENROUTER_API_KEY

    async def decompose(self, prompt: str, context: Dict[str, Any] = None) -> DecompositionResponse:
        """
        Decompose a prompt into subtasks

        Args:
            prompt: The user's original prompt
            context: Optional context information

        Returns:
            DecompositionResponse with subtasks
        """
        start_time = time.time()

        # System prompt for decomposition
        system_prompt = """You are a prompt decomposition specialist. Your job is to analyze complex prompts and break them down into discrete, parallelizable subtasks.

For each subtask, identify:
1. A clear description of what needs to be done
2. The type of task (research, coding, summarization, reasoning, analysis, creative, simple_qa)
3. Estimated complexity (0.0 = trivial, 1.0 = extremely complex)
4. What context from other tasks it might need

Return your response as a JSON array of tasks with this structure:
[
  {
    "description": "Clear description of the subtask",
    "task_type": "research|coding|summarization|reasoning|analysis|creative|simple_qa",
    "estimated_complexity": 0.0-1.0,
    "context_needed": ["list of other task ids or descriptions it depends on"]
  }
]

If the prompt is simple and doesn't need decomposition, return a single task.
"""

        user_prompt = f"Decompose this prompt into subtasks:\n\n{prompt}"

        if context:
            user_prompt += f"\n\nAdditional context: {json.dumps(context)}"

        # Call the decomposer model via OpenRouter
        try:
            subtasks_data = await self._call_openrouter(system_prompt, user_prompt)
            subtasks = self._parse_subtasks(subtasks_data)
        except Exception as e:
            # Fallback: treat as single task
            subtasks = [SubTask(
                id=str(uuid.uuid4()),
                description=prompt,
                task_type=TaskType.REASONING,
                estimated_complexity=0.7
            )]

        elapsed_time = time.time() - start_time

        # Calculate cost (rough estimate)
        # Assume ~500 tokens input, ~300 tokens output for decomposition
        cost = self._calculate_cost(500, 300)

        return DecompositionResponse(
            original_prompt=prompt,
            subtasks=subtasks,
            decomposition_cost=cost,
            decomposition_time=elapsed_time
        )

    async def _call_openrouter(self, system: str, user: str) -> str:
        """Call OpenRouter API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user}
                    ],
                    "temperature": 0.3,
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    def _parse_subtasks(self, response: str) -> List[SubTask]:
        """Parse subtasks from model response"""
        try:
            # Extract JSON from response
            response = response.strip()
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            tasks_data = json.loads(response)

            subtasks = []
            for task_data in tasks_data:
                subtask = SubTask(
                    id=str(uuid.uuid4()),
                    description=task_data.get("description", ""),
                    task_type=TaskType(task_data.get("task_type", "reasoning")),
                    estimated_complexity=float(task_data.get("estimated_complexity", 0.5)),
                    context_needed=task_data.get("context_needed", [])
                )
                subtasks.append(subtask)

            return subtasks
        except Exception as e:
            # Fallback to single task
            return []

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in cents"""
        model_cost = settings.MODEL_COSTS.get(self.model, {"input": 25, "output": 125})
        cost = (input_tokens * model_cost["input"] + output_tokens * model_cost["output"]) / 1_000_000
        return cost
