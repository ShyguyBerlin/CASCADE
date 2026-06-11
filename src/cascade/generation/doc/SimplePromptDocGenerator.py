import copy
import json
import os
import re
import subprocess
#import tiktoken

from cascade.generation.Generator import Generator
from cascade.generation.executor.OpenAICaller import OpenAICaller
from cascade.utils.JavaUtils import build_context, check_syntax, repair_helper_functions, get_repair_helper_functions, \
    build_signature

class SimplePromptDocGenerator(Generator):
    def __init__(self,
                 model="gpt-4o-mini-2024-07-18",
                 max_attempts=1, delay=3,
                 max_tokens=16000,
                 temperature=0,
                 max_prompt_tokens=8000,
                 freq_penalty=0.0, dummy=False,
                 base_url=None, api_key=None #Base url if used with vllm,  for example: "http://127.0.0.1:8000/v1"
                 ):
        super().__init__()
        self.prompt_executor = OpenAICaller(max_attempts=max_attempts, model=model,
                                            max_tokens=max_tokens, temperature=temperature,
                                            delay=delay, freq_penalty=freq_penalty, dummy=dummy,
                                            api_key=api_key, base_url=base_url)

        self.model = model
        self.max_prompt_tokens = max_prompt_tokens

    def generate(self, context, input_path, output_path, response_step2=None):
        results_path = os.path.join(output_path, "results.txt")
        errors_path = os.path.join(output_path, "errors.txt")

        chat_history = []
        print("      Documentation generation Phase 1")
        # first given the method documentation and signature, we want to extract possible testcases or properties.
        prompt_step1 = [
            {"role": "system",
             "content": "You are an expert Java developer and requirements engineer. "
             "You will be given a method signature and its code. "
             "Your task is to create documentation for the method provided in a comprehensive manner. "
             "Only answer with the Docstring, that must begin with /** and end with */. "
             "Do not point out any differences between the signature and the code, use the code as the source of truth."
             "Focus on the behavior of the method as observable from the code, you might add quirks in the code. "
             "Try to mimic what a human developer would write. They will most likely either create a mental model of the way the function works or just describe types of input and output. You may do both."},
            {"role": "user",
             "content": f"Give a short documentation for the following Java method:\n```java\n{build_signature(context, doc=True)}{context.get("code","")}\n```\n\n"
             "Make sure you consider the behavior exactly as observable in the code and convey information in a way relevant to a developer,"
             "do not make any assumptions that cannot be derived from the code."
             "The user does not need the technical details, except if they are relevant."
             "Write it like a tired developer."}
        ]

        chat_history.append(copy.deepcopy(prompt_step1))
        response_step1a = self.prompt_executor.execute(prompt_step1).model_dump()
        chat_history.append(response_step1a)

        if not response_step1a["choices"]:
            print("      error during generation")
            with open(errors_path, "a") as f:
                f.write(f"error during doc generation of {context["signature"]["name"]}")

            return "", chat_history
        
        message = response_step1a["choices"][0]["message"]["content"]

        message = message[message.find("/**"):message.rfind("*/")+2]

        if len(message) == 0:
            print("      error during generation, docstring format not correct")
            with open(errors_path, "a") as f:
                f.write(f"error during doc generation of {context["signature"]["name"]}, LLM did not return docstring format.")

        return message, chat_history
