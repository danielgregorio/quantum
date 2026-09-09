# Plano de Implementacao: Sistema de Logs com Sub-abas

## Visao Geral

Implementar um sistema completo de logs para aplicacoes Quantum com categorizacao por fonte, filtragem avancada e visualizacao em tempo real.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────┐
│                        FONTES DE LOG                            │
├─────────────┬─────────────┬─────────────┬─────────────┬─────────┤
│ App Runtime │  Database   │   Access    │  External   │ Deploy  │
│ (stdout/err)│  (queries)  │  (HTTP)     │   (APIs)    │ (CI/CD) │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴────┬────┘
       │             │             │             │           │
       ▼             ▼             ▼             ▼           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     LOG COLLECTOR SERVICE                        │
│  - Normaliza formato                                            │
│  - Adiciona metadata (project_id, timestamp, source)            │
│  - Envia para storage + WebSocket                               │
└─────────────────────────────────────────────────────────────────┘
       │                                              │
       ▼                                              ▼
┌─────────────────┐                    ┌─────────────────────────┐
│   SQLite/DB     │                    │   WebSocket Manager     │
│ (persistencia)  │                    │   (real-time push)      │
└─────────────────┘                    └─────────────────────────┘
       │                                              │
       ▼                                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND UI                              │
│  [All] [App] [Database] [Access] [API] [Security] [Deploy]     │
│  - Filtros (level, time, search)                                │
│  - Auto-refresh / Real-time                                     │
│  - Export (JSON, CSV)                                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Fases de Implementacao

### FASE 1: Modelo de Dados e Storage (2h)

#### 1.1 Criar modelo ApplicationLog

**Arquivo:** `quantum_admin/backend/models.py`

```python
class ApplicationLog(Base):
    """Log entry for application monitoring"""
    __tablename__ = 'application_logs'

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Categorizacao
    source = Column(String(20), nullable=False, index=True)
    # Valores: app, database, access, api, security, deploy, system

    level = Column(String(10), nullable=False, index=True)
    # Valores: DEBUG, INFO, WARN, ERROR, CRITICAL

    # Conteudo
    message = Column(Text, nullable=False)
    details = Column(JSON)  # Stack trace, request/response, query plan, etc.

    # Contexto
    component = Column(String(255))      # Componente .q que gerou o log
    endpoint = Column(String(255))       # Rota/endpoint (para access logs)
    method = Column(String(10))          # HTTP method (GET, POST, etc.)
    status_code = Column(Integer)        # HTTP status code
    duration_ms = Column(Integer)        # Duracao da operacao
    user_id = Column(String(100))        # Usuario associado
    user_ip = Column(String(45))         # IP do cliente
    request_id = Column(String(50))      # ID unico para correlacionar logs

    # Metadata
    environment = Column(String(50))     # dev, staging, production
    version = Column(String(50))         # Versao da aplicacao

    # Indices para queries frequentes
    __table_args__ = (
        Index('ix_logs_project_source', 'project_id', 'source'),
        Index('ix_logs_project_timestamp', 'project_id', 'timestamp'),
        Index('ix_logs_project_level', 'project_id', 'level'),
    )
```

#### 1.2 Schema Pydantic

**Arquivo:** `quantum_admin/backend/schemas.py`

```python
class LogCreate(BaseModel):
    source: str  # app, database, access, api, security, deploy
    level: str   # DEBUG, INFO, WARN, ERROR, CRITICAL
    message: str
    details: Optional[dict] = None
    component: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[int] = None
    user_id: Optional[str] = None
    user_ip: Optional[str] = None
    request_id: Optional[str] = None

class LogResponse(BaseModel):
    id: int
    project_id: int
    timestamp: datetime
    source: str
    level: str
    message: str
    details: Optional[dict]
    component: Optional[str]
    duration_ms: Optional[int]

    class Config:
        from_attributes = True

class LogFilter(BaseModel):
    source: Optional[str] = None      # Filtrar por fonte
    level: Optional[str] = None       # Filtrar por nivel
    search: Optional[str] = None      # Busca em message
    since: Optional[str] = "1h"       # Periodo: 1h, 6h, 24h, 7d, 30d
    component: Optional[str] = None   # Filtrar por componente
    limit: int = 100
    offset: int = 0
```

---

### FASE 2: Log Collector Service (3h)

#### 2.1 Criar servico de coleta

**Arquivo:** `quantum_admin/backend/log_service.py`

```python
"""
Log Collection and Management Service
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_, or_
import json
import re

from . import models, schemas
from .websocket_manager import WebSocketManager


class LogService:
    """Centralized log management service"""

    # Cores para cada source no terminal/UI
    SOURCE_COLORS = {
        'app': '#3B82F6',       # Blue
        'database': '#8B5CF6',  # Purple
        'access': '#10B981',    # Green
        'api': '#F59E0B',       # Amber
        'security': '#EF4444',  # Red
        'deploy': '#06B6D4',    # Cyan
        'system': '#6B7280',    # Gray
    }

    # Icones para cada source
    SOURCE_ICONS = {
        'app': '📱',
        'database': '🗄️',
        'access': '🌐',
        'api': '🔌',
        'security': '🔐',
        'deploy': '🚀',
        'system': '⚙️',
    }

    LEVEL_PRIORITY = {
        'DEBUG': 0,
        'INFO': 1,
        'WARN': 2,
        'ERROR': 3,
        'CRITICAL': 4,
    }

    def __init__(self, db: Session, ws_manager: Optional[WebSocketManager] = None):
        self.db = db
        self.ws_manager = ws_manager

    def log(
        self,
        project_id: int,
        source: str,
        level: str,
        message: str,
        **kwargs
    ) -> models.ApplicationLog:
        """
        Create a new log entry.

        Args:
            project_id: ID do projeto
            source: app, database, access, api, security, deploy, system
            level: DEBUG, INFO, WARN, ERROR, CRITICAL
            message: Mensagem do log
            **kwargs: Campos adicionais (details, component, endpoint, etc.)
        """
        log_entry = models.ApplicationLog(
            project_id=project_id,
            source=source.lower(),
            level=level.upper(),
            message=message,
            timestamp=datetime.utcnow(),
            **kwargs
        )

        self.db.add(log_entry)
        self.db.commit()
        self.db.refresh(log_entry)

        # Push to WebSocket for real-time updates
        if self.ws_manager:
            self._push_to_websocket(log_entry)

        return log_entry

    def _push_to_websocket(self, log_entry: models.ApplicationLog):
        """Send log entry to connected WebSocket clients"""
        log_data = {
            'type': 'log',
            'data': {
                'id': log_entry.id,
                'timestamp': log_entry.timestamp.isoformat(),
                'source': log_entry.source,
                'level': log_entry.level,
                'message': log_entry.message,
                'component': log_entry.component,
                'duration_ms': log_entry.duration_ms,
            }
        }
        # Broadcast to project channel
        self.ws_manager.broadcast_to_project(
            log_entry.project_id,
            'logs',
            log_data
        )

    def query(
        self,
        project_id: int,
        source: Optional[str] = None,
        level: Optional[str] = None,
        search: Optional[str] = None,
        since: str = "1h",
        component: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[models.ApplicationLog]:
        """
        Query logs with filters.
        """
        query = self.db.query(models.ApplicationLog).filter(
            models.ApplicationLog.project_id == project_id
        )

        # Filter by source
        if source and source != 'all':
            query = query.filter(models.ApplicationLog.source == source.lower())

        # Filter by level (and above)
        if level:
            min_priority = self.LEVEL_PRIORITY.get(level.upper(), 0)
            levels = [l for l, p in self.LEVEL_PRIORITY.items() if p >= min_priority]
            query = query.filter(models.ApplicationLog.level.in_(levels))

        # Filter by time
        since_map = {
            '15m': timedelta(minutes=15),
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30),
        }
        if since in since_map:
            since_time = datetime.utcnow() - since_map[since]
            query = query.filter(models.ApplicationLog.timestamp >= since_time)

        # Search in message
        if search:
            query = query.filter(
                models.ApplicationLog.message.ilike(f'%{search}%')
            )

        # Filter by component
        if component:
            query = query.filter(models.ApplicationLog.component == component)

        # Order by timestamp descending and apply pagination
        return query.order_by(
            desc(models.ApplicationLog.timestamp)
        ).offset(offset).limit(limit).all()

    def get_stats(self, project_id: int, since: str = "24h") -> Dict:
        """Get log statistics for a project"""
        since_map = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '24h': timedelta(hours=24),
            '7d': timedelta(days=7),
        }
        since_time = datetime.utcnow() - since_map.get(since, timedelta(hours=24))

        logs = self.db.query(models.ApplicationLog).filter(
            models.ApplicationLog.project_id == project_id,
            models.ApplicationLog.timestamp >= since_time
        ).all()

        stats = {
            'total': len(logs),
            'by_source': {},
            'by_level': {},
            'errors_count': 0,
            'avg_duration_ms': 0,
        }

        durations = []
        for log in logs:
            # Count by source
            stats['by_source'][log.source] = stats['by_source'].get(log.source, 0) + 1

            # Count by level
            stats['by_level'][log.level] = stats['by_level'].get(log.level, 0) + 1

            # Count errors
            if log.level in ('ERROR', 'CRITICAL'):
                stats['errors_count'] += 1

            # Collect durations
            if log.duration_ms:
                durations.append(log.duration_ms)

        if durations:
            stats['avg_duration_ms'] = sum(durations) / len(durations)

        return stats

    def clear_old_logs(self, project_id: int, days: int = 30) -> int:
        """Delete logs older than specified days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = self.db.query(models.ApplicationLog).filter(
            models.ApplicationLog.project_id == project_id,
            models.ApplicationLog.timestamp < cutoff
        ).delete()
        self.db.commit()
        return result


# Convenience functions for different log sources

def log_app(db, project_id, level, message, **kwargs):
    """Log application event"""
    return LogService(db).log(project_id, 'app', level, message, **kwargs)

def log_database(db, project_id, level, message, duration_ms=None, **kwargs):
    """Log database query/operation"""
    return LogService(db).log(
        project_id, 'database', level, message,
        duration_ms=duration_ms, **kwargs
    )

def log_access(db, project_id, method, endpoint, status_code, duration_ms, **kwargs):
    """Log HTTP access"""
    level = 'ERROR' if status_code >= 500 else 'WARN' if status_code >= 400 else 'INFO'
    message = f"{method} {endpoint} {status_code} {duration_ms}ms"
    return LogService(db).log(
        project_id, 'access', level, message,
        method=method, endpoint=endpoint,
        status_code=status_code, duration_ms=duration_ms,
        **kwargs
    )

def log_api(db, project_id, level, message, **kwargs):
    """Log external API call"""
    return LogService(db).log(project_id, 'api', level, message, **kwargs)

def log_security(db, project_id, level, message, user_id=None, user_ip=None, **kwargs):
    """Log security event"""
    return LogService(db).log(
        project_id, 'security', level, message,
        user_id=user_id, user_ip=user_ip, **kwargs
    )

def log_deploy(db, project_id, level, message, **kwargs):
    """Log deployment event"""
    return LogService(db).log(project_id, 'deploy', level, message, **kwargs)


# Singleton
_log_service = None

def get_log_service(db: Session) -> LogService:
    global _log_service
    if _log_service is None:
        _log_service = LogService(db)
    return _log_service
```

---

### FASE 3: API Endpoints (2h)

#### 3.1 Endpoints REST

**Arquivo:** `quantum_admin/backend/main.py` (adicionar)

```python
# ============================================================================
# LOG ENDPOINTS
# ============================================================================

@app.get("/api/projects/{project_id}/logs", tags=["Logs"])
def get_project_logs(
    project_id: int,
    source: str = "all",
    level: str = None,
    search: str = None,
    since: str = "1h",
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get project logs with filtering"""
    log_service = LogService(db)
    logs = log_service.query(
        project_id=project_id,
        source=source if source != "all" else None,
        level=level,
        search=search,
        since=since,
        limit=limit,
        offset=offset
    )
    return [schemas.LogResponse.from_orm(log) for log in logs]


@app.get("/api/projects/{project_id}/logs/stats", tags=["Logs"])
def get_project_log_stats(
    project_id: int,
    since: str = "24h",
    db: Session = Depends(get_db)
):
    """Get log statistics"""
    log_service = LogService(db)
    return log_service.get_stats(project_id, since)


@app.post("/api/projects/{project_id}/logs", tags=["Logs"])
def create_log_entry(
    project_id: int,
    log_data: schemas.LogCreate,
    db: Session = Depends(get_db)
):
    """Create a new log entry (for external integrations)"""
    log_service = LogService(db)
    log_entry = log_service.log(
        project_id=project_id,
        **log_data.dict()
    )
    return schemas.LogResponse.from_orm(log_entry)


@app.delete("/api/projects/{project_id}/logs/clear", tags=["Logs"])
def clear_old_logs(
    project_id: int,
    days: int = 30,
    db: Session = Depends(get_db),
    user: User = Depends(require_auth)
):
    """Clear logs older than specified days"""
    log_service = LogService(db)
    deleted = log_service.clear_old_logs(project_id, days)
    return {"deleted": deleted}
```

---

### FASE 4: UI com Sub-abas (3h)

#### 4.1 Atualizar tab de Logs no Project Detail

**Substituir a tab Logs existente:**

```python
      <!-- Logs Tab -->
      <div id="tab-logs" class="qa-tab-content qa-hidden">
        <div class="qa-card">
          <div class="qa-card-header">
            <div class="qa-flex qa-justify-between qa-items-center qa-mb-4">
              <h3 class="qa-card-title">Application Logs</h3>
              <div class="qa-flex qa-gap-2">
                <button class="qa-btn qa-btn-ghost qa-btn-sm" id="logs-auto-btn" onclick="toggleLogsAutoRefresh()">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                  Auto
                </button>
                <button class="qa-btn qa-btn-secondary qa-btn-sm" onclick="refreshLogs()">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                  Refresh
                </button>
                <button class="qa-btn qa-btn-ghost qa-btn-sm" onclick="exportLogs()">
                  <svg width="14" height="14" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                  </svg>
                  Export
                </button>
              </div>
            </div>

            <!-- Source Sub-tabs -->
            <div class="qa-flex qa-gap-2 qa-mb-4 qa-flex-wrap">
              <button class="qa-btn qa-btn-sm log-source-tab active" data-source="all" onclick="filterLogSource('all')">
                All
              </button>
              <button class="qa-btn qa-btn-sm qa-btn-ghost log-source-tab" data-source="app" onclick="filterLogSource('app')">
                <span style="color: #3B82F6;">📱</span> App
              </button>
              <button class="qa-btn qa-btn-sm qa-btn-ghost log-source-tab" data-source="database" onclick="filterLogSource('database')">
                <span style="color: #8B5CF6;">🗄️</span> Database
              </button>
              <button class="qa-btn qa-btn-sm qa-btn-ghost log-source-tab" data-source="access" onclick="filterLogSource('access')">
                <span style="color: #10B981;">🌐</span> Access
              </button>
              <button class="qa-btn qa-btn-sm qa-btn-ghost log-source-tab" data-source="api" onclick="filterLogSource('api')">
                <span style="color: #F59E0B;">🔌</span> API
              </button>
              <button class="qa-btn qa-btn-sm qa-btn-ghost log-source-tab" data-source="security" onclick="filterLogSource('security')">
                <span style="color: #EF4444;">🔐</span> Security
              </button>
              <button class="qa-btn qa-btn-sm qa-btn-ghost log-source-tab" data-source="deploy" onclick="filterLogSource('deploy')">
                <span style="color: #06B6D4;">🚀</span> Deploy
              </button>
            </div>

            <!-- Filters Row -->
            <div class="qa-flex qa-gap-3 qa-flex-wrap qa-items-center">
              <div class="qa-flex qa-items-center qa-gap-2">
                <svg width="16" height="16" class="qa-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                <input type="text" id="log-search" class="qa-input qa-input-sm" placeholder="Search logs..." style="width: 200px;" onkeyup="debounceLogSearch()">
              </div>

              <select id="log-level" class="qa-input qa-input-sm qa-select" style="width: 120px;" onchange="refreshLogs()">
                <option value="">All Levels</option>
                <option value="DEBUG">Debug+</option>
                <option value="INFO">Info+</option>
                <option value="WARN">Warn+</option>
                <option value="ERROR">Error+</option>
                <option value="CRITICAL">Critical</option>
              </select>

              <select id="log-since" class="qa-input qa-input-sm qa-select" style="width: 120px;" onchange="refreshLogs()">
                <option value="15m">Last 15 min</option>
                <option value="1h" selected>Last hour</option>
                <option value="6h">Last 6 hours</option>
                <option value="24h">Last 24 hours</option>
                <option value="7d">Last 7 days</option>
                <option value="30d">Last 30 days</option>
              </select>

              <div id="log-stats" class="qa-text-sm qa-text-muted qa-ml-auto">
                <!-- Stats will be loaded here -->
              </div>
            </div>
          </div>

          <!-- Log entries container -->
          <div class="qa-card-body qa-p-0" id="logs-container" style="max-height: 600px; overflow-y: auto;">
            <div id="logs-list" hx-get="{URL_PREFIX}/api/projects/{project_id}/logs-html" hx-trigger="load" hx-swap="innerHTML">
              <div class="qa-text-center qa-text-muted qa-p-6">Loading logs...</div>
            </div>
          </div>
        </div>
      </div>
```

#### 4.2 Endpoint HTML para logs

```python
@app.get("/api/projects/{project_id}/logs-html", response_class=HTMLResponse, tags=["Logs UI"])
def get_project_logs_html(
    project_id: int,
    source: str = "all",
    level: str = None,
    search: str = None,
    since: str = "1h",
    db: Session = Depends(get_db)
):
    """Get project logs as HTML for HTMX"""
    log_service = LogService(db)
    logs = log_service.query(
        project_id=project_id,
        source=source if source != "all" else None,
        level=level,
        search=search,
        since=since,
        limit=200
    )

    if not logs:
        return HTMLResponse(content='''
            <div class="qa-text-center qa-text-muted qa-p-8">
                <svg width="48" height="48" class="qa-mx-auto qa-mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                </svg>
                <p class="qa-mb-2">No logs found</p>
                <p class="qa-text-sm">Try adjusting your filters or time range</p>
            </div>
        ''')

    # Color and icon maps
    source_colors = {
        'app': '#3B82F6',
        'database': '#8B5CF6',
        'access': '#10B981',
        'api': '#F59E0B',
        'security': '#EF4444',
        'deploy': '#06B6D4',
        'system': '#6B7280',
    }
    source_icons = {
        'app': '📱',
        'database': '🗄️',
        'access': '🌐',
        'api': '🔌',
        'security': '🔐',
        'deploy': '🚀',
        'system': '⚙️',
    }
    level_colors = {
        'DEBUG': 'qa-text-muted',
        'INFO': 'qa-text-info',
        'WARN': 'qa-text-warning',
        'ERROR': 'qa-text-danger',
        'CRITICAL': 'qa-text-danger qa-font-bold',
    }

    rows = ""
    for log in logs:
        time_str = log.timestamp.strftime('%H:%M:%S')
        source_color = source_colors.get(log.source, '#6B7280')
        source_icon = source_icons.get(log.source, '📝')
        level_class = level_colors.get(log.level, '')

        duration_badge = ""
        if log.duration_ms:
            duration_class = "qa-text-success" if log.duration_ms < 100 else "qa-text-warning" if log.duration_ms < 500 else "qa-text-danger"
            duration_badge = f'<span class="qa-badge qa-badge-outline {duration_class}" style="font-size: 0.7rem;">{log.duration_ms}ms</span>'

        component_badge = ""
        if log.component:
            component_badge = f'<span class="qa-text-xs qa-text-muted qa-ml-2">[{log.component}]</span>'

        rows += f'''
        <div class="qa-log-entry qa-flex qa-items-start qa-gap-3 qa-p-3 qa-border-b" style="font-family: monospace; font-size: 0.85rem;">
          <span class="qa-text-muted" style="min-width: 70px;">{time_str}</span>
          <span class="qa-badge" style="background: {source_color}20; color: {source_color}; min-width: 80px; text-align: center;">
            {source_icon} {log.source.upper()}
          </span>
          <span class="{level_class}" style="min-width: 60px;">{log.level}</span>
          <span class="qa-flex-1">
            {log.message}
            {component_badge}
          </span>
          {duration_badge}
        </div>
        '''

    return HTMLResponse(content=f'''
        <div class="qa-logs-list">
            {rows}
        </div>
    ''')
```

#### 4.3 JavaScript para interatividade

```javascript
// Log filtering state
let currentLogSource = 'all';
let logsAutoRefresh = false;
let logsRefreshInterval = null;
let logSearchDebounce = null;

function filterLogSource(source) {
  currentLogSource = source;

  // Update active tab
  document.querySelectorAll('.log-source-tab').forEach(btn => {
    btn.classList.remove('active');
    if (btn.dataset.source !== 'all') btn.classList.add('qa-btn-ghost');
  });
  const activeBtn = document.querySelector(`.log-source-tab[data-source="${source}"]`);
  if (activeBtn) {
    activeBtn.classList.add('active');
    activeBtn.classList.remove('qa-btn-ghost');
  }

  refreshLogs();
}

function refreshLogs() {
  const source = currentLogSource;
  const level = document.getElementById('log-level').value;
  const since = document.getElementById('log-since').value;
  const search = document.getElementById('log-search').value;

  const params = new URLSearchParams({
    source: source,
    since: since,
  });
  if (level) params.append('level', level);
  if (search) params.append('search', search);

  htmx.ajax('GET', `{URL_PREFIX}/api/projects/{project_id}/logs-html?${params}`, '#logs-list');
  loadLogStats();
}

function debounceLogSearch() {
  clearTimeout(logSearchDebounce);
  logSearchDebounce = setTimeout(refreshLogs, 300);
}

function toggleLogsAutoRefresh() {
  logsAutoRefresh = !logsAutoRefresh;
  const btn = document.getElementById('logs-auto-btn');

  if (logsAutoRefresh) {
    btn.classList.add('qa-btn-primary');
    btn.classList.remove('qa-btn-ghost');
    logsRefreshInterval = setInterval(refreshLogs, 5000);
  } else {
    btn.classList.remove('qa-btn-primary');
    btn.classList.add('qa-btn-ghost');
    clearInterval(logsRefreshInterval);
  }
}

function loadLogStats() {
  const since = document.getElementById('log-since').value;
  fetch(`{URL_PREFIX}/api/projects/{project_id}/logs/stats?since=${since}`)
    .then(r => r.json())
    .then(stats => {
      document.getElementById('log-stats').innerHTML = `
        <span class="qa-mr-3">Total: <strong>${stats.total}</strong></span>
        <span class="qa-text-danger">Errors: <strong>${stats.errors_count}</strong></span>
      `;
    });
}

function exportLogs() {
  const source = currentLogSource;
  const level = document.getElementById('log-level').value;
  const since = document.getElementById('log-since').value;
  const search = document.getElementById('log-search').value;

  const params = new URLSearchParams({
    source: source,
    since: since,
    limit: 10000,
  });
  if (level) params.append('level', level);
  if (search) params.append('search', search);

  window.open(`{URL_PREFIX}/api/projects/{project_id}/logs?${params}&format=csv`, '_blank');
}
```

---

### FASE 5: Integracao com Runtime Quantum (2h)

#### 5.1 Middleware de Access Logs

Adicionar ao web_server.py do Quantum:

```python
@app.before_request
def log_access_start():
    g.request_start = time.time()
    g.request_id = str(uuid.uuid4())[:8]

@app.after_request
def log_access_end(response):
    if hasattr(g, 'request_start'):
        duration_ms = int((time.time() - g.request_start) * 1000)
        log_access(
            db=get_db(),
            project_id=current_project_id,
            method=request.method,
            endpoint=request.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            user_ip=request.remote_addr,
            request_id=g.request_id
        )
    return response
```

#### 5.2 Database Query Logger

Hook no database_service.py:

```python
def log_query(query, duration_ms, project_id):
    log_database(
        db=get_admin_db(),
        project_id=project_id,
        level='DEBUG' if duration_ms < 100 else 'WARN',
        message=f"Query executed: {query[:100]}...",
        duration_ms=duration_ms,
        details={'full_query': query}
    )
```

---

### FASE 6: WebSocket Real-time (2h)

#### 6.1 Adicionar canal de logs ao WebSocket Manager

```python
# Em websocket_manager.py
class LogChannel:
    """WebSocket channel for real-time log streaming"""

    def __init__(self):
        self.connections: Dict[int, Set[WebSocket]] = {}  # project_id -> connections

    async def connect(self, websocket: WebSocket, project_id: int):
        await websocket.accept()
        if project_id not in self.connections:
            self.connections[project_id] = set()
        self.connections[project_id].add(websocket)

    def disconnect(self, websocket: WebSocket, project_id: int):
        if project_id in self.connections:
            self.connections[project_id].discard(websocket)

    async def broadcast(self, project_id: int, log_entry: dict):
        if project_id in self.connections:
            for ws in self.connections[project_id]:
                try:
                    await ws.send_json(log_entry)
                except:
                    pass
```

#### 6.2 Endpoint WebSocket

```python
@app.websocket("/ws/projects/{project_id}/logs")
async def logs_websocket(websocket: WebSocket, project_id: int):
    log_channel = get_log_channel()
    await log_channel.connect(websocket, project_id)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        log_channel.disconnect(websocket, project_id)
```

---

## Resumo de Arquivos a Criar/Modificar

| Arquivo | Acao | Descricao |
|---------|------|-----------|
| `models.py` | Modificar | Adicionar modelo ApplicationLog |
| `schemas.py` | Modificar | Adicionar LogCreate, LogResponse, LogFilter |
| `log_service.py` | Criar | Servico de coleta e query de logs |
| `main.py` | Modificar | Adicionar endpoints de logs + UI |
| `websocket_manager.py` | Modificar | Adicionar LogChannel |

---

## Ordem de Execucao

1. **FASE 1** - Modelo de dados (2h)
2. **FASE 2** - Log Service (3h)
3. **FASE 3** - API Endpoints (2h)
4. **FASE 4** - UI com sub-abas (3h)
5. **FASE 5** - Integracao runtime (2h)
6. **FASE 6** - WebSocket real-time (2h)

**Total estimado: ~14h**

---

## Verificacao

### Apos cada fase:

```bash
# Testar API
curl http://localhost:8001/api/projects/1/logs?source=app&since=1h

# Testar stats
curl http://localhost:8001/api/projects/1/logs/stats

# Testar UI
# Acessar http://localhost:8001/admin/projects/1 -> aba Logs
```

### Checklist final:

- [ ] Sub-abas All/App/Database/Access/API/Security/Deploy funcionando
- [ ] Filtro por level funcionando
- [ ] Filtro por periodo funcionando
- [ ] Busca em mensagens funcionando
- [ ] Auto-refresh funcionando
- [ ] Export para CSV/JSON funcionando
- [ ] WebSocket real-time funcionando
- [ ] Logs de access sendo coletados
- [ ] Logs de database sendo coletados
- [ ] Logs de deploy sendo coletados
