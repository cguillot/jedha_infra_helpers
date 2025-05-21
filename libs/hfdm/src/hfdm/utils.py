import os
import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)


class VariableProvider:
    def __init__(
        self,
        name: str,
        kv_dict: Dict[str, str] = None,
        lookup_fn: Callable[[str], str | None] = None,
    ):
        self.__name = name.lower()
        self.__kv_dict = kv_dict
        self.__lookup_fn = lookup_fn

    def get_name(self) -> str:
        return self.__name

    def lookup(self, key: str):
        value = None
        if self.__kv_dict:
            value = self.__kv_dict.get(key)

        if value is None and self.__lookup_fn:
            value = self.__lookup_fn(key)

        return value


class VariableReplacer:
    def __init__(self, providers: list[VariableProvider]):
        self.__lookup_providers = {}

        default_provider = VariableProvider("env", lookup_fn=self.__lookup_default)
        self.__lookup_providers["env"] = default_provider

        for p in providers:
            self.__lookup_providers[p.get_name()] = p

    def lookup(self, provider: str, key: str) -> str | None:
        p_name = provider.lower()
        value_provider = self.__lookup_providers.get(p_name)

        if value_provider:
            return value_provider.lookup(key)  # Use the appropriate lookup method

        logger.error("Unknown value provider: %s for key: %s", p_name, key)
        return f"Unknown provider: {p_name}"

    def __lookup_default(self, key: str) -> str | None:
        return os.environ.get(key, None)  # Return environment variable or None
