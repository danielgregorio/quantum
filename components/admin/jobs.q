<q:component name="AdminJobs" require_auth="true" require_role="admin" login_url="/admin/login">
  <!-- Fila de q:job em quantum_jobs.db, somente leitura (admin.jobs.list). -->
  <q:import component="AdminShell" from="admin" />

  <q:invoke name="fila" service="admin.jobs.list" />

  <AdminShell title="Jobs" active="jobs" flash="{flash}" flashType="{flashType}">

    <div class="qa-grid qa-grid-4 qa-mb-6">
      <div class="qa-stat-card">
        <div class="qa-stat-label">Pending</div>
        <div class="qa-stat-value" style="color: var(--q-warning);">{fila.counts.pending}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">waiting in queue</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Running</div>
        <div class="qa-stat-value" style="color: var(--q-info);">{fila.counts.running}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">currently executing</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Completed</div>
        <div class="qa-stat-value" style="color: var(--q-success);">{fila.counts.completed}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">finished successfully</span></div>
      </div>
      <div class="qa-stat-card">
        <div class="qa-stat-label">Failed</div>
        <div class="qa-stat-value" style="color: var(--q-danger);">{fila.counts.failed}</div>
        <div class="qa-stat-change"><span class="qa-text-muted">out of attempts</span></div>
      </div>
    </div>

    <q:if condition="fila.error">
      <div class="qa-flash qa-flash-error" role="alert">quantum_jobs.db could not be read: {fila.error}</div>
    </q:if>

    <q:if condition="fila.found">
      <div class="qa-card">
        <div class="qa-card-header">
          <div>
            <div class="qa-card-title">Recent Jobs</div>
            <div class="qa-card-subtitle">{fila.total} jobs in total, newest {len(fila.jobs)} shown</div>
          </div>
        </div>
        <div class="qa-card-body qa-p-0" style="overflow-x: auto;">
          <table class="qa-table">
            <thead><tr><th>ID</th><th>Name</th><th>Queue</th><th>Status</th><th>Attempts</th><th>Created</th><th>Error</th></tr></thead>
            <tbody>
              <q:loop type="array" var="job" items="{fila.jobs}">
                <tr>
                  <td><span class="qa-font-mono">{job.id}</span></td>
                  <td>{job.name or '-'}</td>
                  <td><span class="qa-badge qa-badge-info">{job.queue or 'default'}</span></td>
                  <td><span class="{'qa-badge qa-badge-success' if job.status == 'completed' else ('qa-badge qa-badge-danger' if job.status == 'failed' else ('qa-badge qa-badge-warning' if job.status == 'pending' else 'qa-badge qa-badge-info'))}">{job.status}</span></td>
                  <td style="font-variant-numeric: tabular-nums;">{job.attempts}/{job.max_attempts}</td>
                  <td><span class="qa-text-sm qa-text-muted">{job.created_at or '-'}</span></td>
                  <td><span class="qa-text-sm qa-text-muted qa-truncate" style="max-width: 320px; display: inline-block;" title="{job.error or ''}">{job.error or '-'}</span></td>
                </tr>
              </q:loop>
            </tbody>
          </table>
        </div>
      </div>
    </q:if>

    <q:if condition="not fila.found">
      <div class="qa-card">
        <div class="qa-empty">
          <div class="qa-empty-title">No Job Queue Yet</div>
          <div class="qa-empty-text">quantum_jobs.db does not exist in the project root. It is created the first time a q:job is dispatched.</div>
        </div>
      </div>
    </q:if>

  </AdminShell>
</q:component>
