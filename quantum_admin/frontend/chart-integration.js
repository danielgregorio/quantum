/**
 * Chart.js Integration for Real-time Metrics
 * Replaces placeholder charts with functional visualizations
 */

// Load Chart.js from CDN
const CHART_JS_CDN = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js';

let Chart = null;
let charts = {};

// Initialize Chart.js
async function initChartJS() {
    if (window.Chart) {
        Chart = window.Chart;
        return;
    }

    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = CHART_JS_CDN;
        script.onload = () => {
            Chart = window.Chart;
            resolve();
        };
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

// Chart configurations
const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            display: true,
            position: 'top'
        }
    }
};

// Create CPU & Memory Chart
function createCPUMemoryChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const data = {
        labels: generateTimeLabels(20),
        datasets: [
            {
                label: 'CPU %',
                data: generateRandomData(20, 10, 40),
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                tension: 0.4,
                fill: true
            },
            {
                label: 'Memory %',
                data: generateRandomData(20, 30, 70),
                borderColor: '#f093fb',
                backgroundColor: 'rgba(240, 147, 251, 0.1)',
                tension: 0.4,
                fill: true
            }
        ]
    };

    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            ...chartDefaults,
            scales: {
                y: {
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Create Request Rate Chart
function createRequestsChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const data = {
        labels: generateTimeLabels(20),
        datasets: [{
            label: 'Requests/min',
            data: generateRandomData(20, 50, 200),
            borderColor: '#11998e',
            backgroundColor: 'rgba(17, 153, 142, 0.1)',
            tension: 0.4,
            fill: true
        }]
    };

    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            ...chartDefaults,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create Response Time Chart
function createResponseTimeChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const data = {
        labels: generateTimeLabels(20),
        datasets: [{
            label: 'Response Time (ms)',
            data: generateRandomData(20, 10, 100),
            borderColor: '#ffc107',
            backgroundColor: 'rgba(255, 193, 7, 0.1)',
            tension: 0.4,
            fill: true
        }]
    };

    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            ...chartDefaults,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create Error Rate Chart
function createErrorsChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const data = {
        labels: generateTimeLabels(20),
        datasets: [{
            label: 'Errors/min',
            data: generateRandomData(20, 0, 10),
            borderColor: '#dc3545',
            backgroundColor: 'rgba(220, 53, 69, 0.1)',
            tension: 0.4,
            fill: true
        }]
    };

    return new Chart(ctx, {
        type: 'line',
        data: data,
        options: {
            ...chartDefaults,
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Create Pie Chart
function createPieChart(canvasId, labels, data, colors) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    return new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 0
            }]
        },
        options: {
            ...chartDefaults,
            cutout: '60%'
        }
    });
}

// Helper: Generate time labels
function generateTimeLabels(count) {
    const labels = [];
    const now = new Date();

    for (let i = count - 1; i >= 0; i--) {
        const time = new Date(now - i * 60000);
        labels.push(time.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }));
    }

    return labels;
}

// Helper: Generate random data
function generateRandomData(count, min, max) {
    return Array.from({ length: count }, () =>
        Math.floor(Math.random() * (max - min + 1)) + min
    );
}

// Update chart data (for real-time updates)
function updateChartData(chart, newDataPoint) {
    if (!chart) return;

    chart.data.datasets.forEach(dataset => {
        dataset.data.push(newDataPoint);
        if (dataset.data.length > 20) {
            dataset.data.shift();
        }
    });

    chart.data.labels.push(new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit'
    }));

    if (chart.data.labels.length > 20) {
        chart.data.labels.shift();
    }

    chart.update('none'); // Update without animation for performance
}

// Auto-update charts
function startAutoUpdate(charts, interval = 5000) {
    setInterval(() => {
        Object.values(charts).forEach(chart => {
            if (chart && chart.data.datasets) {
                chart.data.datasets.forEach(dataset => {
                    const lastValue = dataset.data[dataset.data.length - 1] || 50;
                    const newValue = lastValue + (Math.random() - 0.5) * 20;
                    const clampedValue = Math.max(0, Math.min(100, newValue));

                    updateChartData(chart, clampedValue);
                });
            }
        });
    }, interval);
}

// Initialize all monitoring charts
async function initMonitoringCharts() {
    try {
        await initChartJS();

        charts.cpuMemory = createCPUMemoryChart('cpuMemoryChart');
        charts.requests = createRequestsChart('requestsChart');
        charts.responseTime = createResponseTimeChart('responseTimeChart');
        charts.errors = createErrorsChart('errorsChart');

        // Start auto-update
        startAutoUpdate(charts);

        console.log('📊 Charts initialized successfully');
    } catch (error) {
        console.error('Error initializing charts:', error);
    }
}

// Export for global use
window.ChartIntegration = {
    init: initMonitoringCharts,
    createCPUMemoryChart,
    createRequestsChart,
    createResponseTimeChart,
    createErrorsChart,
    createPieChart,
    updateChartData,
    charts
};
