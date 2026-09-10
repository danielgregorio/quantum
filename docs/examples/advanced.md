---
layout: doc
title: Advanced Examples
---

<script setup>
import { ref, onMounted } from 'vue'

const examples = ref([])

onMounted(async () => {
  try {
    const data = await import('../../examples/_metadata/advanced.json')
    examples.value = data.examples || []
  } catch (e) {
    console.warn('Could not load examples metadata')
  }
})
</script>

# Advanced Examples

Complex examples combining multiple features - real-world applications.

<div class="related-links">
  <a href="../guide/project-structure" class="related-link">Project Structure</a>
</div>

## All Examples

<ExampleGallery :examples="examples" />

## Application Types

### Desktop Application

Build cross-platform desktop apps:

```xml
<q:application id="desktop" type="desktop" width="1200" height="800">
  <q:window title="Task Manager" icon="/assets/icon.png">
    <q:menu>
      <q:menu-item label="File">
        <q:menu-item label="New" shortcut="Ctrl+N" action="newTask" />
        <q:menu-item label="Exit" action="exit" />
      </q:menu-item>
    </q:menu>

    <!-- App content -->
  </q:window>
</q:application>
```

### Job Queue

Background job processing:

```xml
<q:job-queue name="emails" workers="3">
  <q:job name="sendWelcome">
    <q:mail to="{job.data.email}" subject="Welcome!">
      <h1>Welcome, {job.data.name}!</h1>
    </q:mail>
  </q:job>
</q:job-queue>

<!-- Enqueue a job -->
<q:enqueue queue="emails" job="sendWelcome">
  <q:data email="{user.email}" name="{user.name}" />
</q:enqueue>
```

### Python Integration

Call Python code from Quantum:

```xml
<q:python name="analysis" script="/scripts/analyze.py">
  <q:arg name="data" value="{salesData}" />
</q:python>

<p>Analysis Result: {analysis.result}</p>
```

## Featured Applications

| Application | Description |
|-------------|-------------|
| [chat.q](https://github.com/danielgregorio/quantum/blob/main/examples/chat.q) | Real-time chat application |
| [task-manager-desktop.q](https://github.com/danielgregorio/quantum/blob/main/examples/task-manager-desktop.q) | Desktop task management app |
| [filebrowser.q](https://github.com/danielgregorio/quantum/blob/main/examples/filebrowser.q) | File browser interface |

## Related Categories

All other categories build up to these advanced examples:

- [State Management](/examples/state-management)
- [Database Queries](/examples/queries)
- [Authentication](/examples/authentication)
- [AI Agents](/examples/agents)
