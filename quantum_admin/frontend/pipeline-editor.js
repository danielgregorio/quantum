/**
 * Quantum Admin - Pipeline Editor
 * Visual editor for <q:pipeline> XML syntax with Jenkinsfile generation
 */

const API_BASE = 'http://localhost:8000';

// ============================================================================
// Templates
// ============================================================================

const TEMPLATES = {
    'basic-build': `<q:pipeline name="Basic Build Pipeline" description="Simple build and test pipeline">
    <q:agent type="any"/>

    <q:stage name="Checkout">
        <q:step type="git" url="https://github.com/user/repo.git" branch="main"/>
    </q:stage>

    <q:stage name="Build">
        <q:step type="shell">npm install</q:step>
        <q:step type="shell">npm run build</q:step>
    </q:stage>

    <q:stage name="Test">
        <q:step type="shell">npm test</q:step>
    </q:stage>

    <q:post>
        <q:success>
            <q:step type="shell">echo "Build successful!"</q:step>
        </q:success>
        <q:failure>
            <q:step type="shell">echo "Build failed!"</q:step>
        </q:failure>
    </q:post>
</q:pipeline>`,

    'docker-deploy': `<q:pipeline name="Docker Deploy Pipeline" description="Build and deploy Docker image">
    <q:agent type="docker" image="docker:latest"/>

    <q:environment>
        <q:var name="DOCKER_REGISTRY">registry.example.com</q:var>
        <q:var name="IMAGE_NAME">myapp</q:var>
    </q:environment>

    <q:stage name="Build Image">
        <q:step type="shell">docker build -t $IMAGE_NAME:$BUILD_NUMBER .</q:step>
    </q:stage>

    <q:stage name="Push Image">
        <q:step type="shell">docker tag $IMAGE_NAME:$BUILD_NUMBER $DOCKER_REGISTRY/$IMAGE_NAME:latest</q:step>
        <q:step type="shell">docker push $DOCKER_REGISTRY/$IMAGE_NAME:latest</q:step>
    </q:stage>

    <q:stage name="Deploy">
        <q:step type="shell">kubectl set image deployment/myapp myapp=$DOCKER_REGISTRY/$IMAGE_NAME:latest</q:step>
    </q:stage>
</q:pipeline>`,

    'parallel-tests': `<q:pipeline name="Parallel Test Pipeline" description="Run tests in parallel">
    <q:agent type="any"/>

    <q:stage name="Build">
        <q:step type="shell">npm install</q:step>
        <q:step type="shell">npm run build</q:step>
    </q:stage>

    <q:stage name="Parallel Tests" parallel="true">
        <q:step type="shell" name="Unit Tests">npm run test:unit</q:step>
        <q:step type="shell" name="Integration Tests">npm run test:integration</q:step>
        <q:step type="shell" name="E2E Tests">npm run test:e2e</q:step>
    </q:stage>

    <q:stage name="Report">
        <q:step type="shell">npm run test:report</q:step>
    </q:stage>
</q:pipeline>`
};

// ============================================================================
// Tab Switching
// ============================================================================

function switchPipelineTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content-pipeline').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab-pipeline').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');

    // Add active class to button
    event.target.classList.add('active');
}

// ============================================================================
// Template Loading
// ============================================================================

function loadTemplate(templateName) {
    const template = TEMPLATES[templateName];
    if (template) {
        document.getElementById('xml-editor').value = template;
        switchPipelineTab('editor');

        // Show success message
        showSuccess('Template loaded successfully!');

        // Auto-generate
        setTimeout(generateJenkinsfile, 500);
    }
}

// ============================================================================
// Jenkinsfile Generation
// ============================================================================

async function generateJenkinsfile() {
    const xmlContent = document.getElementById('xml-editor').value;
    const errorDiv = document.getElementById('error-message');
    const successDiv = document.getElementById('success-message');
    const outputDiv = document.getElementById('jenkinsfile-output');

    // Clear previous messages
    errorDiv.innerHTML = '';
    successDiv.innerHTML = '';

    try {
        const response = await fetch(`${API_BASE}/pipeline/generate`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                xml_content: xmlContent
            })
        });

        const data = await response.json();

        if (response.ok) {
            // Display generated Jenkinsfile
            outputDiv.textContent = data.jenkinsfile;

            // Show success message
            showSuccess('Jenkinsfile generated successfully!');

        } else {
            // Show error message
            showError(data.detail || 'Failed to generate Jenkinsfile');
            outputDiv.textContent = '// Error generating Jenkinsfile\n// Please fix the XML syntax and try again';
        }

    } catch (error) {
        console.error('Generation error:', error);
        showError('Network error. Please check your connection and try again.');
        outputDiv.textContent = '// Error: Could not connect to server';
    }
}

// ============================================================================
// Download Jenkinsfile
// ============================================================================

function downloadJenkinsfile() {
    const jenkinsfileContent = document.getElementById('jenkinsfile-output').textContent;

    if (jenkinsfileContent.startsWith('//')) {
        alert('Please generate a valid Jenkinsfile first');
        return;
    }

    // Create blob and download
    const blob = new Blob([jenkinsfileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'Jenkinsfile';
    a.click();
    URL.revokeObjectURL(url);

    showSuccess('Jenkinsfile downloaded successfully!');
}

// ============================================================================
// UI Helpers
// ============================================================================

function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.innerHTML = `<div class="error-message">${message}</div>`;

    setTimeout(() => {
        errorDiv.innerHTML = '';
    }, 5000);
}

function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    successDiv.innerHTML = `<div class="success-message">${message}</div>`;

    setTimeout(() => {
        successDiv.innerHTML = '';
    }, 3000);
}

// ============================================================================
// Auto-save to localStorage
// ============================================================================

let autoSaveTimeout;

document.getElementById('xml-editor').addEventListener('input', function() {
    clearTimeout(autoSaveTimeout);
    autoSaveTimeout = setTimeout(() => {
        localStorage.setItem('pipeline-xml-draft', this.value);
    }, 1000);
});

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // Load draft from localStorage
    const draft = localStorage.getItem('pipeline-xml-draft');
    if (draft) {
        const editor = document.getElementById('xml-editor');
        if (editor.value.trim() === '' || confirm('Load saved draft?')) {
            editor.value = draft;
        }
    }

    // Auto-generate on load
    generateJenkinsfile();

    // Add keyboard shortcuts
    document.getElementById('xml-editor').addEventListener('keydown', function(e) {
        // Ctrl/Cmd + S to generate
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            generateJenkinsfile();
        }

        // Ctrl/Cmd + D to download
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            downloadJenkinsfile();
        }

        // Tab key to indent
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = this.selectionStart;
            const end = this.selectionEnd;
            this.value = this.value.substring(0, start) + '    ' + this.value.substring(end);
            this.selectionStart = this.selectionEnd = start + 4;
        }
    });
});

// ============================================================================
// Syntax Highlighting (Basic)
// ============================================================================

function highlightXML() {
    // This is a placeholder for future XML syntax highlighting
    // Could integrate with libraries like Prism.js or CodeMirror
}
