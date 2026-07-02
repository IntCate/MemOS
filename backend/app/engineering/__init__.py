"""工程化模块 - 包含Harness、Inference、Prompt、Context、Tool等工程"""
from .data_structures import (
    Message, Decision, Response, InferenceResult, PipelineResult,
    ChannelType, PromptMode, PromptType
)
from .harness.engine import HarnessEngine
from .inference.engine import InferenceEngine
from .prompt.engine import PromptEngine
from .context.engine import ContextEngine
from .context.data_structures import Context, ContextSource



harness_engine = None
inference_engine = None
prompt_engine = PromptEngine()
context_engine = ContextEngine()


def initialize_engines(config: dict = None):
    global harness_engine, inference_engine, prompt_engine, context_engine
    config = config or {}
    harness_engine = HarnessEngine(config.get('harness', {}))
    inference_engine = InferenceEngine(config.get('inference', {}))
    prompt_engine = PromptEngine(config.get('prompt', {}))
    context_engine = ContextEngine(config.get('context', {}))


__all__ = [
    'Message',
    'Decision',
    'Response',
    'InferenceResult',
    'PipelineResult',
    'ChannelType',
    'PromptMode',
    'PromptType',
    'HarnessEngine',
    'InferenceEngine',
    'PromptEngine',
    'ContextEngine',
    'Context',
    'ContextSource',
    'harness_engine',
    'inference_engine',
    'prompt_engine',
    'context_engine',
    'initialize_engines'
]