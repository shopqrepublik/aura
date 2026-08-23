"""Registered provider adapters. Provider-specific code belongs here."""

from .json_file import JsonFileAdapter

ADAPTERS = {JsonFileAdapter.adapter_key: JsonFileAdapter}

__all__ = ["ADAPTERS", "JsonFileAdapter"]
