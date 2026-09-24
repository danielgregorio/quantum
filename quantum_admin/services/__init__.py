"""
Declared services of the Quantum Admin (step A2 of the officialization plan).

The .q screens in components/admin call these functions with
`<q:invoke service="admin.<area>.<action>">`. They wrap the library that
already existed in quantum_admin/backend (models, crud, services), so that the
admin has ONE data source — the admin database — instead of two paths: the
FastAPI wrote to the database, and the .q screens to quantum_admin/settings/*.yaml.

Each module registers the services of one area:

    admin.projects.*   projects.py
    admin.import.*     yaml_import.py   (brings the old YAML files into the database)

quantum.config.yaml lists the modules under `services:` (SVC-2).
"""
