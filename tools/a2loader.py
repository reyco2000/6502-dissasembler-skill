#!/usr/bin/env python3
"""a2loader.py — compatibility shim: the loader now lives in loader.py and
handles every supported 6502 machine. Importing or running this module is
the same as using loader.py."""

try:
    from tools import loader as _loader
except ImportError:
    import loader as _loader

globals().update({k: v for k, v in vars(_loader).items() if not k.startswith("__")})

if __name__ == "__main__":
    _loader.main()
