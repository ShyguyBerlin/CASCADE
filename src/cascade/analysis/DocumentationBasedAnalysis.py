import copy
import json
import os
import tempfile
from datetime import datetime
from xml.parsers.expat import model
from tqdm import tqdm

from cascade.analysis.Analysis import Analysis
from cascade.analysis.executor.Execution import Execution
from cascade.analysis.executor.ExecutionResults import ExecutionResults

from cascade.generation.executor.OpenAICaller import OpenAICaller
from cascade.generation.Generation import Generation
from cascade.utils.Utils import save_dicts_list_to_json, load_json_from_path
from cascade.utils.JavaUtils import build_signature

from cascade.utils.DockerizedWrapper import DockerizedWrapper
import xml.etree.ElementTree as ET

class DocumentationBasedAnalysis(Analysis):
    def __init__(self,
                 generator: Generation,
                 executor: Execution,
                 regenerate=False,
                 reexecute=False,
                 just_analyze=False,
                 image="maven" ,
                 debug=0,
                 step_size=1,
                 max_repair_tries=3,
                 model:dict = {}
                 ):
        super().__init__(generator, executor)
        self.reexecute = reexecute or regenerate
        self.step_size = step_size
        self.regenerate = regenerate
        self.just_analyze = just_analyze
        self.debug = debug
        self.image = image
        self.output_path = ""
        self.max_repair_tries = max_repair_tries
        self.model=model

        if self.model != {}:
            self.prompt_executor = OpenAICaller(max_attempts=self.model.get("max_attempts",1), model=self.model.get("model","gpt-4o-mini-2024-07-18"),
                                                max_tokens=self.model.get("max_tokens",16000), temperature=self.model.get("temperature",0),
                                                delay=self.model.get("delay",3), freq_penalty=self.model.get("freq_penalty",0), dummy=self.model.get("dummy",False),
                                                api_key=self.model.get("api_key",None), base_url=self.model.get("base_url",None))


    def analyze(self, data: list, input_path, output_path):
        """
        This is the main analysis. It can will run on the extracted data of a whole java project and will save

        :param data: a list with the methods from the program under test. Contains a context dictionary for each method under test.
        :param input_path: a path where
        :param output_path: a path where the output should be written to.
        """
        def log(header, message):
            with open(os.path.join(output_path, "log.txt"), "a") as f:
                f.write(header + "\n")
                f.write(message+ "\n")

        def has_results(dct, results_key: str) -> bool:
            return "results" in dct and results_key in dct["results"] and dct["results"][results_key] not in (None, [], [[], [], []])
        errors_path = os.path.join(output_path, "errors.txt")

        print(f"analyzing {len(data)} elements")

        if os.path.exists(os.path.join(output_path, "analyzed.json")):
            data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
            print(f"loaded existing analyzed data with {len(data)} elements")
        else:
            # preparing/ finding out junit version etc.
            data = self.prepare_data(data, input_path, output_path)
            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))


        if not self.just_analyze:
                # set up the executor


            time_start = datetime.now()
            for idx, d in enumerate(data):
                try:
                    time_now = datetime.now()
                    time_elapsed = time_now - time_start
                    time_avg = time_elapsed / (idx + 1)
                    time_remaining = time_avg * (len(data) - (idx + 1))

                    print(
                        f"{time_now.strftime('%H:%M:%S')}  "
                        f"Analyzing method: {d['signature']['name']}. "
                        f"{idx+1}/{len(data)}  "
                        f"Time so far: {str(time_elapsed).split('.')[0]} "
                        f"Estimated time remaining: {str(time_remaining).split('.')[0]}"
                    )


                    print("    Step 1 - Generate Documentation")

                    if not "new_docs" in d or self.regenerate:
                        print("      generate new docs")
                        new_docs, chat_history = self.generator.generate_doc(d, input_path, output_path)

                        d["new_docs"] = new_docs
                        d["new_docs_history"] = chat_history

                        if new_docs == "":
                            log("GENERATION: no docs could be generated.\n ChatHistory:\n", str(chat_history))
                            d["verdict"] = f"NoInco; error ; no docs generated"
                            continue

                        original_docs = d.get("doc", "")

                        if self.prompt_executor:
                            prompt_comparison = [
                                {"role": "system",
                                "content": "You are an expert Java developer and requirements engineer. "
                                "You will be given two Docstrings for a Java method and your task is to compare them and find out if they are consistent with each other. "
                                "Regard the users requests when deciding what consistent means. "
                                "If one Docstring is substantially shorter than the other, but the information it contains is not in conflict with the longer one, you should consider them consistent."
                                "Ignore parameter descriptions."
                                "If they are, answer with 'consistent'. If they are not, answer with 'inconsistent'. "
                                "You must add an explanation of your decision behind the verdict."
                                "When you add an explanation, put a ';' after the verdict"},
                                {"role": "user",
                                "content": f"I have the following two Docstrings for a Java method:\n```java\n{original_docs}\n```\n\nAnd:\n```java\n{new_docs}\n```\n\n"
                                    "Are they describing the same functionality/ result and side effects? They may describe the same functionality with different levels of detail, that still counts as the same."
                                    "If one of the docstrings is missing e.g. the parameter descriptions, you should not consider them on both; this also holds for implementation details."}
                            ]

                            response_comparison = self.prompt_executor.execute(prompt_comparison).model_dump()
                            if not response_comparison["choices"]:
                                print("      error during generation")
                                with open(errors_path, "a") as f:
                                    f.write(f"error during doc comparison of {d['signature']['name']}")
                                d["verdict"] = f"NoInco; error ; doc comparison failed" 
                                continue
                            message_comparison = response_comparison["choices"][0]["message"]["content"]

                            chat_history.append(prompt_comparison)
                            chat_history.append(message_comparison)
                            d["new_docs_history"] = chat_history

                            if ";" in message_comparison:
                                comparison_verdict = message_comparison.split(";")[0].strip().lower()
                                comparison_reasoning = message_comparison.split(";")[1].strip()
                            else:
                                #Sometimes the model does not add a ; for splitting
                                comparison_verdict = message_comparison.strip().lower()
                                verdict_pos = comparison_verdict.find("consistent")
                                if verdict_pos != -1:
                                    comparison_reasoning = comparison_verdict[verdict_pos + len("consistent"):]
                                else:
                                    comparison_reasoning = ""
                            
                            if len(comparison_reasoning) == 0:
                                print("      model generated no reasoning")
                            else:
                                pass
                                #print(f"      model reasoning (len {len(comparison_reasoning)}): " , comparison_reasoning)

                            if "inconsistent" in comparison_verdict:
                                print("      inconsistent????")
                                d["verdict"] = f"INCO; inconsistent ; {comparison_reasoning}"
                            elif "consistent" in comparison_verdict:
                                print("      consistent")
                                d["verdict"] = f"NoInco; consistent ; {comparison_reasoning}"
                        else:
                            print("      no comparison done, since no prompt executor available")
                            d["verdict"] = f"NoInco; error ; no comparison done"
                            continue
                    else:
                        print("      new docs already generated")
                except Exception as e:
                    d["verdict"] = f"NoInco; error ; exception occurred"

                # save every few steps
                if idx % 10 == 0:
                    with open(os.path.join(output_path, "analyzed.json"), "w") as f:
                        f.write(json.dumps(data))
                    save_dicts_list_to_json(
                        [
                            {
                                "id": item.get("id"),
                                "file_name": os.path.basename(item.get("code_file_path", "")),
                                "file_path": item.get("code_file_path"),
                                "class_name": item.get("parent", {}).get("name"),
                                "function_name": item.get("signature", {}).get("name"),
                                "full_function_signature": build_signature(item, doc=False),
                                "verdict": item.get("verdict"),
                                "new_doc": item.get("new_docs"),
                            }
                            for item in data if item.get("verdict", "").startswith("INCO")
                        ],
                        os.path.join(output_path, "inconsistent_functions.json")
                    )



            # end:  for d in data

            time_end = datetime.now()
            time_total = str(datetime.now() - time_start).split('.')[0]
            print(f"Finished analysis in {time_total}")

            #save final results
            save_dicts_list_to_json(data, os.path.join(output_path, "analyzed.json"))
            save_dicts_list_to_json(
                [
                    {
                        "id": item.get("id"),
                        "file_name": os.path.basename(item.get("code_file_path", "")),
                        "file_path": item.get("code_file_path"),
                        "class_name": item.get("parent", {}).get("name"),
                        "function_name": item.get("signature", {}).get("name"),
                        "full_function_signature": build_signature(item, doc=False),
                        "verdict": item.get("verdict"),
                        "failed_testcases": list((item.get("results", {}).get("(new_code, new_tests)") or item.get("results", {}).get("(code, new_tests)") or [[], [], []])[1]),
                        "errored_testcases": list((item.get("results", {}).get("(new_code, new_tests)") or item.get("results", {}).get("(code, new_tests)") or [[], [], []])[2]),
                        "failing_testcases": list((item.get("results", {}).get("(new_code, new_tests)") or item.get("results", {}).get("(code, new_tests)") or [[], [], []])[1]) + list((item.get("results", {}).get("(new_code, new_tests)") or item.get("results", {}).get("(code, new_tests)") or [[], [], []])[2]),
                    }
                    for item in data if item.get("verdict", "").startswith("INCO")
                ],
                os.path.join(output_path, "inconsistent_functions.json")
            )

        # end: if not just analyze

        # From now on, just print stats from the analysis, no more comarison or generation

        general_stats = {
            "complete_errors": 0,  #
            "LLM_comparison_passed": 0,  #
            "LLM_comparison_error": 0,   #
            "LLM_comparison_failed": 0,  #
            "incos" : 0,        #
            "likely_incos": 0,  #
        }
        incos = []
        likely_incos = []

        # helper function to take the verdict apart
        def parse_verdict(verdict: str):
            parts = verdict.split(";")
            result = {
                "inco_status": parts[0].strip() if len(parts) > 0 else None,
                "test_result": parts[1].strip() if len(parts) > 1 else None,
                "step_info": parts[2].strip() if len(parts) > 2 else None,
                "step1_results": parts[3].strip() if len(parts) > 3 else None,
                "metrics": parts[5].strip() if len(parts) > 5 else None,
            }
            return result

        for d in data:
            if "verdict" in d:
                if not ";" in d["verdict"]:
                    general_stats["complete_errors"] += 1
                    continue
                r = parse_verdict(d["verdict"])
            else :
                print(d["signature"]["name"] , "\t", "No verdict")
                continue
            print(d["signature"]["name"] , "\t", d["verdict"])

            if r["inco_status"] == "INCO":
                    general_stats["incos"] += 1
                    incos.append(d)
            
            if r["test_result"] == "error":
                general_stats["LLM_comparison_error"] += 1
            elif r["test_result"] == "consistent":
                general_stats["LLM_comparison_passed"] += 1
            elif r["test_result"] == "inconsistent":    
                general_stats["LLM_comparison_failed"] += 1

        for key, value in general_stats.items():
            print(f"{key}: {value}")

        print("Incos:")
        for d in incos:
            print("--------------------------------------------------------")
            print(d["signature"]["name"])
            print("docs:           " , d["doc"])
            print("generated docs: " , d["new_docs"])

    def prepare_data(self, data: list, input_path, output_path):
        # Currently just the code and docs is sufficient
        return data

    def evaluate(self, res):
        if res[0] == [] and res[1] == [] and res[2] == []:
            print("        Error")
            # error
            return 0
        elif res[1] == [] and res[2] == []:
            print("        Passed")
            # if no errors or failures  then passed
            return 1
        else:
            print("        Failed")
            return -1

