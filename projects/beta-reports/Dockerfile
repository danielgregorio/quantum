# The beta's reports, on the homelab (README.md):
#
#   docker compose -f projects/beta-reports/compose.yaml up -d --build
#
# From the repository's root. The database lives in the volume (data/); gunicorn serves it with one process,
# so an endpoint's limit= counts every call (its counts are the process's, API-5).
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY quantum ./quantum
RUN pip install --no-cache-dir -e . gunicorn
COPY projects/beta-reports ./projects/beta-reports

WORKDIR /app/projects/beta-reports
EXPOSE 8095
CMD ["sh", "-c", "quantum migrate up && exec gunicorn 'quantum.runtime.web_server:create_app()' --bind 0.0.0.0:8095 --workers 1 --threads 8"]
