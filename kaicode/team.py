"""Multi-Model Team Mode operations."""

import asyncio
from typing import Dict

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich import box

from kaicode.config import KaiConfig
from kaicode.providers import get_provider
from kaicode.providers.base import Message
from kaicode.ui.display import console, print_info, print_error, print_success


async def _call_provider(p_name: str, m_name: str, prompt: str, config: KaiConfig) -> tuple[str, str]:
    try:
        provider = get_provider(p_name, config)
        content = ""
        stream = provider.stream_chat(
            messages=[Message(role="user", content=prompt)],
            model=m_name,
            system="You are a collaborative AI agent. Provide a clear and concise response to the user's prompt.",
            tools=None
        )
        async for chunk in stream:
            if chunk.content:
                content += chunk.content
        return f"{p_name}/{m_name}", content.strip()
    except Exception as e:
        return f"{p_name}/{m_name}", f"Error: {e}"


async def run_panel(prompt: str, config: KaiConfig, panel_names: list[str]) -> Dict[str, str]:
    """Execute a prompt against multiple models simultaneously."""
    if not panel_names:
        print_error("No panel models configured. Check your config.yaml.")
        return {}

    print_info(f"Dispatching to {len(panel_names)} models in parallel...")
    tasks = []
    
    for spec in panel_names:
        if ":" in spec:
            p_name, m_name = spec.split(":", 1)
        else:
            p_name = spec
            m_name = config.get_provider(p_name).default_model or "default"
        tasks.append(_call_provider(p_name, m_name, prompt, config))

    results = await asyncio.gather(*tasks)
    result_dict = dict(results)

    console.print()
    for model_id, response in result_dict.items():
        console.print(
            Panel(
                Text(response),
                title=f"[bold kaicode.assistant] {model_id} [/]",
                border_style="kaicode.separator",
                box=box.ROUNDED,
                padding=(0, 1)
            )
        )
    return result_dict


async def run_consensus(prompt: str, config: KaiConfig, primary_provider: str, primary_model: str, panel_names: list[str]) -> str | None:
    """Run panel, then synthesize into one consensus answer."""
    responses = await run_panel(prompt, config, panel_names)
    if not responses:
        return None

    print_info("Synthesizing consensus...")
    
    synth_prompt = f"Original user request:\n{prompt}\n\n"
    synth_prompt += "Here are the responses from a panel of AI models:\n\n"
    for model_id, response in responses.items():
        synth_prompt += f"--- {model_id} ---\n{response}\n\n"
        
    synth_prompt += "Synthesize these responses into a single, cohesive, optimal answer that addresses the original request. Take the best ideas from each response and combine them."

    _, consensus = await _call_provider(primary_provider, primary_model, synth_prompt, config)
    
    console.print()
    console.print(
        Panel(
            Text(consensus),
            title=f"[bold kaicode.success] Consensus by {primary_provider}/{primary_model} [/]",
            border_style="kaicode.success",
            box=box.HEAVY,
            padding=(0, 1)
        )
    )
    return consensus


async def run_vote(prompt: str, config: KaiConfig, primary_provider: str, primary_model: str, panel_names: list[str]) -> str | None:
    """Run panel, then judge the best answer."""
    responses = await run_panel(prompt, config, panel_names)
    if not responses:
        return None

    print_info("Judging the best response...")
    
    judge_prompt = f"Original user request:\n{prompt}\n\n"
    judge_prompt += "Here are the candidate responses from a panel of AI models:\n\n"
    for idx, (model_id, response) in enumerate(responses.items(), 1):
        judge_prompt += f"--- Candidate {idx} ({model_id}) ---\n{response}\n\n"
        
    judge_prompt += "Act as a judge. Evaluate the candidates based on correctness, clarity, and usefulness. Then declare the winner and explain your reasoning, finally reproducing the winning answer."

    _, judgement = await _call_provider(primary_provider, primary_model, judge_prompt, config)
    
    console.print()
    console.print(
        Panel(
            Text(judgement),
            title=f"[bold kaicode.warning] Judgement by {primary_provider}/{primary_model} [/]",
            border_style="kaicode.warning",
            box=box.HEAVY,
            padding=(0, 1)
        )
    )
    return judgement
