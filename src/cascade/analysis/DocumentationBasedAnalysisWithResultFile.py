import json
import os

from cascade.analysis.DocumentationBasedAnalysis import DocumentationBasedAnalysis


class DocumentationBasedAnalysisWithResultFile(DocumentationBasedAnalysis):
    def analyze(self, data: list, input_path, output_path):
        log_path = os.path.join(output_path, "log.txt")

        def log(header, message):
            with open(log_path, "a") as f:
                f.write(header + "\n")
                f.write(message + "\n")

        with open(log_path, "w") as f:
            f.write("Documentation-based analysis started\n")

        try:
            super().analyze(data, input_path, output_path)
        finally:
            try:
                result_string = self._build_result_string(data, output_path)
                with open(os.path.join(output_path, "result.txt"), "w") as f:
                    f.write(result_string)
                log("Final result:", result_string)
            except Exception as exc:
                log("ERROR:", str(exc))
                print(f"Could not write result.txt: {exc}")

    def _build_result_string(self, data, output_path):
        analyzed_path = os.path.join(output_path, "analyzed.json")
        items = None

        if os.path.exists(analyzed_path):
            try:
                with open(analyzed_path, "r") as f:
                    loaded = json.load(f)

                if isinstance(loaded, list):
                    items = loaded
                elif isinstance(loaded, dict):
                    items = [loaded]
            except Exception:
                items = None

        if items is None:
            items = data or []

        verdicts = []
        for item in items:
            if isinstance(item, dict):
                verdict = item.get("verdict")
                if verdict:
                    verdicts.append(verdict)

        if verdicts:
            return verdicts[-1]

        return "NoInco; error ; no verdict"