from abc import ABC, abstractmethod
from cascade.diagnostics.logging.Logging import Logging

class TimeMeasuring(ABC):
    """
    The abstract base class for all time measuring classes.
    """
    @abstractmethod
    def start(self, phase=""):
        pass

    @abstractmethod
    def start_phase(self,phase=""):
        pass

    @abstractmethod
    def stop(self, phase=""):
        pass

    @abstractmethod
    def log_summary(self):
        pass