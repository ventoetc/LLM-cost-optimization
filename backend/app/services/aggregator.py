"""Result aggregation service"""
from typing import List
from app.models.schemas import SubTaskResult, SubTask


class ResultAggregator:
    """Aggregates results from multiple subtasks into a coherent response"""

    async def aggregate(
        self,
        subtasks: List[SubTask],
        results: List[SubTaskResult],
        original_prompt: str
    ) -> str:
        """
        Aggregate subtask results into a final response

        Args:
            subtasks: Original subtasks
            results: Results from executing subtasks
            original_prompt: The original user prompt

        Returns:
            Aggregated result string
        """
        # Map results to subtasks
        result_map = {r.subtask_id: r for r in results}

        # If single task, just return the result
        if len(subtasks) == 1:
            result = results[0]
            if result.success:
                return result.result
            else:
                return f"Error: {result.error}"

        # Multiple tasks: combine intelligently
        aggregated_parts = []
        aggregated_parts.append(f"# Response to: {original_prompt}\n")

        for subtask in subtasks:
            result = result_map.get(subtask.id)
            if not result:
                continue

            if result.success:
                aggregated_parts.append(f"\n## {subtask.description}")
                aggregated_parts.append(f"{result.result}\n")
                aggregated_parts.append(f"*[Processed by {result.model_used}]*\n")
            else:
                aggregated_parts.append(f"\n## {subtask.description}")
                aggregated_parts.append(f"⚠️ Error: {result.error}\n")

        # Add summary
        successful = sum(1 for r in results if r.success)
        total_cost = sum(r.cost for r in results)

        aggregated_parts.append(f"\n---")
        aggregated_parts.append(f"\n**Processing Summary:**")
        aggregated_parts.append(f"- Completed {successful}/{len(results)} tasks successfully")
        aggregated_parts.append(f"- Total cost: ${total_cost:.4f}")

        return "\n".join(aggregated_parts)
