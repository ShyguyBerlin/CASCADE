from __future__ import annotations

from cascade.diagnostics.logging.Logging import Logging, log_level_key


class KeyLogging(Logging):
    """
    A logging wrapper that adds a key/channel to every log message.
    Delegates to another Logging instance after prefixing messages with the key.
    
    Similar to the C pattern with #define LOG_CHANNEL, this allows subsystems
    to declare their identity once and have all messages tagged consistently.
    """
    
    def __init__(self, wrapped_logger: Logging, key: str = ""):
        """
        Initialize KeyLogging with a wrapped logger and optional initial key.
        
        :param wrapped_logger: The underlying Logging instance to delegate to
        :param key: The channel/key to prefix to messages (e.g., "firewall", "parser")
        """
        super().__init__("", wrapped_logger.output_path, wrapped_logger.log_level)
        self.wrapped_logger = wrapped_logger
        self.key = key
    
    def _log(self, log_level: log_level_key = log_level_key.LOG_LEVEL_INFO, *args, **kwargs):
        delegated_kwargs = dict(kwargs)
        delegated_kwargs["key"] = self.key
        self.wrapped_logger._log(log_level, *args, **delegated_kwargs)
    
    def set_key(self, key: str) -> "Logging":
        self.key = key
        return self
