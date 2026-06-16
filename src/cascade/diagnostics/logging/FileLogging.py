from __future__ import annotations

from datetime import datetime
from typing import Iterable

from cascade.diagnostics.logging.Logging import Logging, log_level_key


class FileLogging(Logging):
    """Writes log entries to a file and supports keyed channels via KeyLogging."""

    _ANSI_BY_LEVEL = {
        log_level_key.LOG_LEVEL_INFO: "97",   # white
        log_level_key.LOG_LEVEL_DEBUG: "94",  # light blue
        log_level_key.LOG_LEVEL_WARN: "93",   # yellow/orange
        log_level_key.LOG_LEVEL_ERROR: "91",  # red
    }

    def __init__(self, 
            output_path:str="",
            log_file_path:str = "log.txt", 
            print_level: log_level_key = log_level_key.LOG_LEVEL_INFO,
            log_level: log_level_key = log_level_key.LOG_LEVEL_DEBUG,
            activate_colors:bool=True):
        super().__init__(output_path, log_file_path, log_level)
        self.print_level=print_level
        self.key_length=len("GENERAL")
        self.activate_colors=activate_colors

    def _log(self, log_level: log_level_key = log_level_key.LOG_LEVEL_INFO, *args, **kwargs):

        key = str(kwargs.get("key", "GENERAL"))
        message = self._build_message(args)
        timestamp = datetime.now().strftime("%d.%m.%Y %H:%M:%S")

        heading = f"[{key} {" "*(self.key_length-len(key))}]"
        colored_heading = self._colorize_heading(heading, log_level)
        line = f"{timestamp} {colored_heading} : {message}"

        if log_level.value >= self.print_level.value:
            print(line)

        if log_level.value >= self.log_level.value:
            with open(self.output_path, "a", encoding="utf-8") as log_file:
                log_file.write(line + "\n")

    def set_key(self, key: str) -> Logging:
        from cascade.diagnostics.logging.KeyLogging import KeyLogging
        self.key_length=max(self.key_length,len(key))
        return KeyLogging(self, key)

    def _build_message(self, args: Iterable[object]) -> str:
        if not args:
            return ""
        return " ".join(str(arg) for arg in args)

    def _colorize_heading(self, heading: str, log_level: log_level_key) -> str:
        color_code = self._ANSI_BY_LEVEL.get(log_level, "97")
        return f"\033[{color_code}m{heading}\033[0m"