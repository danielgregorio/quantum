"""
CRUD operations for Quantum Admin
"""
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime

from . import models


# ============================================================================
# PROJECT OPERATIONS
# ============================================================================

def get_projects(db: Session, skip: int = 0, limit: int = 100) -> List[models.Project]:
    """Get all projects with pagination"""
    return db.query(models.Project).offset(skip).limit(limit).all()


def get_project(db: Session, project_id: int) -> Optional[models.Project]:
    """Get a single project by ID"""
    return db.query(models.Project).filter(models.Project.id == project_id).first()


def get_project_by_name(db: Session, name: str) -> Optional[models.Project]:
    """Get a project by name"""
    return db.query(models.Project).filter(models.Project.name == name).first()


def create_project(db: Session, name: str, description: str = "") -> models.Project:
    """Create a new project"""
    project = models.Project(name=name, description=description)
    db.add(project)
    try:
        db.commit()
        db.refresh(project)
        return project
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Project with name '{name}' already exists")


def update_project(
    db: Session,
    project_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    status: Optional[str] = None,
    source_path: Optional[str] = None,
    git_url: Optional[str] = None,
    git_branch: Optional[str] = None
) -> Optional[models.Project]:
    """Update an existing project"""
    project = get_project(db, project_id)
    if not project:
        return None

    if name is not None:
        project.name = name
    if description is not None:
        project.description = description
    if status is not None:
        project.status = status
    if source_path is not None:
        project.source_path = source_path
    if git_url is not None:
        project.git_url = git_url
    if git_branch is not None:
        project.git_branch = git_branch

    project.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


# O que fazer com cada tabela que aponta para `projects.id` quando o projeto
# e apagado.
#
# `Project` declarava `cascade="all, delete-orphan"` para TRES relacoes —
# datasources, components, endpoints — e existem DEZENOVE tabelas com uma FK
# para projects.id. As outras dezesseis nao tinham relacao nenhuma, entao
# `db.delete(project)` nao as tocava:
#
#   * as oito com project_id NOT NULL (test_runs, environment_variables,
#     configuration_history, deployment_targets, deployments, environments,
#     deployment_versions, application_logs) violavam a FK. Com o SQLite
#     enforcando chaves estrangeiras isso e IntegrityError — HTTP 500 ao
#     apagar um projeto que ja foi usado para qualquer coisa. Sem enforcar
#     (o padrao do SQLite), as linhas ficavam apontando para um projeto que
#     nao existe mais.
#   * as oito com project_id NULL-avel ficavam orfas do mesmo jeito, e
#     `secrets` e `port_allocations` continuavam segurando recursos de um
#     projeto que ninguem consegue mais ver.
#
# 'delete' = a linha pertence ao projeto e vai com ele.
# 'null'   = a linha e historico ou e compartilhavel; sobrevive sem dono.
_PROJECT_CHILD_POLICY = {
    # NOT NULL: nao podem sobreviver
    'Datasource': ('project_id', 'delete'),
    'Component': ('project_id', 'delete'),
    'Endpoint': ('project_id', 'delete'),
    'TestRun': ('project_id', 'delete'),
    'EnvironmentVariable': ('project_id', 'delete'),
    'ConfigurationHistory': ('project_id', 'delete'),
    'DeploymentTarget': ('project_id', 'delete'),
    'Deployment': ('project_id', 'delete'),
    'Environment': ('project_id', 'delete'),
    'DeploymentVersion': ('project_id', 'delete'),
    'ApplicationLog': ('project_id', 'delete'),
    # NULL-aveis que seguram recurso ou segredo: tambem vao.
    # Um secret com project_id NULL viraria um secret GLOBAL, visivel para
    # os outros projetos; uma porta alocada a ninguem nunca mais e liberada.
    'Secret': ('project_id', 'delete'),
    'PortAllocation': ('project_id', 'delete'),
    'ServiceRegistry': ('project_id', 'delete'),
    # NULL-aveis que sao historico: ficam, sem dono. Apagar o log de
    # auditoria de um projeto ao apagar o projeto e apagar exatamente o
    # registro de que ele foi apagado.
    'AuditLog': ('project_id', 'null'),
    'WebhookEvent': ('project_id', 'null'),
    'HealthCheck': ('project_id', 'null'),
    'Incident': ('project_id', 'null'),
    # Connector e explicitamente compartilhavel (tem `shared_with`).
    'Connector': ('owner_project_id', 'null'),
}


def _project_child_tables():
    """Toda classe mapeada com uma FK para projects.id, com sua politica.

    Descoberto por introspecao, e nao a partir de uma lista escrita a mao,
    porque a lista escrita a mao foi exatamente o que ficou para tras: quem
    adicionar uma tabela nova com project_id nao precisa lembrar de mexer
    aqui — vai receber um erro dizendo que falta decidir.
    """
    encontradas = []
    for classe in models.Base.registry.mappers:
        modelo = classe.class_
        for coluna in modelo.__table__.columns:
            alvos = {fk.target_fullname for fk in coluna.foreign_keys}
            if 'projects.id' not in alvos:
                continue
            politica = _PROJECT_CHILD_POLICY.get(modelo.__name__)
            if politica is None or politica[0] != coluna.name:
                raise RuntimeError(
                    f"{modelo.__name__}.{coluna.name} aponta para "
                    f"projects.id e nao tem politica de delecao em "
                    f"_PROJECT_CHILD_POLICY (crud.py). Decida se a linha "
                    f"vai junto ('delete') ou fica sem dono ('null')."
                )
            encontradas.append((modelo, coluna.name, politica[1]))

    # Ordem: filho antes de pai. As tabelas do projeto tambem apontam umas
    # para as outras (`deployments.target_id` -> `deployment_targets.id`),
    # entao apagar em ordem arbitraria dava "FOREIGN KEY constraint failed"
    # com as FKs enforcadas. `sorted_tables` vem em ordem de dependencia
    # (pai primeiro); invertida, e a ordem de delecao.
    ordem = {tabela.name: i for i, tabela in enumerate(
        models.Base.metadata.sorted_tables)}
    encontradas.sort(key=lambda t: -ordem.get(t[0].__tablename__, 0))
    return encontradas


def delete_project(db: Session, project_id: int) -> bool:
    """Delete a project and all its related data"""
    project = get_project(db, project_id)
    if not project:
        return False

    for modelo, coluna, acao in _project_child_tables():
        filtro = getattr(modelo, coluna) == project_id
        if acao == 'delete':
            db.query(modelo).filter(filtro).delete(synchronize_session=False)
        else:
            db.query(modelo).filter(filtro).update(
                {coluna: None}, synchronize_session=False)

    db.delete(project)
    db.commit()
    return True


# ============================================================================
# DATASOURCE OPERATIONS
# ============================================================================

def get_datasources(db: Session, project_id: int) -> List[models.Datasource]:
    """Get all datasources for a project"""
    return db.query(models.Datasource).filter(
        models.Datasource.project_id == project_id
    ).all()


def get_datasource(db: Session, datasource_id: int) -> Optional[models.Datasource]:
    """Get a single datasource by ID"""
    return db.query(models.Datasource).filter(
        models.Datasource.id == datasource_id
    ).first()


def create_datasource(
    db: Session,
    project_id: int,
    name: str,
    type: str,
    connection_type: str,
    **kwargs
) -> models.Datasource:
    """Create a new datasource"""
    datasource = models.Datasource(
        project_id=project_id,
        name=name,
        type=type,
        connection_type=connection_type,
        **kwargs
    )
    db.add(datasource)
    try:
        db.commit()
        db.refresh(datasource)
        return datasource
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Datasource with name '{name}' already exists in this project")


def update_datasource(
    db: Session,
    datasource_id: int,
    **kwargs
) -> Optional[models.Datasource]:
    """Update a datasource"""
    datasource = get_datasource(db, datasource_id)
    if not datasource:
        return None

    for key, value in kwargs.items():
        if hasattr(datasource, key) and value is not None:
            setattr(datasource, key, value)

    datasource.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(datasource)
    return datasource


def delete_datasource(db: Session, datasource_id: int) -> bool:
    """Delete a datasource"""
    datasource = get_datasource(db, datasource_id)
    if not datasource:
        return False

    db.delete(datasource)
    db.commit()
    return True


# ============================================================================
# COMPONENT OPERATIONS
# ============================================================================

def get_components(db: Session, project_id: int) -> List[models.Component]:
    """Get all components for a project"""
    return db.query(models.Component).filter(
        models.Component.project_id == project_id
    ).all()


def get_component(db: Session, component_id: int) -> Optional[models.Component]:
    """Get a single component by ID"""
    return db.query(models.Component).filter(
        models.Component.id == component_id
    ).first()


def create_or_update_component(
    db: Session,
    project_id: int,
    name: str,
    file_path: str,
    status: str = "unknown",
    error_message: Optional[str] = None
) -> models.Component:
    """Create or update a component (upsert)"""
    component = db.query(models.Component).filter(
        models.Component.project_id == project_id,
        models.Component.name == name
    ).first()

    if component:
        # Update existing
        component.file_path = file_path
        component.status = status
        component.error_message = error_message
        component.last_compiled = datetime.utcnow()
    else:
        # Create new
        component = models.Component(
            project_id=project_id,
            name=name,
            file_path=file_path,
            status=status,
            error_message=error_message,
            last_compiled=datetime.utcnow()
        )
        db.add(component)

    db.commit()
    db.refresh(component)
    return component


# ============================================================================
# ENDPOINT OPERATIONS
# ============================================================================

def get_endpoints(db: Session, project_id: int) -> List[models.Endpoint]:
    """Get all endpoints for a project"""
    return db.query(models.Endpoint).filter(
        models.Endpoint.project_id == project_id
    ).all()


def create_or_update_endpoint(
    db: Session,
    project_id: int,
    method: str,
    path: str,
    function_name: str,
    component_id: Optional[int] = None,
    description: Optional[str] = None
) -> models.Endpoint:
    """Create or update an endpoint (upsert)"""
    endpoint = db.query(models.Endpoint).filter(
        models.Endpoint.project_id == project_id,
        models.Endpoint.method == method,
        models.Endpoint.path == path
    ).first()

    if endpoint:
        # Update existing
        endpoint.function_name = function_name
        endpoint.component_id = component_id
        endpoint.description = description
    else:
        # Create new
        endpoint = models.Endpoint(
            project_id=project_id,
            method=method,
            path=path,
            function_name=function_name,
            component_id=component_id,
            description=description
        )
        db.add(endpoint)

    db.commit()
    db.refresh(endpoint)
    return endpoint


# ============================================================================
# TEST RUN OPERATIONS
# ============================================================================

def get_test_runs(
    db: Session,
    project_id: int,
    skip: int = 0,
    limit: int = 100
) -> List[models.TestRun]:
    """Get all test runs for a project with pagination"""
    return db.query(models.TestRun).filter(
        models.TestRun.project_id == project_id
    ).order_by(models.TestRun.started_at.desc()).offset(skip).limit(limit).all()


def get_test_run(db: Session, test_run_id: int) -> Optional[models.TestRun]:
    """Get a single test run by ID with all test results"""
    return db.query(models.TestRun).filter(
        models.TestRun.id == test_run_id
    ).first()


def get_latest_test_run(db: Session, project_id: int) -> Optional[models.TestRun]:
    """Get the latest test run for a project"""
    return db.query(models.TestRun).filter(
        models.TestRun.project_id == project_id
    ).order_by(models.TestRun.started_at.desc()).first()


def delete_test_run(db: Session, test_run_id: int) -> bool:
    """Delete a test run and all its results"""
    test_run = get_test_run(db, test_run_id)
    if not test_run:
        return False

    db.delete(test_run)
    db.commit()
    return True


# ============================================================================
# TEST RESULT OPERATIONS
# ============================================================================

def get_test_results(db: Session, test_run_id: int) -> List[models.TestResult]:
    """Get all test results for a test run"""
    return db.query(models.TestResult).filter(
        models.TestResult.test_run_id == test_run_id
    ).all()


def get_failed_test_results(db: Session, test_run_id: int) -> List[models.TestResult]:
    """Get only failed test results for a test run"""
    return db.query(models.TestResult).filter(
        models.TestResult.test_run_id == test_run_id,
        models.TestResult.status == 'failed'
    ).all()


# ============================================================================
# ENVIRONMENT VARIABLE OPERATIONS
# ============================================================================

def get_environment_variables(
    db: Session,
    project_id: int
) -> List[models.EnvironmentVariable]:
    """Get all environment variables for a project"""
    return db.query(models.EnvironmentVariable).filter(
        models.EnvironmentVariable.project_id == project_id
    ).order_by(models.EnvironmentVariable.key).all()


def get_environment_variable(
    db: Session,
    project_id: int,
    key: str
) -> Optional[models.EnvironmentVariable]:
    """Get a specific environment variable by key"""
    return db.query(models.EnvironmentVariable).filter(
        models.EnvironmentVariable.project_id == project_id,
        models.EnvironmentVariable.key == key
    ).first()


def create_environment_variable(
    db: Session,
    project_id: int,
    key: str,
    value_encrypted: str,
    description: Optional[str] = None,
    is_secret: bool = False
) -> models.EnvironmentVariable:
    """Create a new environment variable"""
    env_var = models.EnvironmentVariable(
        project_id=project_id,
        key=key,
        value_encrypted=value_encrypted,
        description=description,
        is_secret=is_secret
    )
    db.add(env_var)
    try:
        db.commit()
        db.refresh(env_var)
        return env_var
    except IntegrityError:
        db.rollback()
        raise ValueError(f"Environment variable with key '{key}' already exists in this project")


def update_environment_variable(
    db: Session,
    project_id: int,
    key: str,
    value_encrypted: Optional[str] = None,
    description: Optional[str] = None,
    is_secret: Optional[bool] = None
) -> Optional[models.EnvironmentVariable]:
    """Update an environment variable"""
    env_var = get_environment_variable(db, project_id, key)
    if not env_var:
        return None

    if value_encrypted is not None:
        env_var.value_encrypted = value_encrypted
    if description is not None:
        env_var.description = description
    if is_secret is not None:
        env_var.is_secret = is_secret

    env_var.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(env_var)
    return env_var


def delete_environment_variable(
    db: Session,
    project_id: int,
    key: str
) -> bool:
    """Delete an environment variable"""
    env_var = get_environment_variable(db, project_id, key)
    if not env_var:
        return False

    db.delete(env_var)
    db.commit()
    return True


# ============================================================================
# CONFIGURATION HISTORY OPERATIONS
# ============================================================================

def get_configuration_history(
    db: Session,
    project_id: int,
    limit: int = 50
) -> List[models.ConfigurationHistory]:
    """Get configuration history for a project"""
    return db.query(models.ConfigurationHistory).filter(
        models.ConfigurationHistory.project_id == project_id
    ).order_by(models.ConfigurationHistory.changed_at.desc()).limit(limit).all()


def create_configuration_history(
    db: Session,
    project_id: int,
    changes_json: str,
    snapshot_json: str,
    changed_by: str = "system"
) -> models.ConfigurationHistory:
    """Create a configuration history entry"""
    # Get the next version number
    latest = db.query(models.ConfigurationHistory).filter(
        models.ConfigurationHistory.project_id == project_id
    ).order_by(models.ConfigurationHistory.version.desc()).first()

    version = (latest.version + 1) if latest else 1

    history = models.ConfigurationHistory(
        project_id=project_id,
        version=version,
        changed_by=changed_by,
        changes_json=changes_json,
        snapshot_json=snapshot_json
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
