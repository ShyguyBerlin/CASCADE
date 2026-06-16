from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
import os

class log_level_key(Enum):
    LOG_LEVEL_DEBUG = 0
    LOG_LEVEL_INFO = 1
    LOG_LEVEL_WARN = 2
    LOG_LEVEL_ERROR = 3

class Logging(ABC):
    """
    The abstract base class for all logging classes.
    """
    def __init__(self, output_path:str,log_file_path:str, log_level:log_level_key):
        self.output_path = os.path.join(output_path,log_file_path)
        self.log_level = log_level

    @abstractmethod
    def _log(self, log_level:log_level_key = log_level_key.LOG_LEVEL_INFO, *args, **kwargs):
        pass
    
    def log_debug(self, *args, **kwargs):
        self._log(log_level_key.LOG_LEVEL_DEBUG, *args, **kwargs)

    def log_info (self, *args, **kwargs):
        self._log(log_level_key.LOG_LEVEL_INFO, *args, **kwargs)

    def log_warn (self, *args, **kwargs):
        self._log(log_level_key.LOG_LEVEL_WARN, *args, **kwargs)

    def log_error(self, *args, **kwargs):
        self._log(log_level_key.LOG_LEVEL_ERROR, *args, **kwargs)

    @abstractmethod
    def set_key(self, key:str) -> "Logging":
        pass