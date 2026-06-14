"""Infrastructure adapter package for concrete data and external resources."""

from .workbook_assumptions import DATA_PACKAGE, load_workbook_model_spec_record

__all__ = [
    "DATA_PACKAGE",
    "load_workbook_model_spec_record",
]
