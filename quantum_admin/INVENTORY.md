# Inventário do Quantum Admin

> **Gerado** por `python scripts/admin-inventory.py` — não editar à mão. Medido, não declarado: rotas lidas da AST de `quantum_admin/backend/main.py`, sombreamento perguntado ao roteador real, status de cada GET autenticado contra um banco temporário, telas `.q` servidas de uma cópia temporária. Rotas de escrita não são executadas.

**268 rotas FastAPI** em 33 áreas · 63 páginas HTML · 8 sombreadas (nunca alcançadas) · GET sem parâmetro medidos: 83/87 respondem sem erro · **23 módulos de serviço** · **16 telas `.q`**, 16 sem `require_auth`, 36 blocos `q:python`.

A interface do admin (HTML e JS gerados dentro de `main.py`) faz **143 chamadas** com URL legível (7 usam uma variável e não entram na conta). **17 não chegam a rota nenhuma**. **135 rotas de API não são chamadas pela interface** — candidatas a sair se também não servirem a nada fora dela (A2).

## Áreas

| Área | Rotas | Páginas | Escrita | Chamadas pela UI | Serviços usados | GET medidos ok |
|---|---:|---:|---:|---:|---|---|
| Admin UI | 29 | 29 | 0 | 27 | crud | 27/27 |
| Resources | 25 | 1 | 11 | 8 | auth_service, resource_manager | 11/11 |
| Jobs | 24 | 6 | 9 | 12 | auth_service, job_service | 10/10 |
| Docker | 20 | 0 | 10 | 9 | crud, db_setup_service, docker_service, secret_manager | 2/6 |
| Connectors | 13 | 0 | 8 | 6 | connector_service | 2/2 |
| Health | 11 | 2 | 4 | 1 | auth_service, crud, health_service | 4/4 |
| Cloud Integrations | 10 | 1 | 5 | 3 | audit_service, secret_manager | 1/1 |
| Dashboard | 9 | 7 | 0 | 4 | audit_service, auth_service, crud, job_service, settings_service, webhook_service | 8/8 |
| Environments | 9 | 0 | 7 | 0 | auth_service, crud, environment_service | — |
| Test Generator | 9 | 0 | 7 | 5 | auth_service, component_discovery, crud, test_generator | — |
| Settings | 7 | 0 | 4 | 2 | auth_service, settings_service | — |
| Deploy | 7 | 1 | 4 | 1 | audit_service, auth_service, crud, deploy_service | 1/1 |
| CI/CD | 7 | 2 | 1 | 2 | auth_service, crud, pipeline_service, webhook_service | 1/1 |
| Projects | 7 | 1 | 3 | 4 | audit_service, crud | 2/2 |
| Project Detail | 7 | 1 | 0 | 7 | crud, environment_service, settings_service | — |
| Components | 7 | 0 | 3 | 1 | auth_service, component_discovery, crud | — |
| Auth | 6 | 0 | 4 | 3 | auth_service | 2/2 |
| Deploy Pipeline | 6 | 0 | 4 | 1 | auth_service, pipeline_service, websocket_manager | — |
| Tests | 6 | 0 | 3 | 1 | crud, test_execution_service | — |
| Resources UI | 6 | 6 | 0 | 5 | resource_manager | 6/6 |
| Configuration | 5 | 0 | 3 | 1 | crud, secret_manager | — |
| Logs | 5 | 1 | 1 | 2 | auth_service, crud, log_service | — |
| Config Generation | 5 | 0 | 0 | 0 | auth_service, config_generator, crud | — |
| Templates | 5 | 2 | 1 | 4 | audit_service, crud, template_service | 3/3 |
| Webhooks | 4 | 0 | 2 | 0 | auth_service, webhook_service | 1/1 |
| Datasources | 4 | 0 | 3 | 0 | auth_service, crud, secret_manager | — |
| Audit Log | 4 | 1 | 0 | 1 | audit_service, auth_service, crud | 2/2 |
| Deploy Versions | 3 | 0 | 0 | 0 | auth_service | — |
| Test Dashboard | 3 | 2 | 0 | 2 | crud | — |
| Project Settings | 2 | 0 | 1 | 1 | auth_service, crud, settings_service | — |
| — | 1 | 0 | 0 | 0 | websocket_manager | — |
| API | 1 | 0 | 0 | 0 | secret_manager | — |
| Endpoints | 1 | 0 | 0 | 0 | crud | — |

## Rotas sombreadas

Declaradas, mas o roteador entrega a URL a outra rota registrada antes. O código delas não roda.

| Verbo | Caminho | Handler (linha) | Atendida por |
|---|---|---|---|
| GET | `/settings` | `get_settings` (4534) | serve_settings_page (/settings) |
| GET | `/settings/export` | `export_settings` (4893) | get_setting (/settings/{path:path}) |
| GET | `/jobs` | `list_all_jobs` (6783) | serve_jobs_page (/jobs) |
| GET | `/projects` | `list_projects` (7352) | serve_projects_page (/projects) |
| GET | `/projects/{project_id}` | `get_project` (7690) | serve_project_detail (/projects/{project_id:int}) |
| GET | `/settings/cloud` | `get_cloud_integrations_html` (13771) | get_setting (/settings/{path:path}) |
| GET | `/settings/cloud/{integration_id}` | `get_cloud_integration` (13836) | get_setting (/settings/{path:path}) |
| PUT | `/settings/cloud/{integration_id}` | `update_cloud_integration` (13899) | set_setting (/settings/{path:path}) |

## Chamadas da interface que não chegam a uma rota

Botões e telas que chamam uma URL que o roteador não atende: falham sempre.

| Verbo | URL chamada | Linha em main.py | Por quê |
|---|---|---:|---|
| GET | `/admin/projects/1/datasources` | 1709 | existe sem o prefixo `/admin` (`/projects/1/datasources` → `list_datasources`) |
| DELETE | `/admin/datasources/1` | 1782 | existe sem o prefixo `/admin` (`/datasources/1` → `delete_datasource`) |
| POST | `/admin/datasources/1/start` | 1796 | existe sem o prefixo `/admin` (`/datasources/1/start` → `start_datasource_container`) |
| POST | `/admin/datasources/1/stop` | 1811 | existe sem o prefixo `/admin` (`/datasources/1/stop` → `stop_datasource_container`) |
| GET | `/admin/datasources/1/logs` | 1849 | existe sem o prefixo `/admin` (`/datasources/1/logs` → `get_datasource_container_logs`) |
| POST | `/admin/datasources/1/test` | 1873 | existe sem o prefixo `/admin` (`/datasources/1/test` → `test_datasource_connection`) |
| POST | `/admin/projects/1/environments/defaults` | 1900 | existe sem o prefixo `/admin` (`/projects/1/environments/defaults` → `create_default_environments`) |
| GET | `/admin/projects/1/environments/1` | 1920 | existe sem o prefixo `/admin` (`/projects/1/environments/1` → `get_environment`) |
| DELETE | `/admin/projects/1/environments/1` | 1998 | existe sem o prefixo `/admin` (`/projects/1/environments/1` → `delete_environment`) |
| POST | `/admin/projects/1/environments/1/test` | 2017 | existe sem o prefixo `/admin` (`/projects/1/environments/1/test` → `test_environment_connection`) |
| POST | `/admin/projects/1/environments/1/launch` | 2051 | existe sem o prefixo `/admin` (`/projects/1/environments/1/launch` → `launch_app_in_environment`) |
| GET | `/admin/projects/1/environments` | 2403 | existe sem o prefixo `/admin` (`/projects/1/environments` → `list_environments`) |
| POST | `/admin/deploy/pipeline/1/cancel` | 2557 | existe sem o prefixo `/admin` (`/deploy/pipeline/1/cancel` → `cancel_pipeline`) |
| POST | `/admin/projects/1/environments/defaults` | 2623 | existe sem o prefixo `/admin` (`/projects/1/environments/defaults` → `create_default_environments`) |
| POST | `/admin/projects/1/environments/1/test` | 2712 | existe sem o prefixo `/admin` (`/projects/1/environments/1/test` → `test_environment_connection`) |
| GET | `/projects/1/test-runs/1` | 4048 | nenhuma rota |
| POST | `/projects/1/git/pull` | 8074 | nenhuma rota |

## GETs que respondem com erro

| Caminho | Status | Resposta |
|---|---|---|
| `/docker/images` | 503 | {"detail":"Docker service not available"} |
| `/docker/volumes` | 503 | {"detail":"Docker service not available"} |
| `/docker/networks` | 503 | {"detail":"Docker service not available"} |
| `/docker/containers` | 503 | {"detail":"Docker service is not available"} |

## Módulos de serviço

O que o plano (A1) preserva como biblioteca. **Rotas** = rotas cujo handler usa o módulo; **testes** = arquivos de teste que o citam.

| Módulo | Linhas | Públicos | Rotas | Telas .q | Testes |
|---|---:|---:|---:|---|---|
| `resource_manager` | 1118 | 7 | 31 | — | `test_resource_discovery_without_psutil.py` |
| `connector_service` | 983 | 5 | 12 | — | **nenhum** |
| `pipeline_service` | 812 | 6 | 6 | — | **nenhum** |
| `test_generator` | 782 | 5 | 5 | — | **nenhum** |
| `component_discovery` | 766 | 8 | 7 | — | `test_html_tolerance_everywhere.py` |
| `template_service` | 710 | 3 | 4 | — | **nenhum** |
| `deploy_service` | 698 | 6 | 6 | — | `test_deploy_build_is_real.py`, `test_deploy_package_and_status.py`, `test_deploy_steps_do_not_lie.py` |
| `config_generator` | 586 | 2 | 5 | — | **nenhum** |
| `crud` | 557 | 29 | 78 | — | `test_admin_smoke.py`, `test_delete_project_leaves_nothing_behind.py` |
| `settings_service` | 485 | 12 | 11 | — | **nenhum** |
| `webhook_service` | 454 | 2 | 10 | — | `test_webhooks_fail_closed.py` |
| `docker_service` | 422 | 1 | 1 | — | **nenhum** |
| `environment_service` | 418 | 2 | 10 | — | **nenhum** |
| `auth_service` | 394 | 5 | 103 | — | `test_admin_has_no_default_credentials.py`, `test_admin_smoke.py`, `test_auth_and_action_logging.py` |
| `health_service` | 390 | 10 | 9 | — | **nenhum** |
| `git_service` | 370 | 3 | 0 | — | **nenhum** |
| `test_execution_service` | 364 | 1 | 3 | — | **nenhum** |
| `websocket_manager` | 360 | 4 | 2 | — | **nenhum** |
| `job_service` | 347 | 2 | 26 | — | `test_job_executor.py` |
| `audit_service` | 346 | 7 | 14 | — | **nenhum** |
| `log_service` | 331 | 8 | 4 | — | **nenhum** |
| `secret_manager` | 277 | 6 | 10 | — | `test_admin_smoke.py`, `test_secret_key_mismatch_is_not_silent.py` |
| `db_setup_service` | 193 | 1 | 2 | — | **nenhum** |

## Telas `.q` (components/admin)

Fonte de dados: **banco** = datasource `admin` (o mesmo SQLite do FastAPI); **yaml** = arquivo em `quantum_admin/settings/` via `_lib.py`. As duas não se falam.

| Tela | Rota | Auth | Status | Actions | q:python (linhas) | Efeitos do Python | Fonte de dados |
|---|---|---|---|---|---|---|---|
| `agents.q` | `/admin/agents` | **não** | 200 | — | 1 (97) | lê arquivos | — |
| `app/[name].q` | `/admin/app/[name]` | **não** | 200 | updateProject, createProjectConnector, testConnector, detachConnector, saveProjectConfig, runComponentTests, generateComponentTests, createEnvironment, updateEnvironment, deleteEnvironment, startServer, stopServer | 13 (728) | processos, escreve arquivo, lê arquivos, rede | yaml (connectors.yaml), yaml (projects.yaml) |
| `applications.q` | `/admin/applications` | **não** | 200 | createProject, deleteProject, syncProjects | 4 (227) | escreve arquivo, lê arquivos | yaml (connectors.yaml), yaml (projects.yaml) |
| `component/[...path].q` | `/admin/component/[...path]` | **não** | 200 | runTests, generateTests | 3 (361) | processos, escreve arquivo, lê arquivos | — |
| `components.q` | `/admin/components` | **não** | 200 | — | 1 (61) | lê arquivos | — |
| `connectors.q` | `/admin/connectors` | **não** | 200 | createConnector, deleteConnector, testConnector, updateConnector, testAll | 6 (378) | escreve arquivo, lê arquivos, rede | yaml (connectors.yaml) |
| `dashboard.q` | `/admin/dashboard` | **não** | 200 | — | 1 (64) | lê arquivos | — |
| `database.q` | `/admin/database` | **não** | 200 | — | 1 (91) | lê arquivos | — |
| `datasources.q` | `/admin/datasources` | **não** | 200 | — | 0 (0) | — | banco (admin) |
| `features.q` | `/admin/features` | **não** | 200 | — | 1 (61) | lê arquivos | — |
| `index.q` | `/admin` | **não** | 200 | — | 0 (0) | — | — |
| `jobs.q` | `/admin/jobs` | **não** | 200 | — | 1 (90) | — | — |
| `projects.q` | `/admin/projects` | **não** | 200 | — | 0 (0) | — | banco (admin) |
| `settings.q` | `/admin/settings` | **não** | 200 | saveSettings | 2 (195) | escreve arquivo, lê arquivos | — |
| `source.q` | `/admin/source` | **não** | 200 | — | 1 (86) | lê arquivos | — |
| `tests.q` | `/admin/tests` | **não** | 200 | — | 1 (59) | lê arquivos | — |

## Rotas

### API

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/datasources/by-name/{name}` | api | `get_datasource_by_name` (7794, 50) | secret_manager | — | — |

### Admin UI

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/` | página | `serve_admin_ui_root` (362, 3) | — | sim | 200 |
| GET | `/admin` | página | `serve_admin_ui_root` (362, 3) | — | sim | 200 |
| GET | `/admin/` | página | `serve_admin_ui_root` (362, 3) | — | sim | 200 |
| GET | `/admin/cicd` | página | `serve_cicd_page` (451, 2) | — | sim | 200 |
| GET | `/admin/components` | página | `serve_components_page` (481, 2) | — | sim | 200 |
| GET | `/admin/deploy` | página | `serve_deploy_page` (439, 2) | — | sim | 200 |
| GET | `/admin/docker` | página | `serve_docker_page` (433, 2) | — | sim | 200 |
| GET | `/admin/jobs` | página | `serve_jobs_page` (445, 2) | — | sim | 200 |
| GET | `/admin/login` | página | `serve_login_page` (412, 2) | — | — | 200 |
| GET | `/admin/logout` | página | `serve_logout_page` (418, 4) | — | sim | 307 |
| GET | `/admin/projects` | página | `serve_projects_page` (427, 2) | — | sim | 200 |
| GET | `/admin/projects/{project_id:int}` | página | `serve_project_detail` (397, 11) | crud | sim | — |
| GET | `/admin/resources` | página | `serve_resources_page` (469, 2) | — | sim | 200 |
| GET | `/admin/settings` | página | `serve_settings_page` (463, 2) | — | sim | 200 |
| GET | `/admin/tests` | página | `serve_tests_page` (457, 2) | — | sim | 200 |
| GET | `/admin/users` | página | `serve_users_page` (475, 2) | — | sim | 200 |
| GET | `/cicd` | página | `serve_cicd_page` (451, 2) | — | sim | 200 |
| GET | `/components` | página | `serve_components_page` (481, 2) | — | sim | 200 |
| GET | `/deploy` | página | `serve_deploy_page` (439, 2) | — | sim | 200 |
| GET | `/docker` | página | `serve_docker_page` (433, 2) | — | sim | 200 |
| GET | `/jobs` | página | `serve_jobs_page` (445, 2) | — | sim | 200 |
| GET | `/login` | página | `serve_login_page` (412, 2) | — | — | 200 |
| GET | `/logout` | página | `serve_logout_page` (418, 4) | — | sim | 307 |
| GET | `/projects` | página | `serve_projects_page` (427, 2) | — | sim | 200 |
| GET | `/projects/{project_id:int}` | página | `serve_project_detail` (397, 11) | crud | sim | — |
| GET | `/resources` | página | `serve_resources_page` (469, 2) | — | sim | 200 |
| GET | `/settings` | página | `serve_settings_page` (463, 2) | — | sim | 200 |
| GET | `/tests` | página | `serve_tests_page` (457, 2) | — | sim | 200 |
| GET | `/users` | página | `serve_users_page` (475, 2) | — | sim | 200 |

### Audit Log

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/audit-log` | api | `get_project_audit_log` (10986, 30) | audit_service, auth_service, crud | — | — |
| GET | `/api/projects/{project_id}/audit-log-html` | página | `get_project_audit_log_html` (11019, 64) | audit_service, crud | sim | — |
| GET | `/audit-log` | api | `get_global_audit_log` (11086, 19) | audit_service, auth_service | — | 200 |
| GET | `/audit-log/stats` | api | `get_audit_stats` (11108, 9) | audit_service, auth_service | — | 200 |

### Auth

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/auth/change-password` | api | `change_password` (4512, 15) | auth_service | — | — |
| POST | `/auth/login` | api | `login` (4392, 28) | auth_service | sim | — |
| GET | `/auth/me` | api | `get_me` (4423, 7) | auth_service | — | 200 |
| GET | `/auth/users` | api | `list_users` (4433, 4) | auth_service | — | 200 |
| POST | `/auth/users` | api | `create_user` (4440, 40) | auth_service | sim | — |
| DELETE | `/auth/users/{username}` | api | `delete_user` (4483, 26) | auth_service | sim | — |

### CI/CD

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/ci-cd/dashboard` | página | `get_cicd_dashboard_html` (6595, 175) | crud, webhook_service | — | — |
| GET | `/api/webhooks/events-html` | página | `get_webhooks_events_html` (7622, 24) | — | sim | 200 |
| GET | `/projects/{project_id}/badge.svg` | api | `get_build_badge` (6426, 50) | crud, webhook_service | — | — |
| GET | `/projects/{project_id}/pipelines` | api | `list_pipelines` (6363, 36) | crud, webhook_service | — | — |
| POST | `/projects/{project_id}/pipelines/{pipeline_id}/retry` | api | `retry_pipeline` (6544, 48) | auth_service, pipeline_service, webhook_service | sim | — |
| GET | `/projects/{project_id}/pipelines/{pipeline_id}/status` | api | `get_pipeline_status` (6402, 21) | webhook_service | — | — |
| GET | `/projects/{project_id}/tests/badge.svg` | api | `get_tests_badge` (6479, 39) | crud | — | — |

### Cloud Integrations

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/integrations` | api | `list_cloud_integrations` (14045, 7) | — | — | 200 |
| GET | `/integrations/{provider}/config-schema` | api | `get_provider_config_schema` (14073, 15) | — | — | — |
| GET | `/integrations/{provider}/regions` | api | `get_provider_regions` (14055, 15) | — | — | — |
| GET | `/settings/cloud` | página | `get_cloud_integrations_html` (13771, 62) | — | — | sombreada |
| POST | `/settings/cloud` | api | `create_cloud_integration` (13845, 51) | audit_service, secret_manager | — | — |
| POST | `/settings/cloud/test` | api | `test_cloud_connection` (13975, 24) | — | sim | — |
| DELETE | `/settings/cloud/{integration_id}` | api | `delete_cloud_integration` (13947, 25) | audit_service | sim | — |
| GET | `/settings/cloud/{integration_id}` | api | `get_cloud_integration` (13836, 6) | — | — | sombreada |
| PUT | `/settings/cloud/{integration_id}` | api | `update_cloud_integration` (13899, 45) | audit_service, secret_manager | — | sombreada |
| POST | `/settings/cloud/{integration_id}/test` | api | `test_existing_cloud_integration` (14002, 40) | secret_manager | sim | — |

### Components

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/components/validate` | api | `validate_component_file` (9063, 19) | auth_service, component_discovery | — | — |
| GET | `/projects/{project_id}/components` | api | `list_components` (8829, 12) | crud | — | — |
| GET | `/projects/{project_id}/components/dependencies` | api | `get_dependency_graph` (9001, 29) | component_discovery, crud | — | — |
| POST | `/projects/{project_id}/components/discover` | api | `discover_components` (8851, 43) | auth_service, component_discovery, crud | — | — |
| POST | `/projects/{project_id}/components/sync` | api | `sync_components` (8897, 34) | auth_service, component_discovery, crud | sim | — |
| GET | `/projects/{project_id}/components/unused` | api | `get_unused_components` (9033, 27) | component_discovery, crud | — | — |
| GET | `/projects/{project_id}/components/{component_id}/details` | api | `get_component_details` (8934, 64) | component_discovery | — | — |

### Config Generation

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/config/docker-compose` | api | `generate_docker_compose` (12306, 21) | auth_service, config_generator | — | — |
| GET | `/projects/{project_id}/config/download/{config_type}` | api | `download_config` (12379, 46) | auth_service, config_generator, crud | — | — |
| GET | `/projects/{project_id}/config/env` | api | `generate_env_file` (12280, 23) | auth_service, config_generator | — | — |
| GET | `/projects/{project_id}/config/nginx` | api | `generate_nginx_config` (12330, 21) | auth_service, config_generator | — | — |
| GET | `/projects/{project_id}/config/systemd` | api | `generate_systemd_service` (12354, 22) | auth_service, config_generator, crud | — | — |

### Configuration

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/configuration/history` | api | `get_configuration_history` (10959, 20) | crud | — | — |
| GET | `/projects/{project_id}/environment-variables` | api | `list_environment_variables` (10725, 39) | crud, secret_manager | sim | — |
| POST | `/projects/{project_id}/environment-variables` | api | `create_environment_variable` (10767, 70) | crud, secret_manager | — | — |
| DELETE | `/projects/{project_id}/environment-variables/{key}` | api | `delete_environment_variable` (10920, 36) | crud | — | — |
| PUT | `/projects/{project_id}/environment-variables/{key}` | api | `update_environment_variable` (10840, 77) | crud, secret_manager | — | — |

### Connectors

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/settings/connectors` | api | `list_connectors` (4568, 81) | connector_service | sim | 200 |
| POST | `/settings/connectors` | api | `create_connector` (4666, 12) | connector_service | — | — |
| GET | `/settings/connectors/id/{connector_id}` | api | `get_connector` (4681, 12) | connector_service | sim | — |
| GET | `/settings/connectors/providers` | api | `get_connector_providers` (4652, 11) | connector_service | — | 200 |
| POST | `/settings/connectors/test` | api | `test_connector_data` (4750, 6) | connector_service | sim | — |
| GET | `/settings/connectors/type/{connector_type}` | api | `list_connectors_by_type` (4789, 3) | — | — | — |
| GET | `/settings/connectors/type/{connector_type}/default` | api | `get_default_connector` (4795, 9) | connector_service | — | — |
| DELETE | `/settings/connectors/{connector_id}` | api | `delete_connector` (4711, 12) | connector_service | sim | — |
| PUT | `/settings/connectors/{connector_id}` | api | `update_connector` (4696, 12) | connector_service | — | — |
| POST | `/settings/connectors/{connector_id}/default` | api | `set_connector_default` (4726, 12) | connector_service | sim | — |
| POST | `/settings/connectors/{connector_id}/docker/start` | api | `start_connector_docker` (4759, 12) | connector_service | — | — |
| POST | `/settings/connectors/{connector_id}/docker/stop` | api | `stop_connector_docker` (4774, 12) | connector_service | — | — |
| POST | `/settings/connectors/{connector_id}/test` | api | `test_connector` (4741, 6) | connector_service | sim | — |

### Dashboard

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/dashboard` | página | `get_main_dashboard_html` (12807, 162) | crud, job_service, webhook_service | — | 200 |
| GET | `/api/docker/dashboard` | página | `get_docker_dashboard_html` (13041, 160) | — | sim | 200 |
| GET | `/api/projects/list-html` | página | `get_projects_list_html` (12972, 66) | crud | — | 200 |
| GET | `/api/projects/{project_id}/components/dashboard` | página | `get_components_dashboard_html` (13543, 221) | crud | sim | — |
| GET | `/api/settings/dashboard` | página | `get_settings_dashboard_html` (13357, 139) | auth_service, settings_service | — | 200 |
| GET | `/api/users/dashboard` | página | `get_users_dashboard_html` (13204, 150) | auth_service | — | 200 |
| GET | `/dashboard/activity` | página | `get_dashboard_activity_html` (11674, 43) | audit_service | sim | 200 |
| GET | `/dashboard/activity-legacy` | api | `get_dashboard_activity_legacy` (5122, 43) | audit_service, auth_service | — | 200 |
| GET | `/dashboard/stats` | api | `get_dashboard_stats` (4922, 197) | auth_service, crud, job_service | sim | 200 |

### Datasources

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| DELETE | `/datasources/{datasource_id}` | api | `delete_datasource` (8793, 29) | crud | — | — |
| PUT | `/datasources/{datasource_id}` | api | `update_datasource` (8746, 44) | auth_service, crud, secret_manager | — | — |
| GET | `/projects/{project_id}/datasources` | api | `list_datasources` (7777, 12) | crud | — | — |
| POST | `/projects/{project_id}/datasources` | api | `create_datasource` (8639, 100) | crud, secret_manager | — | — |

### Deploy

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/environments/{env_id}/rollback-html` | página | `get_rollback_html` (5773, 50) | — | — | — |
| POST | `/deploy` | api | `create_deployment` (5500, 57) | auth_service, crud, deploy_service | — | — |
| POST | `/deploy/{deploy_id}/cancel` | api | `cancel_deployment` (5595, 22) | auth_service, deploy_service | — | — |
| POST | `/deploy/{deploy_id}/rollback` | api | `rollback_deployment` (5620, 24) | auth_service, deploy_service | — | — |
| GET | `/deploy/{deploy_id}/status` | api | `get_deployment_status` (5560, 32) | auth_service, deploy_service | — | — |
| GET | `/deployments` | api | `list_deployments` (5483, 14) | auth_service, deploy_service | — | 200 |
| POST | `/projects/{project_id}/environments/{env_id}/rollback` | api | `rollback_to_version` (5668, 102) | audit_service, auth_service, crud, deploy_service | sim | — |

### Deploy Pipeline

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/deploy/pipeline/{deployment_id}` | api | `get_pipeline_status` (6098, 12) | pipeline_service | — | — |
| POST | `/deploy/pipeline/{deployment_id}/cancel` | api | `cancel_pipeline` (6124, 12) | auth_service, pipeline_service | — | — |
| GET | `/deploy/pipeline/{deployment_id}/logs` | api | `get_pipeline_logs` (6113, 8) | websocket_manager | — | — |
| POST | `/deploy/pipeline/{deployment_id}/promote` | api | `promote_deployment` (6165, 23) | auth_service, pipeline_service | — | — |
| POST | `/deploy/pipeline/{deployment_id}/rollback` | api | `rollback_pipeline` (6139, 23) | auth_service, pipeline_service | — | — |
| POST | `/deploy/start` | api | `start_pipeline` (6060, 35) | auth_service, pipeline_service | sim | — |

### Deploy Versions

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/environments/{env_id}/versions` | api | `list_environment_versions` (5647, 18) | auth_service | — | — |
| GET | `/projects/{project_id}/versions` | api | `list_deployment_versions` (6195, 19) | — | — | — |
| GET | `/projects/{project_id}/versions/{version_id}` | api | `get_deployment_version` (6217, 20) | — | — | — |

### Docker

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/datasources/{datasource_id}/logs` | api | `get_datasource_container_logs` (9268, 27) | crud | — | — |
| GET | `/datasources/{datasource_id}/logs` | api | `get_datasource_container_logs` (9429, 44) | crud | — | — |
| POST | `/datasources/{datasource_id}/restart` | api | `restart_datasource_container` (9221, 44) | crud | — | — |
| POST | `/datasources/{datasource_id}/setup` | api | `setup_datasource` (9580, 61) | crud, db_setup_service | — | — |
| POST | `/datasources/{datasource_id}/start` | api | `start_datasource_container` (9089, 82) | crud, db_setup_service | — | — |
| GET | `/datasources/{datasource_id}/status` | api | `get_datasource_container_status` (9386, 40) | crud | — | — |
| POST | `/datasources/{datasource_id}/stop` | api | `stop_datasource_container` (9174, 44) | crud | — | — |
| POST | `/datasources/{datasource_id}/test` | api | `test_datasource_connection` (9298, 85) | crud, secret_manager | — | — |
| POST | `/docker/connect` | api | `docker_connect` (4310, 29) | docker_service | sim | — |
| GET | `/docker/containers` | api | `list_all_containers` (9476, 101) | — | sim | 503 |
| DELETE | `/docker/containers/{container_id}` | api | `remove_docker_container` (5457, 19) | — | — | — |
| GET | `/docker/containers/{container_id}/logs` | api | `get_container_logs` (5435, 19) | — | — | — |
| POST | `/docker/containers/{container_id}/restart` | api | `restart_container` (5413, 19) | — | — | — |
| POST | `/docker/containers/{container_id}/start` | api | `start_container` (5369, 19) | — | sim | — |
| POST | `/docker/containers/{container_id}/stop` | api | `stop_container` (5391, 19) | — | sim | — |
| GET | `/docker/images` | api | `list_docker_images` (5282, 26) | — | sim | 503 |
| GET | `/docker/info` | api | `get_docker_info` (5207, 72) | — | sim | 200 |
| GET | `/docker/networks` | api | `list_docker_networks` (5339, 27) | — | sim | 503 |
| GET | `/docker/status` | api | `docker_status` (4255, 52) | — | sim | 200 |
| GET | `/docker/volumes` | api | `list_docker_volumes` (5311, 25) | — | sim | 503 |

### Endpoints

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/endpoints` | api | `list_endpoints` (9648, 12) | crud | — | — |

### Environments

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/environments` | api | `list_environments` (5842, 9) | environment_service | — | — |
| POST | `/projects/{project_id}/environments` | api | `create_environment` (5854, 13) | auth_service, environment_service | — | — |
| POST | `/projects/{project_id}/environments/defaults` | api | `create_default_environments` (6044, 9) | auth_service, environment_service | — | — |
| DELETE | `/projects/{project_id}/environments/{env_id}` | api | `delete_environment` (5900, 11) | auth_service, environment_service | — | — |
| GET | `/projects/{project_id}/environments/{env_id}` | api | `get_environment` (5870, 11) | environment_service | — | — |
| PUT | `/projects/{project_id}/environments/{env_id}` | api | `update_environment` (5884, 13) | auth_service, environment_service | — | — |
| POST | `/projects/{project_id}/environments/{env_id}/approve` | api | `approve_environment` (6030, 11) | auth_service, environment_service | — | — |
| POST | `/projects/{project_id}/environments/{env_id}/launch` | api | `launch_app_in_environment` (5926, 101) | crud, environment_service, *subprocess* | — | — |
| POST | `/projects/{project_id}/environments/{env_id}/test` | api | `test_environment_connection` (5914, 9) | environment_service | — | — |

### Health

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/health` | api | `get_project_health` (11490, 20) | auth_service, crud, health_service | — | — |
| POST | `/api/projects/{project_id}/health-checks` | api | `create_health_check_endpoint` (11564, 30) | auth_service, crud, health_service | — | — |
| POST | `/api/projects/{project_id}/health-checks/run` | api | `run_project_health_checks` (11597, 14) | auth_service, crud, health_service | — | — |
| GET | `/api/projects/{project_id}/health-html` | página | `get_project_health_html` (11513, 48) | health_service | — | — |
| GET | `/api/projects/{project_id}/incidents` | api | `get_project_incidents` (11614, 16) | auth_service, crud, health_service | — | — |
| GET | `/health` | api | `health_check` (4245, 7) | — | — | 200 |
| GET | `/health/database` | api | `health_database` (5168, 32) | — | sim | 200 |
| GET | `/health/system` | api | `get_system_health` (11456, 6) | health_service | — | 200 |
| GET | `/health/system-html` | página | `get_system_health_html` (11465, 22) | health_service | — | 200 |
| POST | `/incidents/{incident_id}/acknowledge` | api | `acknowledge_incident_endpoint` (11655, 16) | auth_service, health_service | — | — |
| POST | `/incidents/{incident_id}/resolve` | api | `resolve_incident_endpoint` (11633, 19) | auth_service, health_service | — | — |

### Jobs

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/jobs-list` | página | `get_jobs_list_html` (7483, 41) | job_service | sim | 200 |
| GET | `/api/jobs/dashboard` | página | `get_jobs_dashboard_html` (7020, 279) | job_service | sim | 200 |
| GET | `/api/jobs/overview-html` | página | `get_jobs_overview_html` (7527, 23) | job_service | sim | 200 |
| GET | `/api/queues-list` | página | `get_queues_list_html` (7595, 24) | job_service | sim | 200 |
| GET | `/api/schedules-list` | página | `get_schedules_list_html` (7553, 18) | job_service | sim | 200 |
| GET | `/api/threads-list` | página | `get_threads_list_html` (7574, 18) | job_service | sim | 200 |
| GET | `/jobs` | api | `list_all_jobs` (6783, 12) | auth_service, job_service | — | sombreada |
| POST | `/jobs/dispatch` | api | `dispatch_job` (6844, 20) | auth_service, job_service | — | — |
| GET | `/jobs/overview` | api | `get_jobs_overview` (6798, 4) | auth_service, job_service | — | 200 |
| GET | `/jobs/{job_id}` | api | `get_job_details` (6805, 10) | auth_service, job_service | — | — |
| POST | `/jobs/{job_id}/cancel` | api | `cancel_job` (6818, 10) | auth_service, job_service | sim | — |
| POST | `/jobs/{job_id}/retry` | api | `retry_job` (6831, 10) | auth_service, job_service | sim | — |
| GET | `/queues` | api | `list_queues` (6987, 4) | auth_service, job_service | — | 200 |
| POST | `/queues/{queue}/purge` | api | `purge_queue` (7004, 9) | auth_service, job_service | sim | — |
| GET | `/queues/{queue}/stats` | api | `get_queue_stats` (6994, 7) | auth_service, job_service | — | — |
| GET | `/schedules` | api | `list_schedules` (6871, 4) | auth_service, job_service | — | 200 |
| DELETE | `/schedules/{name}` | api | `remove_schedule` (6930, 10) | auth_service, job_service | — | — |
| GET | `/schedules/{name}` | api | `get_schedule_details` (6878, 10) | auth_service, job_service | — | — |
| POST | `/schedules/{name}/pause` | api | `pause_schedule` (6891, 10) | auth_service, job_service | sim | — |
| POST | `/schedules/{name}/resume` | api | `resume_schedule` (6904, 10) | auth_service, job_service | sim | — |
| POST | `/schedules/{name}/run` | api | `run_schedule_now` (6917, 10) | auth_service, job_service | sim | — |
| GET | `/threads` | api | `list_threads` (6947, 7) | auth_service, job_service | — | 200 |
| GET | `/threads/{name}` | api | `get_thread_details` (6957, 10) | auth_service, job_service | — | — |
| POST | `/threads/{name}/terminate` | api | `terminate_thread` (6970, 10) | auth_service, job_service | — | — |

### Logs

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/logs` | api | `get_project_logs` (11124, 59) | auth_service, crud, log_service | — | — |
| GET | `/api/projects/{project_id}/logs-html` | página | `get_project_logs_html` (11186, 99) | crud, log_service | sim | — |
| GET | `/api/projects/{project_id}/logs/export` | api | `export_project_logs` (11288, 53) | crud, log_service | — | — |
| POST | `/api/projects/{project_id}/logs/generate-sample` | api | `generate_sample_logs` (11344, 87) | crud | — | — |
| GET | `/api/projects/{project_id}/logs/stats` | api | `get_project_log_stats` (11434, 15) | crud, log_service | sim | — |

### Project Detail

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/connectors-html` | api | `get_project_connectors_html` (8239, 88) | — | sim | — |
| GET | `/api/projects/{project_id}/datasources-html` | api | `get_project_datasources_html` (8090, 146) | crud | sim | — |
| GET | `/api/projects/{project_id}/environments-html` | api | `get_project_environments_html` (8330, 106) | environment_service | sim | — |
| GET | `/api/projects/{project_id}/general` | api | `get_project_general_html` (7887, 58) | crud | sim | — |
| GET | `/api/projects/{project_id}/header` | api | `get_project_header_html` (7851, 33) | crud | sim | — |
| GET | `/api/projects/{project_id}/paths-html` | api | `get_project_paths_html` (8439, 192) | crud, settings_service | sim | — |
| GET | `/api/projects/{project_id}/source-html` | página | `get_project_source_html` (7948, 139) | crud | sim | — |

### Project Settings

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/projects/{project_id}/settings` | api | `get_project_settings` (4848, 16) | auth_service, crud, settings_service | — | — |
| PUT | `/projects/{project_id}/settings` | api | `update_project_settings` (4867, 23) | auth_service, crud, settings_service | sim | — |

### Projects

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects` | api | `get_projects_json` (7476, 4) | crud | sim | 200 |
| GET | `/api/projects-grid` | página | `get_projects_grid` (7420, 53) | crud | sim | 200 |
| GET | `/projects` | api | `list_projects` (7352, 65) | crud | — | sombreada |
| POST | `/projects` | api | `create_project` (7654, 33) | audit_service, crud | — | — |
| DELETE | `/projects/{project_id}` | api | `delete_project` (7743, 27) | audit_service, crud | sim | — |
| GET | `/projects/{project_id}` | api | `get_project` (7690, 9) | crud | — | sombreada |
| PUT | `/projects/{project_id}` | api | `update_project` (7702, 38) | audit_service, crud | sim | — |

### Resources

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/resources/containers` | api | `get_docker_containers_resource` (11859, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/overview` | api | `get_resources_overview` (11725, 19) | auth_service, resource_manager | — | 200 |
| GET | `/resources/overview-html` | página | `get_resources_overview_html` (11747, 79) | resource_manager | sim | 200 |
| GET | `/resources/ports` | api | `list_port_allocations` (11892, 17) | auth_service, resource_manager | — | 200 |
| POST | `/resources/ports/allocate` | api | `allocate_port` (11912, 32) | auth_service, resource_manager | — | — |
| GET | `/resources/ports/check/{port}` | api | `check_port_availability` (11966, 9) | resource_manager | — | — |
| GET | `/resources/ports/discovered` | api | `get_discovered_ports` (11839, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/ports/ranges` | api | `list_port_ranges` (11978, 8) | auth_service, resource_manager | — | 200 |
| POST | `/resources/ports/ranges` | api | `create_port_range` (11989, 21) | auth_service, resource_manager | — | — |
| POST | `/resources/ports/release` | api | `release_port` (11947, 16) | auth_service, resource_manager | sim | — |
| POST | `/resources/ports/reserve` | api | `reserve_port` (12013, 17) | auth_service, resource_manager | — | — |
| GET | `/resources/processes` | api | `get_quantum_processes` (11849, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/scan` | api | `scan_resources` (11829, 7) | auth_service, resource_manager | — | 200 |
| GET | `/resources/secrets` | api | `list_secrets` (12037, 33) | auth_service, resource_manager | — | 200 |
| POST | `/resources/secrets` | api | `create_or_update_secret` (12073, 33) | auth_service, resource_manager | — | — |
| DELETE | `/resources/secrets/{secret_id}` | api | `delete_secret` (12109, 15) | auth_service, resource_manager | sim | — |
| POST | `/resources/secrets/{secret_id}/rotate` | api | `rotate_secret` (12127, 16) | auth_service, resource_manager | sim | — |
| GET | `/resources/services` | api | `list_services` (12150, 21) | auth_service, resource_manager | — | 200 |
| POST | `/resources/services` | api | `register_service` (12174, 31) | auth_service, resource_manager | — | — |
| GET | `/resources/services/discover/{service_type}` | api | `discover_services` (12253, 14) | resource_manager | — | — |
| POST | `/resources/services/health-check` | api | `run_health_checks` (12237, 13) | auth_service, resource_manager | sim | — |
| DELETE | `/resources/services/{service_id}` | api | `unregister_service` (12208, 15) | auth_service, resource_manager | sim | — |
| GET | `/resources/services/{service_id}/health` | api | `check_service_health` (12226, 8) | resource_manager | sim | — |
| POST | `/resources/sync` | api | `sync_discovered_resources` (11879, 10) | auth_service, resource_manager | sim | — |
| GET | `/resources/system` | api | `get_system_resources` (11869, 7) | auth_service, resource_manager | — | 200 |

### Resources UI

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/resources/containers-html` | página | `get_discovered_containers_html` (12755, 45) | resource_manager | sim | 200 |
| GET | `/api/resources/discovered-ports-html` | página | `get_discovered_ports_html` (12712, 40) | resource_manager | sim | 200 |
| GET | `/api/resources/ports-html` | página | `get_ports_html` (12468, 75) | resource_manager | sim | 200 |
| GET | `/api/resources/secrets-html` | página | `get_secrets_html` (12546, 83) | resource_manager | sim | 200 |
| GET | `/api/resources/services-html` | página | `get_services_html` (12632, 77) | resource_manager | sim | 200 |
| GET | `/api/resources/stats` | página | `get_resources_stats_html` (12432, 33) | resource_manager | — | 200 |

### Settings

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/api/settings/docker` | api | `save_docker_settings` (13499, 41) | auth_service, settings_service | sim | — |
| GET | `/settings` | api | `get_settings` (4534, 4) | auth_service, settings_service | — | sombreada |
| PUT | `/settings` | api | `update_settings` (4541, 14) | auth_service, settings_service | — | — |
| GET | `/settings/export` | api | `export_settings` (4893, 4) | auth_service, settings_service | — | sombreada |
| POST | `/settings/import` | api | `import_settings` (4900, 15) | auth_service, settings_service | — | — |
| GET | `/settings/{path:path}` | api | `get_setting` (4807, 14) | auth_service, settings_service | sim | — |
| PUT | `/settings/{path:path}` | api | `set_setting` (4824, 17) | auth_service, settings_service | — | — |

### Templates

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/create-project-wizard` | página | `get_create_project_wizard` (14219, 192) | — | sim | 200 |
| POST | `/projects/from-template` | api | `create_project_from_template` (14139, 77) | audit_service, crud, template_service | sim | — |
| GET | `/templates` | api | `list_templates` (14095, 5) | template_service | — | 200 |
| GET | `/templates-html` | página | `get_templates_html` (14113, 23) | template_service | sim | 200 |
| GET | `/templates/{template_id}` | api | `get_template` (14103, 7) | template_service | sim | — |

### Test Dashboard

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/api/projects/{project_id}/tests/dashboard` | página | `get_test_dashboard_html` (10446, 149) | crud | sim | — |
| GET | `/api/projects/{project_id}/tests/runs/{run_id}/details` | página | `get_test_run_details_html` (10598, 76) | crud | sim | — |
| GET | `/api/projects/{project_id}/tests/summary` | api | `get_test_summary` (10677, 41) | crud | — | — |

### Test Generator

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/api/projects/{project_id}/components/generate-missing-tests` | api | `generate_missing_tests` (10178, 63) | auth_service, crud, test_generator | sim | — |
| POST | `/api/projects/{project_id}/components/sync-tests` | api | `sync_component_tests` (10154, 21) | auth_service, component_discovery | sim | — |
| GET | `/api/projects/{project_id}/components/{component_id}/tests` | api | `get_component_tests` (10356, 33) | — | — | — |
| POST | `/api/projects/{project_id}/components/{component_id}/tests/run` | api | `run_component_tests` (9995, 156) | auth_service, crud, *subprocess* | sim | — |
| POST | `/api/projects/{project_id}/tests/run-all` | api | `run_all_tests` (10244, 109) | auth_service, crud, *subprocess* | sim | — |
| POST | `/projects/{project_id}/components/{component_id}/tests/generate` | api | `generate_tests_for_component` (9946, 46) | auth_service, test_generator | sim | — |
| POST | `/projects/{project_id}/tests/conftest` | api | `generate_conftest` (10418, 21) | auth_service, test_generator | — | — |
| GET | `/projects/{project_id}/tests/coverage-estimate` | api | `get_test_coverage_estimate` (10392, 23) | crud, test_generator | — | — |
| POST | `/projects/{project_id}/tests/generate` | api | `generate_tests_for_project` (9892, 51) | auth_service, crud, test_generator | — | — |

### Tests

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| POST | `/projects/{project_id}/tests/run` | api | `run_tests` (9672, 47) | crud, test_execution_service | sim | — |
| GET | `/projects/{project_id}/tests/runs` | api | `list_test_runs` (9722, 22) | crud | — | — |
| DELETE | `/projects/{project_id}/tests/runs/{run_id}` | api | `delete_test_run` (9851, 27) | crud | — | — |
| GET | `/projects/{project_id}/tests/runs/{run_id}` | api | `get_test_run` (9747, 28) | crud | — | — |
| POST | `/projects/{project_id}/tests/runs/{run_id}/cancel` | api | `cancel_test_run` (9815, 33) | crud, test_execution_service | — | — |
| GET | `/projects/{project_id}/tests/runs/{run_id}/status` | api | `get_test_run_status` (9778, 34) | crud, test_execution_service | — | — |

### Webhooks

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| GET | `/webhooks/events` | api | `list_webhook_events` (6332, 10) | auth_service, webhook_service | — | 200 |
| GET | `/webhooks/events/{event_id}` | api | `get_webhook_event` (6345, 11) | auth_service, webhook_service | — | — |
| POST | `/webhooks/github` | api | `github_webhook` (6244, 43) | webhook_service | — | — |
| POST | `/webhooks/gitlab` | api | `gitlab_webhook` (6290, 39) | webhook_service | — | — |

### —

| Verbo | Caminho | Tipo | Handler (linha, linhas) | Usa | UI | Status |
|---|---|---|---|---|---|---|
| WEBSOCKET | `/ws/deploy/{deployment_id}/logs` | websocket | `websocket_deploy_logs` (7309, 36) | websocket_manager | — | — |
