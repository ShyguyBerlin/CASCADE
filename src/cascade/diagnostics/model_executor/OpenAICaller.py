import os
import time
from openai import OpenAI
from cascade.generation.executor.LLMCaller import LLMCaller
from cascade.diagnostics.PipelineTools import PipelineTools
import traceback

class OpenAICaller(LLMCaller):
    def __init__(
        self,
        pipeline:PipelineTools=None,
        max_attempts=1,
        max_tokens=16000,
        temperature=0,
        delay=5,
        dummy=False,
        model="gpt",
        freq_penalty=0.0,
        base_url=None,          # ← optional
        api_key=None,           # ← optional
        timeout=60.0,
    ):
        self.pipeline=pipeline
        self.log=pipeline.log.set_key("LLM-Call")
        self.max_attempts = max_attempts
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.delay = delay
        self.freq_penalty = freq_penalty
        self.model = model

        if dummy:
            self.client = None
            return

        client_kwargs = {
            "timeout": timeout,
        }

        if base_url is not None:
            # we expect this to be a vLLM OpenAI-compatible server
            client_kwargs["base_url"] = base_url
            client_kwargs["api_key"] = os.environ.get("VLLM_API_KEY", api_key or "dummy")
        else:
            # Normal OpenAI
            client_kwargs["api_key"] = os.environ.get("OPENAI_API_KEY", api_key)

        self.log.log_debug(f"My model is {self.model} and my url is {client_kwargs["base_url"]}")
        self.client = OpenAI(**client_kwargs)

    def execute(self, prompt, **kwargs):
        self.pipeline.time.start("LLM call")
        attempt = 0
        self.log.log_debug(f"I am being called by {traceback.format_stack()}")
        while attempt < self.max_attempts:
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=prompt,
                    max_completion_tokens=self.max_tokens,   #temporary fix for gpt5
                    #temperature=self.temperature,
                    frequency_penalty=self.freq_penalty,
                    **kwargs,
                )
                self.pipeline.time.stop("LLM call")
                return response

            except Exception as e:
                self.log.log_info(f"Generation attempt {attempt + 1} failed: {e}")
                attempt += 1
                time.sleep(self.delay)

        self.pipeline.time.stop("LLM call")
        raise Exception("Generation failed. because of repeated errors.")


