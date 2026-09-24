# Quantum Admin Inventory

> **Generated** by `python scripts/admin-inventory.py` — do not edit by hand. Measured, not declared: routes read from the AST of `quantum_admin/backend/main.py`, shadowing asked of the real router, status of each authenticated GET against a temporary database, `.q` screens served from a temporary copy. Write routes are not executed.

**234 FastAPI routes** in 28 areas · 59 HTML pages · 5 shadowed (never reached) · GETs without parameters measured: 79/83 respond without error · **20 service modules** · **17 `.q` screens**, 2 without `require_auth`, 0 `q:python` blocks.

The admin interface (HTML and JS generated inside `main.py`) makes **128 calls** with a readable URL (4 use a variable and are not counted). **13 reach no route at all**. **115 API routes are not called by the interface** — candidates to go if they also serve nothing outside it (A2).

## Areas

| Area | Routes | Pages | Write | Called by the UI | Services used | GETs measured ok |
|---|---:|---:|---:|---:|---|---|
| Admin UI | 27 | 27 | 0 | 25 | crud | 25/25 |
| Resources | 25 | 1 | 11 | 8 | auth_service, resource_manager | 11/11 |
| Jobs | 24 | 6 | 9 | 12 | auth_service, job_service | 10/10 |
| Docker | 19 | 0 | 10 | 9 | crud, db_setup_service, docker_service, secret_manager | 2/6 |
| Connectors | 13 | 0 | 8 | 6 | connector_service | 2/2 |
| Health | 11 | 2 | 4 | 1 | auth_service, crud, health_service | 4/4 |
| Dashboard | 9 | 7 | 0 | 4 | audit_service, auth_service, crud, job_service, settings_service, webhook_service | 8/8 |
| Test Generator | 9 | 0 | 7 | 5 | auth_service, component_discovery, crud, test_generator | — |
| Environments | 8 | 0 | 6 | 0 | auth_service, crud, environment_service | — |
| Settings | 7 | 0 | 4 | 1 | auth_service, settings_service | — |
| Projects | 7 | 1 | 3 | 4 | audit_service, crud | 2/2 |
| Project Detail | 7 | 1 | 0 | 7 | crud, environment_service, settings_service | — |
| Components | 7 | 0 | 3 | 1 | auth_service, component_discovery, crud | — |
| Auth | 6 | 0 | 4 | 3 | auth_service | 2/2 |
| Tests | 6 | 0 | 3 | 1 | crud, test_execution_service | — |
| Resources UI | 6 | 6 | 0 | 5 | resource_manager | 6/6 |
| Configuration | 5 | 0 | 3 | 1 | crud, secret_manager | — |
| Logs | 5 | 1 | 1 | 2 | auth_service, crud, log_service | — |
| Config Generation | 5 | 0 | 0 | 0 | auth_service, config_generator, crud | — |
| Templates | 5 | 2 | 1 | 4 | audit_service, crud, template_service | 3/3 |
| Webhooks | 4 | 0 | 2 | 0 | auth_service, webhook_service | 1/1 |
| CI/CD | 4 | 2 | 0 | 1 | crud, webhook_service | 1/1 |
| Datasources | 4 | 0 | 3 | 0 | auth_service, crud, secret_manager | — |
| Audit Log | 4 | 1 | 0 | 1 | audit_service, auth_service, crud | 2/2 |
| Test Dashboard | 3 | 2 | 0 | 2 | crud | — |
| Project Settings | 2 | 0 | 1 | 1 | auth_service, crud, settings_service | — |
| API | 1 | 0 | 0 | 0 | secret_manager | — |
| Endpoints | 1 | 0 | 0 | 0 | crud | — |

## Shadowed routes

Declared, but the router hands the URL to another route registered earlier. Their code never runs.

| Verb | Path | Handler (line) | Served by |
|---|---|---|---|
| GET | `/settings` | `get_settings` (3475) | serve_settings_page (/settings) |
| GET | `/settings/export` | `export_settings` (3834) | get_setting (/settings/{path:path}) |
| GET | `/jobs` | `list_all_jobs` (5029) | serve_jobs_page (/jobs) |
| GET | `/projects` | `list_projects` (5552) | serve_projects_page (/projects) |
| GET | `/projects/{project_id}` | `get_project` (5890) | serve_project_detail (/projects/{project_id:int}) |

## Interface calls that reach no route

Buttons and screens that call a URL the router does not serve: they always fail.

| Verb | Called URL | Line in main.py | Why |
|---|---|---:|---|
| GET | `/admin/projects/1/datasources` | 1680 | exists without the `/admin` prefix (`/projects/1/datasources` → `list_datasources`) |
| DELETE | `/admin/datasources/1` | 1753 | exists without the `/admin` prefix (`/datasources/1` → `delete_datasource`) |
| POST | `/admin/datasources/1/start` | 1767 | exists without the `/admin` prefix (`/datasources/1/start` → `start_datasource_container`) |
| POST | `/admin/datasources/1/stop` | 1782 | exists without the `/admin` prefix (`/datasources/1/stop` → `stop_datasource_container`) |
| GET | `/admin/datasources/1/logs` | 1820 | exists without the `/admin` prefix (`/datasources/1/logs` → `get_datasource_container_logs`) |
| POST | `/admin/datasources/1/test` | 1844 | exists without the `/admin` prefix (`/datasources/1/test` → `test_datasource_connection`) |
| POST | `/admin/projects/1/environments/defaults` | 1871 | exists without the `/admin` prefix (`/projects/1/environments/defaults` → `create_default_environments`) |
| GET | `/admin/projects/1/environments/1` | 1891 | exists without the `/admin` prefix (`/projects/1/environments/1` → `get_environment`) |
| DELETE | `/admin/projects/1/environments/1` | 1961 | exists without the `/admin` prefix (`/projects/1/environments/1` → `delete_environment`) |
| POST | `/admin/projects/1/environments/1/test` | 1980 | exists without the `/admin` prefix (`/projects/1/environments/1/test` → `test_environment_connection`) |
| POST | `/admin/projects/1/environments/1/launch` | 2007 | exists without the `/admin` prefix (`/projects/1/environments/1/launch` → `launch_app_in_environment`) |
| GET | `/projects/1/test-runs/1` | 2989 | no route |
| POST | `/projects/1/git/pull` | 6274 | no route |

## GETs that respond with an error

| Path | Status | Response |
|---|---|---|
| `/docker/images` | 503 | {"detail":"Docker service not available"} |
| `/docker/volumes` | 503 | {"detail":"Docker service not available"} |
| `/docker/networks` | 503 | {"detail":"Docker service not available"} |
| `/docker/containers` | 503 | {"detail":"Docker service is not available"} |

## Service modules

What the plan (A1) keeps as a library. **Routes** = routes whose handler uses the module; **tests** = test files that cite it.

| Module | Lines | Public | Routes | .q screens | Tests |
|---|---:|---:|---:|---|---|
| `resource_manager` | 1118 | 7 | 31 | — | `test_resource_discovery_without_psutil.py` |
| `connector_service` | 1016 | 6 | 12 | yes | `conftest.py`, `test_admin_services_connectors.py`, `test_admin_services_projects.py` |
| `test_generator` | 782 | 5 | 5 | — | **none** |
| `component_discovery` | 766 | 8 | 7 | — | `test_html_tolerance_everywhere.py` |
| `template_service` | 710 | 3 | 4 | — | **none** |
| `config_generator` | 586 | 2 | 5 | — | **none** |
| `crud` | 557 | 29 | 74 | — | `test_admin_datasource_logs.py`, `test_admin_smoke.py`, `test_delete_project_leaves_nothing_behind.py` |
| `settings_service` | 470 | 10 | 11 | — | `conftest.py`, `conftest.py`, `test_admin_has_no_deploy.py` |
| `docker_service` | 422 | 1 | 1 | — | `test_admin_datasource_logs.py` |
| `environment_service` | 418 | 2 | 9 | — | **none** |
| `auth_service` | 394 | 5 | 90 | — | `test_admin_has_no_default_credentials.py`, `test_admin_screens.py`, `test_admin_services_auth.py` +3 |
| `health_service` | 390 | 10 | 9 | — | **none** |
| `git_service` | 370 | 3 | 0 | — | **none** |
| `test_execution_service` | 364 | 1 | 3 | — | **none** |
| `webhook_service` | 355 | 2 | 7 | — | `test_webhooks_fail_closed.py` |
| `job_service` | 347 | 2 | 26 | — | `test_job_executor.py`, `test_admin_smoke.py` |
| `audit_service` | 346 | 7 | 10 | — | **none** |
| `log_service` | 331 | 8 | 4 | — | **none** |
| `secret_manager` | 278 | 6 | 7 | — | `test_admin_smoke.py`, `test_secret_key_mismatch_is_not_silent.py` |
| `db_setup_service` | 193 | 1 | 2 | — | **none** |

## `.q` screens (quantum_admin/components/admin)

Each screen calls the declared services (`q:invoke service=`, `quantum_admin/services/`); **Status** is the response to a GET without a session — 302 to `/admin/login` on a protected screen.

| Screen | Route | Auth | Status | Actions | Services | q:python (lines) | Python effects | Data source |
|---|---|---|---|---|---:|---|---|---|
| `_layout/AdminShell.q` | `/admin/_layout/AdminShell` | yes | 404 | — | 0 | 0 (0) | — | — |
| `agents.q` | `/admin/agents` | yes | 302 | — | 1 | 0 (0) | — | — |
| `app/[name].q` | `/admin/app/[name]` | yes | 302 | updateProject, createProjectConnector, testConnector, detachConnector, saveProjectConfig, createEnvironment, createDefaultEnvironments, updateEnvironment, deleteEnvironment, startServer, stopServer | 19 | 0 (0) | — | — |
| `applications.q` | `/admin/applications` | yes | 302 | createProject, deleteProject, syncProjects, importYaml | 7 | 0 (0) | — | — |
| `component/[...path].q` | `/admin/component/[...path]` | yes | 302 | generateTests, runTests | 3 | 0 (0) | — | — |
| `components.q` | `/admin/components` | yes | 302 | — | 1 | 0 (0) | — | — |
| `connectors.q` | `/admin/connectors` | yes | 302 | createConnector, updateConnector, deleteConnector, testConnector, testAll | 7 | 0 (0) | — | — |
| `dashboard.q` | `/admin/dashboard` | yes | 302 | — | 2 | 0 (0) | — | — |
| `database.q` | `/admin/database` | yes | 302 | — | 1 | 0 (0) | — | — |
| `features.q` | `/admin/features` | yes | 302 | — | 1 | 0 (0) | — | — |
| `index.q` | `/admin` | yes | 302 | — | 0 | 0 (0) | — | — |
| `jobs.q` | `/admin/jobs` | yes | 302 | — | 1 | 0 (0) | — | — |
| `login.q` | `/admin/login` | **no** | 200 | signIn | 1 | 0 (0) | — | — |
| `logout.q` | `/admin/logout` | **no** | 200 | signOut | 0 | 0 (0) | — | — |
| `settings.q` | `/admin/settings` | yes | 302 | saveSettings | 3 | 0 (0) | — | — |
| `source.q` | `/admin/source` | yes | 302 | — | 1 | 0 (0) | — | — |
| `tests.q` | `/admin/tests` | yes | 302 | — | 1 | 0 (0) | — | — |

## Routes

### API

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/datasources/by-name/{name}` | api | `get_datasource_by_name` (5994, 50) | secret_manager | — | — |

### Admin UI

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/` | page | `serve_admin_ui_root` (372, 3) | — | yes | 200 |
| GET | `/admin` | page | `serve_admin_ui_root` (372, 3) | — | yes | 200 |
| GET | `/admin/` | page | `serve_admin_ui_root` (372, 3) | — | yes | 200 |
| GET | `/admin/cicd` | page | `serve_cicd_page` (454, 2) | — | yes | 200 |
| GET | `/admin/components` | page | `serve_components_page` (484, 2) | — | yes | 200 |
| GET | `/admin/docker` | page | `serve_docker_page` (442, 2) | — | yes | 200 |
| GET | `/admin/jobs` | page | `serve_jobs_page` (448, 2) | — | yes | 200 |
| GET | `/admin/login` | page | `serve_login_page` (421, 2) | — | — | 200 |
| GET | `/admin/logout` | page | `serve_logout_page` (427, 4) | — | yes | 307 |
| GET | `/admin/projects` | page | `serve_projects_page` (436, 2) | — | yes | 200 |
| GET | `/admin/projects/{project_id:int}` | page | `serve_project_detail` (406, 11) | crud | yes | — |
| GET | `/admin/resources` | page | `serve_resources_page` (472, 2) | — | yes | 200 |
| GET | `/admin/settings` | page | `serve_settings_page` (466, 2) | — | yes | 200 |
| GET | `/admin/tests` | page | `serve_tests_page` (460, 2) | — | yes | 200 |
| GET | `/admin/users` | page | `serve_users_page` (478, 2) | — | yes | 200 |
| GET | `/cicd` | page | `serve_cicd_page` (454, 2) | — | yes | 200 |
| GET | `/components` | page | `serve_components_page` (484, 2) | — | yes | 200 |
| GET | `/docker` | page | `serve_docker_page` (442, 2) | — | yes | 200 |
| GET | `/jobs` | page | `serve_jobs_page` (448, 2) | — | yes | 200 |
| GET | `/login` | page | `serve_login_page` (421, 2) | — | — | 200 |
| GET | `/logout` | page | `serve_logout_page` (427, 4) | — | yes | 307 |
| GET | `/projects` | page | `serve_projects_page` (436, 2) | — | yes | 200 |
| GET | `/projects/{project_id:int}` | page | `serve_project_detail` (406, 11) | crud | yes | — |
| GET | `/resources` | page | `serve_resources_page` (472, 2) | — | yes | 200 |
| GET | `/settings` | page | `serve_settings_page` (466, 2) | — | yes | 200 |
| GET | `/tests` | page | `serve_tests_page` (460, 2) | — | yes | 200 |
| GET | `/users` | page | `serve_users_page` (478, 2) | — | yes | 200 |

### Audit Log

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/audit-log` | api | `get_project_audit_log` (9150, 30) | audit_service, auth_service, crud | — | — |
| GET | `/api/projects/{project_id}/audit-log-html` | page | `get_project_audit_log_html` (9183, 64) | audit_service, crud | yes | — |
| GET | `/audit-log` | api | `get_global_audit_log` (9250, 19) | audit_service, auth_service | — | 200 |
| GET | `/audit-log/stats` | api | `get_audit_stats` (9272, 9) | audit_service, auth_service | — | 200 |

### Auth

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/auth/change-password` | api | `change_password` (3453, 15) | auth_service | — | — |
| POST | `/auth/login` | api | `login` (3333, 28) | auth_service | yes | — |
| GET | `/auth/me` | api | `get_me` (3364, 7) | auth_service | — | 200 |
| GET | `/auth/users` | api | `list_users` (3374, 4) | auth_service | — | 200 |
| POST | `/auth/users` | api | `create_user` (3381, 40) | auth_service | yes | — |
| DELETE | `/auth/users/{username}` | api | `delete_user` (3424, 26) | auth_service | yes | — |

### CI/CD

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/ci-cd/dashboard` | page | `get_cicd_dashboard_html` (4849, 167) | crud, webhook_service | — | — |
| GET | `/api/webhooks/events-html` | page | `get_webhooks_events_html` (5822, 24) | — | yes | 200 |
| GET | `/projects/{project_id}/badge.svg` | api | `get_build_badge` (4731, 50) | crud, webhook_service | — | — |
| GET | `/projects/{project_id}/tests/badge.svg` | api | `get_tests_badge` (4784, 39) | crud | — | — |

### Components

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/components/validate` | api | `validate_component_file` (7255, 19) | auth_service, component_discovery | — | — |
| GET | `/projects/{project_id}/components` | api | `list_components` (7021, 12) | crud | — | — |
| GET | `/projects/{project_id}/components/dependencies` | api | `get_dependency_graph` (7193, 29) | component_discovery, crud | — | — |
| POST | `/projects/{project_id}/components/discover` | api | `discover_components` (7043, 43) | auth_service, component_discovery, crud | — | — |
| POST | `/projects/{project_id}/components/sync` | api | `sync_components` (7089, 34) | auth_service, component_discovery, crud | yes | — |
| GET | `/projects/{project_id}/components/unused` | api | `get_unused_components` (7225, 27) | component_discovery, crud | — | — |
| GET | `/projects/{project_id}/components/{component_id}/details` | api | `get_component_details` (7126, 64) | component_discovery | — | — |

### Config Generation

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/config/docker-compose` | api | `generate_docker_compose` (10463, 21) | auth_service, config_generator | — | — |
| GET | `/projects/{project_id}/config/download/{config_type}` | api | `download_config` (10536, 46) | auth_service, config_generator, crud | — | — |
| GET | `/projects/{project_id}/config/env` | api | `generate_env_file` (10437, 23) | auth_service, config_generator | — | — |
| GET | `/projects/{project_id}/config/nginx` | api | `generate_nginx_config` (10487, 21) | auth_service, config_generator | — | — |
| GET | `/projects/{project_id}/config/systemd` | api | `generate_systemd_service` (10511, 22) | auth_service, config_generator, crud | — | — |

### Configuration

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/configuration/history` | api | `get_configuration_history` (9123, 20) | crud | — | — |
| GET | `/projects/{project_id}/environment-variables` | api | `list_environment_variables` (8889, 39) | crud, secret_manager | yes | — |
| POST | `/projects/{project_id}/environment-variables` | api | `create_environment_variable` (8931, 70) | crud, secret_manager | — | — |
| DELETE | `/projects/{project_id}/environment-variables/{key}` | api | `delete_environment_variable` (9084, 36) | crud | — | — |
| PUT | `/projects/{project_id}/environment-variables/{key}` | api | `update_environment_variable` (9004, 77) | crud, secret_manager | — | — |

### Connectors

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/settings/connectors` | api | `list_connectors` (3509, 81) | connector_service | yes | 200 |
| POST | `/settings/connectors` | api | `create_connector` (3607, 12) | connector_service | — | — |
| GET | `/settings/connectors/id/{connector_id}` | api | `get_connector` (3622, 12) | connector_service | yes | — |
| GET | `/settings/connectors/providers` | api | `get_connector_providers` (3593, 11) | connector_service | — | 200 |
| POST | `/settings/connectors/test` | api | `test_connector_data` (3691, 6) | connector_service | yes | — |
| GET | `/settings/connectors/type/{connector_type}` | api | `list_connectors_by_type` (3730, 3) | — | — | — |
| GET | `/settings/connectors/type/{connector_type}/default` | api | `get_default_connector` (3736, 9) | connector_service | — | — |
| DELETE | `/settings/connectors/{connector_id}` | api | `delete_connector` (3652, 12) | connector_service | yes | — |
| PUT | `/settings/connectors/{connector_id}` | api | `update_connector` (3637, 12) | connector_service | — | — |
| POST | `/settings/connectors/{connector_id}/default` | api | `set_connector_default` (3667, 12) | connector_service | yes | — |
| POST | `/settings/connectors/{connector_id}/docker/start` | api | `start_connector_docker` (3700, 12) | connector_service | — | — |
| POST | `/settings/connectors/{connector_id}/docker/stop` | api | `stop_connector_docker` (3715, 12) | connector_service | — | — |
| POST | `/settings/connectors/{connector_id}/test` | api | `test_connector` (3682, 6) | connector_service | yes | — |

### Dashboard

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/dashboard` | page | `get_main_dashboard_html` (10964, 162) | crud, job_service, webhook_service | — | 200 |
| GET | `/api/docker/dashboard` | page | `get_docker_dashboard_html` (11198, 160) | — | yes | 200 |
| GET | `/api/projects/list-html` | page | `get_projects_list_html` (11129, 66) | crud | — | 200 |
| GET | `/api/projects/{project_id}/components/dashboard` | page | `get_components_dashboard_html` (11700, 221) | crud | yes | — |
| GET | `/api/settings/dashboard` | page | `get_settings_dashboard_html` (11514, 139) | auth_service, settings_service | — | 200 |
| GET | `/api/users/dashboard` | page | `get_users_dashboard_html` (11361, 150) | auth_service | — | 200 |
| GET | `/dashboard/activity` | page | `get_dashboard_activity_html` (9831, 43) | audit_service | yes | 200 |
| GET | `/dashboard/activity-legacy` | api | `get_dashboard_activity_legacy` (4039, 43) | audit_service, auth_service | — | 200 |
| GET | `/dashboard/stats` | api | `get_dashboard_stats` (3863, 173) | auth_service, crud, job_service | yes | 200 |

### Datasources

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| DELETE | `/datasources/{datasource_id}` | api | `delete_datasource` (6985, 29) | crud | — | — |
| PUT | `/datasources/{datasource_id}` | api | `update_datasource` (6938, 44) | auth_service, crud, secret_manager | — | — |
| GET | `/projects/{project_id}/datasources` | api | `list_datasources` (5977, 12) | crud | — | — |
| POST | `/projects/{project_id}/datasources` | api | `create_datasource` (6831, 100) | crud, secret_manager | — | — |

### Docker

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/datasources/{datasource_id}/logs` | api | `get_datasource_container_logs` (7460, 41) | crud | — | — |
| POST | `/datasources/{datasource_id}/restart` | api | `restart_datasource_container` (7413, 44) | crud | — | — |
| POST | `/datasources/{datasource_id}/setup` | api | `setup_datasource` (7744, 61) | crud, db_setup_service | — | — |
| POST | `/datasources/{datasource_id}/start` | api | `start_datasource_container` (7281, 82) | crud, db_setup_service | — | — |
| GET | `/datasources/{datasource_id}/status` | api | `get_datasource_container_status` (7592, 40) | crud | — | — |
| POST | `/datasources/{datasource_id}/stop` | api | `stop_datasource_container` (7366, 44) | crud | — | — |
| POST | `/datasources/{datasource_id}/test` | api | `test_datasource_connection` (7504, 85) | crud, secret_manager | — | — |
| POST | `/docker/connect` | api | `docker_connect` (3251, 29) | docker_service | yes | — |
| GET | `/docker/containers` | api | `list_all_containers` (7640, 101) | — | yes | 503 |
| DELETE | `/docker/containers/{container_id}` | api | `remove_docker_container` (4374, 19) | — | — | — |
| GET | `/docker/containers/{container_id}/logs` | api | `get_container_logs` (4352, 19) | — | — | — |
| POST | `/docker/containers/{container_id}/restart` | api | `restart_container` (4330, 19) | — | — | — |
| POST | `/docker/containers/{container_id}/start` | api | `start_container` (4286, 19) | — | yes | — |
| POST | `/docker/containers/{container_id}/stop` | api | `stop_container` (4308, 19) | — | yes | — |
| GET | `/docker/images` | api | `list_docker_images` (4199, 26) | — | yes | 503 |
| GET | `/docker/info` | api | `get_docker_info` (4124, 72) | — | yes | 200 |
| GET | `/docker/networks` | api | `list_docker_networks` (4256, 27) | — | yes | 503 |
| GET | `/docker/status` | api | `docker_status` (3196, 52) | — | yes | 200 |
| GET | `/docker/volumes` | api | `list_docker_volumes` (4228, 25) | — | yes | 503 |

### Endpoints

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/endpoints` | api | `list_endpoints` (7812, 12) | crud | — | — |

### Environments

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/environments` | api | `list_environments` (4408, 9) | environment_service | — | — |
| POST | `/projects/{project_id}/environments` | api | `create_environment` (4420, 13) | auth_service, environment_service | — | — |
| POST | `/projects/{project_id}/environments/defaults` | api | `create_default_environments` (4596, 9) | auth_service, environment_service | — | — |
| DELETE | `/projects/{project_id}/environments/{env_id}` | api | `delete_environment` (4466, 11) | auth_service, environment_service | — | — |
| GET | `/projects/{project_id}/environments/{env_id}` | api | `get_environment` (4436, 11) | environment_service | — | — |
| PUT | `/projects/{project_id}/environments/{env_id}` | api | `update_environment` (4450, 13) | auth_service, environment_service | — | — |
| POST | `/projects/{project_id}/environments/{env_id}/launch` | api | `launch_app_in_environment` (4492, 101) | crud, environment_service, *subprocess* | — | — |
| POST | `/projects/{project_id}/environments/{env_id}/test` | api | `test_environment_connection` (4480, 9) | environment_service | — | — |

### Health

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/health` | api | `get_project_health` (9647, 20) | auth_service, crud, health_service | — | — |
| POST | `/api/projects/{project_id}/health-checks` | api | `create_health_check_endpoint` (9721, 30) | auth_service, crud, health_service | — | — |
| POST | `/api/projects/{project_id}/health-checks/run` | api | `run_project_health_checks` (9754, 14) | auth_service, crud, health_service | — | — |
| GET | `/api/projects/{project_id}/health-html` | page | `get_project_health_html` (9670, 48) | health_service | — | — |
| GET | `/api/projects/{project_id}/incidents` | api | `get_project_incidents` (9771, 16) | auth_service, crud, health_service | — | — |
| GET | `/health` | api | `health_check` (3186, 7) | — | — | 200 |
| GET | `/health/database` | api | `health_database` (4085, 32) | — | yes | 200 |
| GET | `/health/system` | api | `get_system_health` (9613, 6) | health_service | — | 200 |
| GET | `/health/system-html` | page | `get_system_health_html` (9622, 22) | health_service | — | 200 |
| POST | `/incidents/{incident_id}/acknowledge` | api | `acknowledge_incident_endpoint` (9812, 16) | auth_service, health_service | — | — |
| POST | `/incidents/{incident_id}/resolve` | api | `resolve_incident_endpoint` (9790, 19) | auth_service, health_service | — | — |

### Jobs

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/jobs-list` | page | `get_jobs_list_html` (5683, 41) | job_service | yes | 200 |
| GET | `/api/jobs/dashboard` | page | `get_jobs_dashboard_html` (5266, 279) | job_service | yes | 200 |
| GET | `/api/jobs/overview-html` | page | `get_jobs_overview_html` (5727, 23) | job_service | yes | 200 |
| GET | `/api/queues-list` | page | `get_queues_list_html` (5795, 24) | job_service | yes | 200 |
| GET | `/api/schedules-list` | page | `get_schedules_list_html` (5753, 18) | job_service | yes | 200 |
| GET | `/api/threads-list` | page | `get_threads_list_html` (5774, 18) | job_service | yes | 200 |
| GET | `/jobs` | api | `list_all_jobs` (5029, 12) | auth_service, job_service | — | shadowed |
| POST | `/jobs/dispatch` | api | `dispatch_job` (5090, 20) | auth_service, job_service | — | — |
| GET | `/jobs/overview` | api | `get_jobs_overview` (5044, 4) | auth_service, job_service | — | 200 |
| GET | `/jobs/{job_id}` | api | `get_job_details` (5051, 10) | auth_service, job_service | — | — |
| POST | `/jobs/{job_id}/cancel` | api | `cancel_job` (5064, 10) | auth_service, job_service | yes | — |
| POST | `/jobs/{job_id}/retry` | api | `retry_job` (5077, 10) | auth_service, job_service | yes | — |
| GET | `/queues` | api | `list_queues` (5233, 4) | auth_service, job_service | — | 200 |
| POST | `/queues/{queue}/purge` | api | `purge_queue` (5250, 9) | auth_service, job_service | yes | — |
| GET | `/queues/{queue}/stats` | api | `get_queue_stats` (5240, 7) | auth_service, job_service | — | — |
| GET | `/schedules` | api | `list_schedules` (5117, 4) | auth_service, job_service | — | 200 |
| DELETE | `/schedules/{name}` | api | `remove_schedule` (5176, 10) | auth_service, job_service | — | — |
| GET | `/schedules/{name}` | api | `get_schedule_details` (5124, 10) | auth_service, job_service | — | — |
| POST | `/schedules/{name}/pause` | api | `pause_schedule` (5137, 10) | auth_service, job_service | yes | — |
| POST | `/schedules/{name}/resume` | api | `resume_schedule` (5150, 10) | auth_service, job_service | yes | — |
| POST | `/schedules/{name}/run` | api | `run_schedule_now` (5163, 10) | auth_service, job_service | yes | — |
| GET | `/threads` | api | `list_threads` (5193, 7) | auth_service, job_service | — | 200 |
| GET | `/threads/{name}` | api | `get_thread_details` (5203, 10) | auth_service, job_service | — | — |
| POST | `/threads/{name}/terminate` | api | `terminate_thread` (5216, 10) | auth_service, job_service | — | — |

### Logs

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/logs` | api | `get_project_logs` (9288, 59) | auth_service, crud, log_service | — | — |
| GET | `/api/projects/{project_id}/logs-html` | page | `get_project_logs_html` (9350, 99) | crud, log_service | yes | — |
| GET | `/api/projects/{project_id}/logs/export` | api | `export_project_logs` (9452, 53) | crud, log_service | — | — |
| POST | `/api/projects/{project_id}/logs/generate-sample` | api | `generate_sample_logs` (9508, 80) | crud | — | — |
| GET | `/api/projects/{project_id}/logs/stats` | api | `get_project_log_stats` (9591, 15) | crud, log_service | yes | — |

### Project Detail

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/connectors-html` | api | `get_project_connectors_html` (6439, 88) | — | yes | — |
| GET | `/api/projects/{project_id}/datasources-html` | api | `get_project_datasources_html` (6290, 146) | crud | yes | — |
| GET | `/api/projects/{project_id}/environments-html` | api | `get_project_environments_html` (6530, 98) | environment_service | yes | — |
| GET | `/api/projects/{project_id}/general` | api | `get_project_general_html` (6087, 58) | crud | yes | — |
| GET | `/api/projects/{project_id}/header` | api | `get_project_header_html` (6051, 33) | crud | yes | — |
| GET | `/api/projects/{project_id}/paths-html` | api | `get_project_paths_html` (6631, 192) | crud, settings_service | yes | — |
| GET | `/api/projects/{project_id}/source-html` | page | `get_project_source_html` (6148, 139) | crud | yes | — |

### Project Settings

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/settings` | api | `get_project_settings` (3789, 16) | auth_service, crud, settings_service | — | — |
| PUT | `/projects/{project_id}/settings` | api | `update_project_settings` (3808, 23) | auth_service, crud, settings_service | yes | — |

### Projects

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects` | api | `get_projects_json` (5676, 4) | crud | yes | 200 |
| GET | `/api/projects-grid` | page | `get_projects_grid` (5620, 53) | crud | yes | 200 |
| GET | `/projects` | api | `list_projects` (5552, 65) | crud | — | shadowed |
| POST | `/projects` | api | `create_project` (5854, 33) | audit_service, crud | — | — |
| DELETE | `/projects/{project_id}` | api | `delete_project` (5943, 27) | audit_service, crud | yes | — |
| GET | `/projects/{project_id}` | api | `get_project` (5890, 9) | crud | — | shadowed |
| PUT | `/projects/{project_id}` | api | `update_project` (5902, 38) | audit_service, crud | yes | — |

### Resources

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/resources/containers` | api | `get_docker_containers_resource` (10016, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/overview` | api | `get_resources_overview` (9882, 19) | auth_service, resource_manager | — | 200 |
| GET | `/resources/overview-html` | page | `get_resources_overview_html` (9904, 79) | resource_manager | yes | 200 |
| GET | `/resources/ports` | api | `list_port_allocations` (10049, 17) | auth_service, resource_manager | — | 200 |
| POST | `/resources/ports/allocate` | api | `allocate_port` (10069, 32) | auth_service, resource_manager | — | — |
| GET | `/resources/ports/check/{port}` | api | `check_port_availability` (10123, 9) | resource_manager | — | — |
| GET | `/resources/ports/discovered` | api | `get_discovered_ports` (9996, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/ports/ranges` | api | `list_port_ranges` (10135, 8) | auth_service, resource_manager | — | 200 |
| POST | `/resources/ports/ranges` | api | `create_port_range` (10146, 21) | auth_service, resource_manager | — | — |
| POST | `/resources/ports/release` | api | `release_port` (10104, 16) | auth_service, resource_manager | yes | — |
| POST | `/resources/ports/reserve` | api | `reserve_port` (10170, 17) | auth_service, resource_manager | — | — |
| GET | `/resources/processes` | api | `get_quantum_processes` (10006, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/scan` | api | `scan_resources` (9986, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/secrets` | api | `list_secrets` (10194, 33) | auth_service, resource_manager | — | 200 |
| POST | `/resources/secrets` | api | `create_or_update_secret` (10230, 33) | auth_service, resource_manager | — | — |
| DELETE | `/resources/secrets/{secret_id}` | api | `delete_secret` (10266, 15) | auth_service, resource_manager | yes | — |
| POST | `/resources/secrets/{secret_id}/rotate` | api | `rotate_secret` (10284, 16) | auth_service, resource_manager | yes | — |
| GET | `/resources/services` | api | `list_services` (10307, 21) | auth_service, resource_manager | — | 200 |
| POST | `/resources/services` | api | `register_service` (10331, 31) | auth_service, resource_manager | — | — |
| GET | `/resources/services/discover/{service_type}` | api | `discover_services` (10410, 14) | resource_manager | — | — |
| POST | `/resources/services/health-check` | api | `run_health_checks` (10394, 13) | auth_service, resource_manager | yes | — |
| DELETE | `/resources/services/{service_id}` | api | `unregister_service` (10365, 15) | auth_service, resource_manager | yes | — |
| GET | `/resources/services/{service_id}/health` | api | `check_service_health` (10383, 8) | resource_manager | yes | — |
| POST | `/resources/sync` | api | `sync_discovered_resources` (10036, 10) | auth_service, resource_manager | yes | — |
| GET | `/resources/system` | api | `get_system_resources` (10026, 7) | auth_service, resource_manager | — | 200 |

### Resources UI

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/resources/containers-html` | page | `get_discovered_containers_html` (10912, 45) | resource_manager | yes | 200 |
| GET | `/api/resources/discovered-ports-html` | page | `get_discovered_ports_html` (10869, 40) | resource_manager | yes | 200 |
| GET | `/api/resources/ports-html` | page | `get_ports_html` (10625, 75) | resource_manager | yes | 200 |
| GET | `/api/resources/secrets-html` | page | `get_secrets_html` (10703, 83) | resource_manager | yes | 200 |
| GET | `/api/resources/services-html` | page | `get_services_html` (10789, 77) | resource_manager | yes | 200 |
| GET | `/api/resources/stats` | page | `get_resources_stats_html` (10589, 33) | resource_manager | — | 200 |

### Settings

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/api/settings/docker` | api | `save_docker_settings` (11656, 41) | auth_service, settings_service | yes | — |
| GET | `/settings` | api | `get_settings` (3475, 4) | auth_service, settings_service | — | shadowed |
| PUT | `/settings` | api | `update_settings` (3482, 14) | auth_service, settings_service | — | — |
| GET | `/settings/export` | api | `export_settings` (3834, 4) | auth_service, settings_service | — | shadowed |
| POST | `/settings/import` | api | `import_settings` (3841, 15) | auth_service, settings_service | — | — |
| GET | `/settings/{path:path}` | api | `get_setting` (3748, 14) | auth_service, settings_service | — | — |
| PUT | `/settings/{path:path}` | api | `set_setting` (3765, 17) | auth_service, settings_service | — | — |

### Templates

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/create-project-wizard` | page | `get_create_project_wizard` (12052, 192) | — | yes | 200 |
| POST | `/projects/from-template` | api | `create_project_from_template` (11972, 77) | audit_service, crud, template_service | yes | — |
| GET | `/templates` | api | `list_templates` (11928, 5) | template_service | — | 200 |
| GET | `/templates-html` | page | `get_templates_html` (11946, 23) | template_service | yes | 200 |
| GET | `/templates/{template_id}` | api | `get_template` (11936, 7) | template_service | yes | — |

### Test Dashboard

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/tests/dashboard` | page | `get_test_dashboard_html` (8610, 149) | crud | yes | — |
| GET | `/api/projects/{project_id}/tests/runs/{run_id}/details` | page | `get_test_run_details_html` (8762, 76) | crud | yes | — |
| GET | `/api/projects/{project_id}/tests/summary` | api | `get_test_summary` (8841, 41) | crud | — | — |

### Test Generator

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/api/projects/{project_id}/components/generate-missing-tests` | api | `generate_missing_tests` (8342, 63) | auth_service, crud, test_generator | yes | — |
| POST | `/api/projects/{project_id}/components/sync-tests` | api | `sync_component_tests` (8318, 21) | auth_service, component_discovery | yes | — |
| GET | `/api/projects/{project_id}/components/{component_id}/tests` | api | `get_component_tests` (8520, 33) | — | — | — |
| POST | `/api/projects/{project_id}/components/{component_id}/tests/run` | api | `run_component_tests` (8159, 156) | auth_service, crud, *subprocess* | yes | — |
| POST | `/api/projects/{project_id}/tests/run-all` | api | `run_all_tests` (8408, 109) | auth_service, crud, *subprocess* | yes | — |
| POST | `/projects/{project_id}/components/{component_id}/tests/generate` | api | `generate_tests_for_component` (8110, 46) | auth_service, test_generator | yes | — |
| POST | `/projects/{project_id}/tests/conftest` | api | `generate_conftest` (8582, 21) | auth_service, test_generator | — | — |
| GET | `/projects/{project_id}/tests/coverage-estimate` | api | `get_test_coverage_estimate` (8556, 23) | crud, test_generator | — | — |
| POST | `/projects/{project_id}/tests/generate` | api | `generate_tests_for_project` (8056, 51) | auth_service, crud, test_generator | — | — |

### Tests

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/projects/{project_id}/tests/run` | api | `run_tests` (7836, 47) | crud, test_execution_service | yes | — |
| GET | `/projects/{project_id}/tests/runs` | api | `list_test_runs` (7886, 22) | crud | — | — |
| DELETE | `/projects/{project_id}/tests/runs/{run_id}` | api | `delete_test_run` (8015, 27) | crud | — | — |
| GET | `/projects/{project_id}/tests/runs/{run_id}` | api | `get_test_run` (7911, 28) | crud | — | — |
| POST | `/projects/{project_id}/tests/runs/{run_id}/cancel` | api | `cancel_test_run` (7979, 33) | crud, test_execution_service | — | — |
| GET | `/projects/{project_id}/tests/runs/{run_id}/status` | api | `get_test_run_status` (7942, 34) | crud, test_execution_service | — | — |

### Webhooks

| Verb | Path | Kind | Handler (line, lines) | Uses | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/webhooks/events` | api | `list_webhook_events` (4700, 10) | auth_service, webhook_service | — | 200 |
| GET | `/webhooks/events/{event_id}` | api | `get_webhook_event` (4713, 11) | auth_service, webhook_service | — | — |
| POST | `/webhooks/github` | api | `github_webhook` (4612, 43) | webhook_service | — | — |
| POST | `/webhooks/gitlab` | api | `gitlab_webhook` (4658, 39) | webhook_service | — | — |
