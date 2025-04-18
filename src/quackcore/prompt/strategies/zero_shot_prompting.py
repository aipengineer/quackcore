# src/quackcore/prompt/strategies/zero_shot_prompting.py
"""
Zero-shot Prompting strategy for the PromptBooster.

This strategy uses a task description without examples to perform zero-shot prompting.
"""

from quackcore.prompt.registry import register_prompt_strategy
from quackcore.prompt.strategy_base import PromptStrategy


def render(task_description: str) -> str:
    return f"""
{task_description}
""".strip()

strategy = PromptStrategy(
    id="zero-shot-prompting",
    label="Zero-shot Prompting",
    description="Uses a task description without examples to perform zero-shot prompting.",
    input_vars=["task_description"],
    render_fn=render,
    tags=["zero-shot", "general-prompting"],
    origin="Prompt Engineering (Lee Boonstra, February 2025)",
)
register_prompt_strategy(strategy)
