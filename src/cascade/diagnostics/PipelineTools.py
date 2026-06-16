from cascade.diagnostics.logging.Logging import Logging
from cascade.diagnostics.model_executor.LLMCaller import LLMCaller
from cascade.diagnostics.time.TimeMeasuring import TimeMeasuring

class PipelineTools:
    def __init__(self):
        pass

    def set_log(self, log:Logging):
        self.log=log

    def set_llm(self, llm:LLMCaller):
        self.llm=llm

    def set_time(self, time:TimeMeasuring):
        self.time=time