"""
Run the old Quantum Admin API server (FastAPI). `quantum admin` is the admin
that ships; this backend stays in the repository only (A4.2).

    python quantum_admin/backend/run.py
"""
import pathlib
import sys

import uvicorn

if __name__ == "__main__":
    admin = pathlib.Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(admin))
    uvicorn.run(
        "backend.main:app",
        app_dir=str(admin),
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )
