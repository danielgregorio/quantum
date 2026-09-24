"""Moved to quantum_admin.core.environment_service (A4.2: the wheel ships the admin's library,
not this FastAPI backend). The backend imports it by its old name."""
import sys

from quantum_admin.core import environment_service as _module

sys.modules[__name__] = _module
