"""
MDX MML to NDP MML Converter

This package provides functionality to convert MDX format MML (Music Macro Language)
to NDP format MML.
"""

from .mdx_converter_logic import convert_mml_file

__version__ = "0.1.0"
__all__ = ['convert_mml_file']
