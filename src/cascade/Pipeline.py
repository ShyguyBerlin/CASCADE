import os

from cascade.extraction.Extraction import Extraction
from cascade.filters.Filter import Filter
from cascade.analysis.Analysis import Analysis
from cascade.utils.Utils import load_json_from_path
from cascade.diagnostics.PipelineTools import PipelineTools

class Pipeline():
    def __init__(self, extraction: Extraction, _filter: Filter, analysis: Analysis, tools: PipelineTools, setup_config: dict):
        """
        The main pipeline object. Calls "extract" and "analyse" in an appropriate manner.
        is usually build through Pipeline_Factory
        :param extraction: the specific instantiated Extraction object that is used for extraction
        :param analysis: the specific instantiated analysis object
         :param setup: a dictionary that contains the names of the specific instances used
         for extraction, analysis and the objects inside of them,
        """
        self.extraction = extraction
        self._filter = _filter
        self.analysis = analysis
        self.setup_config = setup_config
        self.tools = tools
        self.log=self.tools.log.set_key("Pipeline")

    def execute(self, input_path, output_path) -> None:
        """
        This executes the entire pipline. First extract() from the extraction object is called.
        he output of that is passed to the analysis object. and analyze is executed.

        These specific objects handle what the specific operations do and any things like temporary or
        intermediate saving, which type of analyses should be done and the generator that the analysis uses.
        """
        if not os.path.exists(os.path.join(output_path, "analyzed.json")):
            self.log.log_info("Extraction started")
            data = self.extraction.extract(input_path, output_path)
            self.log.log_info("Extraction finished. Extracted: ", len(data))

            self.log.log_info("Filtering started")
            filtered_data = self._filter.filter_all(data)
            self.log.log_info("Filtering finished. Remaining: ", len(filtered_data))

        else:
            self.log.log_info("Found analyzed results, will skip extraction and filtering")
            # generated artifacts for the same dataset can be saved to avoid repeated generation of code and tests.
            temp_data = load_json_from_path(os.path.join(output_path, "analyzed.json"))
            filtered_data = []
            if temp_data:
                filtered_data = temp_data

        if not filtered_data:
            self.log.log_warn("No data to analyze")
            return

        self.log.log_info("Analysis started")
        self.analysis.analyze(filtered_data, input_path, output_path)
        self.log.log_info("Analysis finished")
        self.tools.time.log_summary()

