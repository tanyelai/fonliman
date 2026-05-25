"""fonliman — open-source TEFAS dashboard.

The FastAPI app is exposed by `fonliman.main:app` rather than at the package
root so that submodules (e.g. `fonliman.tefas`) can be imported without
triggering app startup. This matters for tests and scripts that exercise the
TEFAS client in isolation.
"""

__version__ = "0.1.1"
