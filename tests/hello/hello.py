"""A tiny stand-in app: the reusable workflows build and smoke-test it in CI, so they are proved without a real app."""

import sys

if "--version" in sys.argv:
    print("hello 0.0.0")
elif "--selftest" in sys.argv:
    print("selftest: ok")
else:
    print("hello")
