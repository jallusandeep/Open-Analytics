# backend\app\services\data_collection\__init__.py
# Public package for data collection services.
#
# This file imports the split modules and patches each module namespace with all
# public symbols. That keeps the original single-file behavior working when a
# function in one split module calls a helper/function now located in another
# split module.

from importlib import import_module

_MODULE_NAMES = [
    "common",
    "current_instruments",
    "expired_instruments",
    "summary_service",
    "market_holidays_service",
    "company_fundamentals_service",
    "news_ipo_service",
    "instrument_sync_service",
    "ohlcv_service",
    "preview_service",
]

_modules = [
    import_module(f"{__name__}.{module_name}")
    for module_name in _MODULE_NAMES
]

_public_symbols = {}

for _module in _modules:
    for _name, _value in vars(_module).items():
        if not _name.startswith("_"):
            _public_symbols[_name] = _value

for _module in _modules:
    _module.__dict__.update(_public_symbols)

globals().update(_public_symbols)

__all__ = sorted(_public_symbols.keys())
