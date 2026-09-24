"""Moved to quantum_admin.core.settings_service (A4.2: the wheel ships the admin's library,
not this FastAPI backend). The backend imports it by its old name."""
import sys

from quantum_admin.core import settings_service as _module

sys.modules[__name__] = _module
