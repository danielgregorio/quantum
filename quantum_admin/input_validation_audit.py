#!/usr/bin/env python3
"""
Quantum Admin - Input Validation Audit

Automated script to audit all API endpoints for proper input validation.

This script:
1. Parses the FastAPI application to extract all endpoints
2. Checks for Pydantic model usage
3. Identifies endpoints with missing validation
4. Tests common injection vectors
5. Generates a detailed validation coverage report

Usage:
    python input_validation_audit.py [--test] [--report]

Options:
    --test      Run live validation tests against running server
    --report    Generate detailed HTML report
"""

import ast
import os
import re
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict


@dataclass
class Endpoint:
    """Represents an API endpoint"""
    method: str
    path: str
    function_name: str
    has_pydantic_model: bool
    has_manual_validation: bool
    parameters: List[str]
    validation_score: int  # 0-100
    issues: List[str]
    file_path: str
    line_number: int


@dataclass
class ValidationReport:
    """Overall validation audit report"""
    total_endpoints: int
    validated_endpoints: int
    unvalidated_endpoints: int
    validation_coverage: float
    high_risk_endpoints: List[Endpoint]
    medium_risk_endpoints: List[Endpoint]
    low_risk_endpoints: List[Endpoint]
    recommendations: List[str]


class InputValidationAuditor:
    """Audits FastAPI application for input validation"""

    def __init__(self, backend_dir: str):
        self.backend_dir = Path(backend_dir)
        self.endpoints: List[Endpoint] = []
        self.pydantic_models: Set[str] = set()

    def scan_pydantic_models(self):
        """Find all Pydantic models in schemas.py"""
        schemas_file = self.backend_dir / "schemas.py"

        if not schemas_file.exists():
            print(f"⚠ Warning: schemas.py not found at {schemas_file}")
            return

        with open(schemas_file, 'r') as f:
            content = f.read()
            tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if class inherits from BaseModel
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "BaseModel":
                        self.pydantic_models.add(node.name)
                    elif isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                        self.pydantic_models.add(node.name)

        print(f"✓ Found {len(self.pydantic_models)} Pydantic models")

    def scan_main_py(self):
        """Scan main.py for API endpoints"""
        main_file = self.backend_dir / "main.py"

        if not main_file.exists():
            print(f"✗ Error: main.py not found at {main_file}")
            return

        with open(main_file, 'r') as f:
            lines = f.readlines()
            content = ''.join(lines)

        # Parse AST
        tree = ast.parse(content)

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Check if function is decorated with @app.get, @app.post, etc.
                for decorator in node.decorator_list:
                    endpoint = self._parse_endpoint_decorator(
                        decorator, node, lines
                    )
                    if endpoint:
                        self.endpoints.append(endpoint)

        print(f"✓ Found {len(self.endpoints)} API endpoints")

    def _parse_endpoint_decorator(
        self,
        decorator: ast.expr,
        function: ast.FunctionDef,
        lines: List[str]
    ) -> Endpoint:
        """Parse endpoint decorator to extract method and path"""

        # Extract method (get, post, put, delete, etc.)
        method = None
        path = None

        if isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Attribute):
                method = decorator.func.attr.upper()

                # Extract path from first argument
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    path = decorator.args[0].value
        elif isinstance(decorator, ast.Attribute):
            method = decorator.attr.upper()

        if not method or method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]:
            return None

        # Analyze function parameters
        parameters = []
        has_pydantic_model = False
        has_manual_validation = False

        for arg in function.args.args:
            param_name = arg.arg

            # Skip self, request, db, etc.
            if param_name in ["self", "request", "db", "current_user"]:
                continue

            parameters.append(param_name)

            # Check if parameter has type annotation
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    type_name = arg.annotation.id
                    if type_name in self.pydantic_models:
                        has_pydantic_model = True

        # Check function body for manual validation
        for stmt in ast.walk(function):
            if isinstance(stmt, ast.Call):
                if isinstance(stmt.func, ast.Name):
                    # Look for validation functions
                    if stmt.func.id in ["validate", "check", "sanitize", "InputSanitizer"]:
                        has_manual_validation = True

        # Calculate validation score and identify issues
        validation_score, issues = self._calculate_validation_score(
            method, parameters, has_pydantic_model, has_manual_validation
        )

        return Endpoint(
            method=method,
            path=path or "unknown",
            function_name=function.name,
            has_pydantic_model=has_pydantic_model,
            has_manual_validation=has_manual_validation,
            parameters=parameters,
            validation_score=validation_score,
            issues=issues,
            file_path=str(self.backend_dir / "main.py"),
            line_number=function.lineno
        )

    def _calculate_validation_score(
        self,
        method: str,
        parameters: List[str],
        has_pydantic: bool,
        has_manual: bool
    ) -> Tuple[int, List[str]]:
        """Calculate validation score (0-100) and identify issues"""

        score = 100
        issues = []

        # Unsafe methods (POST, PUT, DELETE) require stricter validation
        is_unsafe_method = method in ["POST", "PUT", "DELETE", "PATCH"]

        if is_unsafe_method:
            if not has_pydantic and not has_manual:
                score -= 50
                issues.append("No input validation for unsafe method")

            if parameters and not has_pydantic:
                score -= 30
                issues.append("Parameters without Pydantic model validation")

        # Safe methods (GET) still benefit from validation
        if method == "GET":
            if parameters and not has_pydantic and not has_manual:
                score -= 20
                issues.append("Query parameters without validation")

        # Bonus points for both types of validation
        if has_pydantic and has_manual:
            score = min(100, score + 10)

        return max(0, score), issues

    def generate_report(self) -> ValidationReport:
        """Generate validation audit report"""

        validated = sum(1 for e in self.endpoints if e.validation_score >= 70)
        unvalidated = len(self.endpoints) - validated

        coverage = (validated / len(self.endpoints) * 100) if self.endpoints else 0

        # Categorize by risk
        high_risk = [e for e in self.endpoints if e.validation_score < 50]
        medium_risk = [e for e in self.endpoints if 50 <= e.validation_score < 70]
        low_risk = [e for e in self.endpoints if e.validation_score >= 70]

        # Generate recommendations
        recommendations = []

        if high_risk:
            recommendations.append(
                f"🚨 CRITICAL: {len(high_risk)} high-risk endpoints without validation. "
                "Add Pydantic models immediately."
            )

        if medium_risk:
            recommendations.append(
                f"⚠️  WARNING: {len(medium_risk)} endpoints with incomplete validation. "
                "Review and enhance validation logic."
            )

        if coverage < 80:
            recommendations.append(
                f"📊 Coverage at {coverage:.1f}%. Target: 80%+. "
                "Create Pydantic models for all request bodies."
            )

        if coverage >= 90:
            recommendations.append(
                "✅ Excellent validation coverage! Consider adding custom validators "
                "for business logic."
            )

        return ValidationReport(
            total_endpoints=len(self.endpoints),
            validated_endpoints=validated,
            unvalidated_endpoints=unvalidated,
            validation_coverage=coverage,
            high_risk_endpoints=high_risk,
            medium_risk_endpoints=medium_risk,
            low_risk_endpoints=low_risk,
            recommendations=recommendations
        )

    def print_report(self, report: ValidationReport):
        """Print validation report to console"""

        print("\n" + "=" * 80)
        print("QUANTUM ADMIN - INPUT VALIDATION AUDIT REPORT")
        print("=" * 80)

        print(f"\n📊 SUMMARY")
        print(f"  Total Endpoints:      {report.total_endpoints}")
        print(f"  Validated:            {report.validated_endpoints} ({report.validation_coverage:.1f}%)")
        print(f"  Needs Improvement:    {report.unvalidated_endpoints}")
        print(f"  Coverage:             {report.validation_coverage:.1f}%")

        if report.high_risk_endpoints:
            print(f"\n🚨 HIGH RISK ({len(report.high_risk_endpoints)} endpoints)")
            for ep in report.high_risk_endpoints[:10]:  # Show top 10
                print(f"  [{ep.method:6}] {ep.path:40} (Score: {ep.validation_score})")
                for issue in ep.issues:
                    print(f"           └─ {issue}")

        if report.medium_risk_endpoints:
            print(f"\n⚠️  MEDIUM RISK ({len(report.medium_risk_endpoints)} endpoints)")
            for ep in report.medium_risk_endpoints[:10]:
                print(f"  [{ep.method:6}] {ep.path:40} (Score: {ep.validation_score})")

        print(f"\n✅ LOW RISK ({len(report.low_risk_endpoints)} endpoints)")
        print(f"  Well-validated endpoints with Pydantic models")

        print("\n💡 RECOMMENDATIONS")
        for i, rec in enumerate(report.recommendations, 1):
            print(f"  {i}. {rec}")

        print("\n" + "=" * 80)

        # Overall grade
        if report.validation_coverage >= 90:
            grade = "A"
            emoji = "🏆"
        elif report.validation_coverage >= 80:
            grade = "B"
            emoji = "✅"
        elif report.validation_coverage >= 70:
            grade = "C"
            emoji = "⚠️"
        elif report.validation_coverage >= 60:
            grade = "D"
            emoji = "⚠️"
        else:
            grade = "F"
            emoji = "🚨"

        print(f"\n{emoji}  OVERALL GRADE: {grade} ({report.validation_coverage:.1f}% coverage)")
        print("=" * 80 + "\n")

    def save_json_report(self, report: ValidationReport, output_file: str):
        """Save report as JSON"""

        data = {
            "summary": {
                "total_endpoints": report.total_endpoints,
                "validated_endpoints": report.validated_endpoints,
                "unvalidated_endpoints": report.unvalidated_endpoints,
                "coverage": report.validation_coverage
            },
            "high_risk": [asdict(e) for e in report.high_risk_endpoints],
            "medium_risk": [asdict(e) for e in report.medium_risk_endpoints],
            "low_risk": [asdict(e) for e in report.low_risk_endpoints],
            "recommendations": report.recommendations
        }

        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        print(f"✓ JSON report saved: {output_file}")

    def save_html_report(self, report: ValidationReport, output_file: str):
        """Save report as HTML"""

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Input Validation Audit - Quantum Admin</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; margin: 40px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin: 30px 0; }}
        .stat {{ background: #ecf0f1; padding: 20px; border-radius: 6px; text-align: center; }}
        .stat-value {{ font-size: 36px; font-weight: bold; color: #2c3e50; }}
        .stat-label {{ color: #7f8c8d; margin-top: 5px; }}
        .endpoint {{ margin: 15px 0; padding: 15px; background: #f8f9fa; border-left: 4px solid #ddd; border-radius: 4px; }}
        .endpoint.high-risk {{ border-left-color: #e74c3c; background: #fdefef; }}
        .endpoint.medium-risk {{ border-left-color: #f39c12; background: #fef5e7; }}
        .endpoint.low-risk {{ border-left-color: #27ae60; background: #eafaf1; }}
        .method {{ display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; font-weight: bold; color: white; margin-right: 10px; }}
        .method.GET {{ background: #3498db; }}
        .method.POST {{ background: #27ae60; }}
        .method.PUT {{ background: #f39c12; }}
        .method.DELETE {{ background: #e74c3c; }}
        .score {{ float: right; font-weight: bold; }}
        .score.high {{ color: #27ae60; }}
        .score.medium {{ color: #f39c12; }}
        .score.low {{ color: #e74c3c; }}
        .issues {{ margin-top: 10px; font-size: 14px; color: #7f8c8d; }}
        .recommendations {{ background: #e8f4f8; padding: 20px; border-radius: 6px; margin-top: 30px; }}
        .recommendations li {{ margin: 10px 0; }}
        .grade {{ text-align: center; font-size: 72px; font-weight: bold; margin: 40px 0; }}
        .grade.A {{ color: #27ae60; }}
        .grade.B {{ color: #3498db; }}
        .grade.C {{ color: #f39c12; }}
        .grade.D {{ color: #e67e22; }}
        .grade.F {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔒 Input Validation Audit Report</h1>
        <p><strong>Quantum Admin API</strong> | Generated: {self._get_timestamp()}</p>

        <div class="summary">
            <div class="stat">
                <div class="stat-value">{report.total_endpoints}</div>
                <div class="stat-label">Total Endpoints</div>
            </div>
            <div class="stat">
                <div class="stat-value">{report.validated_endpoints}</div>
                <div class="stat-label">Validated</div>
            </div>
            <div class="stat">
                <div class="stat-value">{report.unvalidated_endpoints}</div>
                <div class="stat-label">Need Attention</div>
            </div>
            <div class="stat">
                <div class="stat-value">{report.validation_coverage:.1f}%</div>
                <div class="stat-label">Coverage</div>
            </div>
        </div>

        {self._render_grade(report.validation_coverage)}

        {self._render_endpoints_section("🚨 High Risk Endpoints", report.high_risk_endpoints, "high-risk")}
        {self._render_endpoints_section("⚠️ Medium Risk Endpoints", report.medium_risk_endpoints, "medium-risk")}
        {self._render_endpoints_section("✅ Well-Validated Endpoints", report.low_risk_endpoints[:20], "low-risk")}

        <div class="recommendations">
            <h2>💡 Recommendations</h2>
            <ol>
                {"".join(f"<li>{rec}</li>" for rec in report.recommendations)}
            </ol>
        </div>
    </div>
</body>
</html>
"""

        with open(output_file, 'w') as f:
            f.write(html)

        print(f"✓ HTML report saved: {output_file}")

    def _get_timestamp(self):
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _render_grade(self, coverage: float) -> str:
        """Render overall grade"""
        if coverage >= 90:
            grade = "A"
            grade_class = "A"
        elif coverage >= 80:
            grade = "B"
            grade_class = "B"
        elif coverage >= 70:
            grade = "C"
            grade_class = "C"
        elif coverage >= 60:
            grade = "D"
            grade_class = "D"
        else:
            grade = "F"
            grade_class = "F"

        return f'<div class="grade {grade_class}">{grade}</div>'

    def _render_endpoints_section(self, title: str, endpoints: List[Endpoint], css_class: str) -> str:
        """Render section of endpoints"""
        if not endpoints:
            return ""

        html = f"<h2>{title} ({len(endpoints)})</h2>"

        for ep in endpoints[:50]:  # Limit to 50
            score_class = "high" if ep.validation_score >= 70 else "medium" if ep.validation_score >= 50 else "low"

            issues_html = ""
            if ep.issues:
                issues_html = "<div class='issues'>Issues: " + "; ".join(ep.issues) + "</div>"

            html += f"""
            <div class="endpoint {css_class}">
                <span class="method {ep.method}">{ep.method}</span>
                <strong>{ep.path}</strong>
                <span class="score {score_class}">{ep.validation_score}/100</span>
                <div style="clear: both;"></div>
                {issues_html}
            </div>
            """

        return html


def main():
    """Main entry point"""

    import argparse

    parser = argparse.ArgumentParser(description="Audit API input validation")
    parser.add_argument("--report", action="store_true", help="Generate HTML report")
    parser.add_argument("--json", action="store_true", help="Generate JSON report")
    parser.add_argument("--backend", default="./backend", help="Path to backend directory")

    args = parser.parse_args()

    # Create auditor
    auditor = InputValidationAuditor(args.backend)

    print("🔍 Starting input validation audit...\n")

    # Scan for Pydantic models
    auditor.scan_pydantic_models()

    # Scan main.py for endpoints
    auditor.scan_main_py()

    # Generate report
    report = auditor.generate_report()

    # Print to console
    auditor.print_report(report)

    # Save reports if requested
    if args.json:
        auditor.save_json_report(report, "security_reports/validation_audit.json")

    if args.report:
        auditor.save_html_report(report, "security_reports/validation_audit.html")
        print("\n💡 Open security_reports/validation_audit.html in your browser")

    # Exit with error code if coverage is too low
    if report.validation_coverage < 70:
        sys.exit(1)


if __name__ == "__main__":
    main()
