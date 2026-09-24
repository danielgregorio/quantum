#!/usr/bin/env python
"""
Quantum Benchmark Runner

Runs all benchmarks and generates reports comparing Quantum
with other platforms and languages.

Usage:
    python run_all.py                    # Run all benchmarks
    python run_all.py --category core    # Run specific category
    python run_all.py --report html      # Generate HTML report
    python run_all.py --quick            # Quick run (fewer iterations)
"""

import sys
import argparse
import json
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from framework import BenchmarkSuite, Benchmark


def load_benchmarks():
    """Load all benchmark modules"""
    import bench_core
    import bench_data
    import bench_python
    import bench_comparisons

    return [
        bench_core,
        bench_data,
        bench_python,
        bench_comparisons
    ]


def run_all_benchmarks(quick=False):
    """Run all registered benchmarks"""
    print("=" * 70)
    print("  QUANTUM FRAMEWORK BENCHMARKS")
    print("=" * 70)
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()

    # Load benchmark modules
    load_benchmarks()

    # Create suite
    suite = BenchmarkSuite("Quantum Complete Benchmark Suite")

    # Run all benchmarks
    print("Running benchmarks...\n")
    suite.run_all()

    return suite


def run_category(category: str, quick=False):
    """Run benchmarks in a specific category"""
    print(f"Running {category} benchmarks...")

    # Load benchmark modules
    load_benchmarks()

    # Create suite
    suite = BenchmarkSuite(f"Quantum {category.title()} Benchmarks")

    # Run category
    suite.run_category(category)

    return suite


def generate_html_report(suite: BenchmarkSuite, output_path: str = "benchmarks/results"):
    """Generate an HTML report with charts"""
    results_dir = Path(output_path)
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"report_{timestamp}.html"

    # Group results by category
    categories = {}
    for result in suite.results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantum Benchmark Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
            padding: 2rem;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, #3b82f6, #8b5cf6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{ color: #94a3b8; margin-bottom: 2rem; }}
        .system-info {{
            background: #1e293b;
            border-radius: 0.5rem;
            padding: 1rem;
            margin-bottom: 2rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
        }}
        .system-info-item {{ }}
        .system-info-label {{ color: #94a3b8; font-size: 0.875rem; }}
        .system-info-value {{ color: #f1f5f9; font-weight: 600; }}
        .category {{
            background: #1e293b;
            border-radius: 0.75rem;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        .category-title {{
            font-size: 1.25rem;
            color: #3b82f6;
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1rem;
        }}
        th, td {{
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #334155;
        }}
        th {{
            color: #94a3b8;
            font-weight: 500;
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        td {{ color: #e2e8f0; }}
        .number {{ text-align: right; font-family: monospace; }}
        .fast {{ color: #22c55e; }}
        .medium {{ color: #f59e0b; }}
        .slow {{ color: #ef4444; }}
        .chart-container {{
            height: 300px;
            margin-top: 1rem;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .summary-card {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #334155;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
        }}
        .summary-value {{
            font-size: 2rem;
            font-weight: 700;
            color: #3b82f6;
        }}
        .summary-label {{ color: #94a3b8; font-size: 0.875rem; }}
        footer {{
            text-align: center;
            color: #64748b;
            margin-top: 2rem;
            padding-top: 2rem;
            border-top: 1px solid #334155;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Quantum Framework Benchmarks</h1>
        <p class="subtitle">Performance analysis report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="system-info">
            <div class="system-info-item">
                <div class="system-info-label">Platform</div>
                <div class="system-info-value">{suite.system_info.get('platform', 'N/A')} {suite.system_info.get('platform_release', '')}</div>
            </div>
            <div class="system-info-item">
                <div class="system-info-label">Python Version</div>
                <div class="system-info-value">{suite.system_info.get('python_version', 'N/A').split()[0]}</div>
            </div>
            <div class="system-info-item">
                <div class="system-info-label">CPU Cores</div>
                <div class="system-info-value">{suite.system_info.get('cpu_count', 'N/A')}</div>
            </div>
            <div class="system-info-item">
                <div class="system-info-label">Memory</div>
                <div class="system-info-value">{suite.system_info.get('memory_total_gb', 0):.1f} GB</div>
            </div>
        </div>

        <div class="summary">
            <div class="summary-card">
                <div class="summary-value">{len(suite.results)}</div>
                <div class="summary-label">Total Benchmarks</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{len(categories)}</div>
                <div class="summary-label">Categories</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{sum(r.iterations for r in suite.results):,}</div>
                <div class="summary-label">Total Iterations</div>
            </div>
            <div class="summary-card">
                <div class="summary-value">{sum(r.total_time_ms for r in suite.results)/1000:.1f}s</div>
                <div class="summary-label">Total Time</div>
            </div>
        </div>
"""

    for category, results in sorted(categories.items()):
        # Sort by average time
        results = sorted(results, key=lambda r: r.avg_time_ms)

        html += f"""
        <div class="category">
            <h2 class="category-title">{category}</h2>
            <table>
                <thead>
                    <tr>
                        <th>Benchmark</th>
                        <th class="number">Iterations</th>
                        <th class="number">Avg (ms)</th>
                        <th class="number">Min (ms)</th>
                        <th class="number">Max (ms)</th>
                        <th class="number">Ops/sec</th>
                        <th class="number">Memory (MB)</th>
                    </tr>
                </thead>
                <tbody>
"""

        for r in results:
            # Determine speed class
            if r.avg_time_ms < 0.1:
                speed_class = "fast"
            elif r.avg_time_ms < 1.0:
                speed_class = "medium"
            else:
                speed_class = "slow"

            html += f"""
                    <tr>
                        <td>{r.name}</td>
                        <td class="number">{r.iterations:,}</td>
                        <td class="number {speed_class}">{r.avg_time_ms:.4f}</td>
                        <td class="number">{r.min_time_ms:.4f}</td>
                        <td class="number">{r.max_time_ms:.4f}</td>
                        <td class="number">{r.ops_per_second:,.0f}</td>
                        <td class="number">{r.memory_delta_mb:+.2f}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
            <div class="chart-container">
                <canvas id="chart-{category}"></canvas>
            </div>
        </div>
""".format(category=category.replace(" ", "_"))

    # Add chart scripts
    html += """
        <footer>
            <p>Generated by Quantum Benchmark Suite</p>
        </footer>
    </div>

    <script>
"""

    for category, results in sorted(categories.items()):
        results = sorted(results, key=lambda r: r.avg_time_ms)[:15]  # Top 15
        labels = [r.name for r in results]
        data = [r.ops_per_second for r in results]

        html += f"""
        new Chart(document.getElementById('chart-{category.replace(" ", "_")}'), {{
            type: 'bar',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [{{
                    label: 'Operations per second',
                    data: {json.dumps(data)},
                    backgroundColor: 'rgba(59, 130, 246, 0.5)',
                    borderColor: 'rgba(59, 130, 246, 1)',
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                indexAxis: 'y',
                plugins: {{
                    legend: {{ display: false }},
                    title: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        grid: {{ color: '#334155' }},
                        ticks: {{ color: '#94a3b8' }}
                    }},
                    y: {{
                        grid: {{ display: false }},
                        ticks: {{ color: '#e2e8f0' }}
                    }}
                }}
            }}
        }});
"""

    html += """
    </script>
</body>
</html>
"""

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"HTML report saved to: {filename}")
    return filename


def generate_markdown_report(suite: BenchmarkSuite, output_path: str = "benchmarks/results"):
    """Generate a Markdown report"""
    results_dir = Path(output_path)
    results_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = results_dir / f"report_{timestamp}.md"

    # Group results by category
    categories = {}
    for result in suite.results:
        if result.category not in categories:
            categories[result.category] = []
        categories[result.category].append(result)

    md = f"""# Quantum Framework Benchmark Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## System Information

| Property | Value |
|----------|-------|
| Platform | {suite.system_info.get('platform', 'N/A')} {suite.system_info.get('platform_release', '')} |
| Python | {suite.system_info.get('python_version', 'N/A').split()[0]} |
| CPU Cores | {suite.system_info.get('cpu_count', 'N/A')} |
| Memory | {suite.system_info.get('memory_total_gb', 0):.1f} GB |

## Summary

- **Total Benchmarks:** {len(suite.results)}
- **Categories:** {len(categories)}
- **Total Iterations:** {sum(r.iterations for r in suite.results):,}
- **Total Time:** {sum(r.total_time_ms for r in suite.results)/1000:.1f}s

"""

    for category, results in sorted(categories.items()):
        results = sorted(results, key=lambda r: r.avg_time_ms)

        md += f"""## {category.title()}

| Benchmark | Iterations | Avg (ms) | Min (ms) | Max (ms) | Ops/sec |
|-----------|------------|----------|----------|----------|---------|
"""

        for r in results:
            md += f"| {r.name} | {r.iterations:,} | {r.avg_time_ms:.4f} | {r.min_time_ms:.4f} | {r.max_time_ms:.4f} | {r.ops_per_second:,.0f} |\n"

        md += "\n"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(md)

    print(f"Markdown report saved to: {filename}")
    return filename


def main():
    parser = argparse.ArgumentParser(
        description="Quantum Framework Benchmark Runner"
    )
    parser.add_argument(
        "--category", "-c",
        help="Run specific category (core, database, json, python, etc.)"
    )
    parser.add_argument(
        "--report", "-r",
        choices=["html", "markdown", "json", "all"],
        help="Generate report in specified format"
    )
    parser.add_argument(
        "--quick", "-q",
        action="store_true",
        help="Quick run with fewer iterations"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available benchmarks"
    )

    args = parser.parse_args()

    # Load benchmarks
    load_benchmarks()

    if args.list:
        print("\nAvailable Benchmarks:\n")
        categories = {}
        for name, benchmark in Benchmark.registry.items():
            if benchmark.category not in categories:
                categories[benchmark.category] = []
            categories[benchmark.category].append(name)

        for category, names in sorted(categories.items()):
            print(f"  [{category}]")
            for name in sorted(names):
                print(f"    - {name}")
            print()
        return

    # Run benchmarks
    if args.category:
        suite = run_category(args.category, quick=args.quick)
    else:
        suite = run_all_benchmarks(quick=args.quick)

    # Print summary
    suite.print_summary()

    # Generate reports
    if args.report:
        if args.report in ["html", "all"]:
            generate_html_report(suite)
        if args.report in ["markdown", "all"]:
            generate_markdown_report(suite)
        if args.report in ["json", "all"]:
            suite.save_results()


if __name__ == "__main__":
    main()
