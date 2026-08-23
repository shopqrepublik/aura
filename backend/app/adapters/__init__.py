"""Registered provider adapters. Provider-specific code belongs here."""

from .json_file import JsonFileAdapter
from .national_gallery_london import NationalGalleryLondonAdapter

ADAPTERS = {
    JsonFileAdapter.adapter_key: JsonFileAdapter,
    NationalGalleryLondonAdapter.adapter_key: NationalGalleryLondonAdapter,
}

__all__ = ["ADAPTERS", "JsonFileAdapter", "NationalGalleryLondonAdapter"]
