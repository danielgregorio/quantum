#!/bin/bash
# ============================================================================
# Quantum Admin - Security Audit Script
# ============================================================================
# Automated security scanning and vulnerability assessment
#
# Usage:
#   ./security_audit.sh [mode]
#
# Modes:
#   quick    - Fast security checks (default)
#   full     - Comprehensive security audit
#   deps     - Only dependency vulnerability scan
#   code     - Only code security scan
#   report   - Generate detailed HTML report
#
# Requirements:
#   - bandit (pip install bandit)
#   - safety (pip install safety)
#   - Optional: semgrep (for advanced SAST)
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
REPORTS_DIR="$SCRIPT_DIR/security_reports"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# Mode
MODE="${1:-quick}"

# ============================================================================
# Helper Functions
# ============================================================================

print_header() {
    echo ""
    echo -e "${BLUE}============================================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}============================================================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${PURPLE}ℹ $1${NC}"
}

# ============================================================================
# Check Dependencies
# ============================================================================

check_tools() {
    print_header "Checking Security Tools"

    local missing_tools=()

    if ! command -v bandit &> /dev/null; then
        print_warning "bandit not found"
        missing_tools+=("bandit")
    else
        print_success "bandit: $(bandit --version 2>&1 | head -1)"
    fi

    if ! command -v safety &> /dev/null; then
        print_warning "safety not found"
        missing_tools+=("safety")
    else
        print_success "safety: $(safety --version 2>&1 | head -1)"
    fi

    if ! command -v semgrep &> /dev/null; then
        print_info "semgrep not found (optional)"
    else
        print_success "semgrep: $(semgrep --version 2>&1 | head -1)"
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        print_error "Missing required tools: ${missing_tools[*]}"
        echo ""
        echo "Install with:"
        echo "  pip install ${missing_tools[*]}"
        exit 1
    fi

    print_success "All required tools installed"
}

# ============================================================================
# Dependency Vulnerability Scanning
# ============================================================================

scan_dependencies() {
    print_header "Dependency Vulnerability Scan (Safety)"

    cd "$SCRIPT_DIR"

    print_info "Scanning Python dependencies for known vulnerabilities..."

    # Create reports directory
    mkdir -p "$REPORTS_DIR"

    # Run safety check
    if safety check --json --output "$REPORTS_DIR/safety_${TIMESTAMP}.json" 2>&1 | tee "$REPORTS_DIR/safety_${TIMESTAMP}.txt"; then
        print_success "No known vulnerabilities found in dependencies"
    else
        print_warning "Vulnerabilities found! Check: $REPORTS_DIR/safety_${TIMESTAMP}.txt"
    fi

    # Also check for outdated packages
    print_info "Checking for outdated packages..."
    pip list --outdated > "$REPORTS_DIR/outdated_packages_${TIMESTAMP}.txt" 2>&1 || true
    print_success "Outdated packages report: $REPORTS_DIR/outdated_packages_${TIMESTAMP}.txt"
}

# ============================================================================
# Code Security Scanning (SAST)
# ============================================================================

scan_code() {
    print_header "Static Application Security Testing (Bandit)"

    cd "$SCRIPT_DIR"

    print_info "Scanning Python code for security issues..."

    # Create reports directory
    mkdir -p "$REPORTS_DIR"

    # Run bandit with different severity levels
    local bandit_exit_code=0

    # Full scan with JSON output
    bandit -r "$BACKEND_DIR" \
        -f json \
        -o "$REPORTS_DIR/bandit_${TIMESTAMP}.json" \
        --severity-level medium \
        --confidence-level medium \
        --exclude "$BACKEND_DIR/tests" \
        || bandit_exit_code=$?

    # Human-readable output
    bandit -r "$BACKEND_DIR" \
        -f txt \
        -o "$REPORTS_DIR/bandit_${TIMESTAMP}.txt" \
        --severity-level medium \
        --confidence-level medium \
        --exclude "$BACKEND_DIR/tests" \
        || true

    # HTML report
    bandit -r "$BACKEND_DIR" \
        -f html \
        -o "$REPORTS_DIR/bandit_${TIMESTAMP}.html" \
        --severity-level medium \
        --confidence-level medium \
        --exclude "$BACKEND_DIR/tests" \
        || true

    if [ $bandit_exit_code -eq 0 ]; then
        print_success "No security issues found by Bandit"
    else
        print_warning "Security issues found! Check: $REPORTS_DIR/bandit_${TIMESTAMP}.html"
    fi

    # Print summary
    print_info "Reports generated:"
    echo "  - JSON: $REPORTS_DIR/bandit_${TIMESTAMP}.json"
    echo "  - Text: $REPORTS_DIR/bandit_${TIMESTAMP}.txt"
    echo "  - HTML: $REPORTS_DIR/bandit_${TIMESTAMP}.html"
}

# ============================================================================
# Advanced SAST (Semgrep)
# ============================================================================

scan_semgrep() {
    if ! command -v semgrep &> /dev/null; then
        print_info "Skipping semgrep scan (not installed)"
        return
    fi

    print_header "Advanced SAST (Semgrep)"

    cd "$SCRIPT_DIR"

    print_info "Running semgrep security rules..."

    mkdir -p "$REPORTS_DIR"

    # Run semgrep with auto config (uses community rules)
    semgrep --config=auto \
        --json \
        --output "$REPORTS_DIR/semgrep_${TIMESTAMP}.json" \
        "$BACKEND_DIR" \
        || true

    # HTML report
    semgrep --config=auto \
        --sarif \
        --output "$REPORTS_DIR/semgrep_${TIMESTAMP}.sarif" \
        "$BACKEND_DIR" \
        || true

    print_success "Semgrep scan complete: $REPORTS_DIR/semgrep_${TIMESTAMP}.json"
}

# ============================================================================
# OWASP Top 10 Checklist
# ============================================================================

owasp_checklist() {
    print_header "OWASP Top 10 Security Checklist"

    local checks_passed=0
    local checks_total=10

    # A01:2021 – Broken Access Control
    print_info "[1/10] Checking for Broken Access Control..."
    if grep -r "@require_role\|@require_permission" "$BACKEND_DIR" > /dev/null; then
        print_success "Role-based access control found"
        ((checks_passed++))
    else
        print_warning "No RBAC decorators found - verify access control"
    fi

    # A02:2021 – Cryptographic Failures
    print_info "[2/10] Checking for Cryptographic Failures..."
    if grep -r "bcrypt\|hash_password\|passlib" "$BACKEND_DIR" > /dev/null; then
        print_success "Password hashing implementation found"
        ((checks_passed++))
    else
        print_warning "No password hashing found - verify cryptography"
    fi

    # A03:2021 – Injection
    print_info "[3/10] Checking for Injection vulnerabilities..."
    if grep -r "sqlalchemy\|pydantic" "$BACKEND_DIR" > /dev/null; then
        print_success "ORM and validation frameworks found (helps prevent injection)"
        ((checks_passed++))
    else
        print_warning "Verify SQL injection protection"
    fi

    # A04:2021 – Insecure Design
    print_info "[4/10] Checking for Insecure Design..."
    if [ -f "$BACKEND_DIR/security.py" ]; then
        print_success "Security module exists"
        ((checks_passed++))
    else
        print_warning "No dedicated security module found"
    fi

    # A05:2021 – Security Misconfiguration
    print_info "[5/10] Checking for Security Misconfiguration..."
    if grep -r "CORS\|SecurityHeadersMiddleware" "$BACKEND_DIR" > /dev/null; then
        print_success "Security headers and CORS configuration found"
        ((checks_passed++))
    else
        print_warning "Verify security configuration"
    fi

    # A06:2021 – Vulnerable and Outdated Components
    print_info "[6/10] Checking for Vulnerable Components..."
    # This is covered by safety check
    print_success "Covered by Safety scan"
    ((checks_passed++))

    # A07:2021 – Identification and Authentication Failures
    print_info "[7/10] Checking for Authentication Failures..."
    if grep -r "JWT\|python-jose\|get_current_user" "$BACKEND_DIR" > /dev/null; then
        print_success "JWT authentication implementation found"
        ((checks_passed++))
    else
        print_warning "Verify authentication implementation"
    fi

    # A08:2021 – Software and Data Integrity Failures
    print_info "[8/10] Checking for Data Integrity..."
    if grep -r "pydantic\|BaseModel" "$BACKEND_DIR" > /dev/null; then
        print_success "Data validation with Pydantic found"
        ((checks_passed++))
    else
        print_warning "Verify data integrity checks"
    fi

    # A09:2021 – Security Logging and Monitoring Failures
    print_info "[9/10] Checking for Logging & Monitoring..."
    if grep -r "logger\|logging\|prometheus" "$BACKEND_DIR" > /dev/null; then
        print_success "Logging and monitoring implementation found"
        ((checks_passed++))
    else
        print_warning "Verify logging and monitoring"
    fi

    # A10:2021 – Server-Side Request Forgery (SSRF)
    print_info "[10/10] Checking for SSRF protection..."
    if grep -r "validate_url\|urlparse" "$BACKEND_DIR" > /dev/null; then
        print_success "URL validation found"
        ((checks_passed++))
    else
        print_warning "Verify SSRF protection"
    fi

    echo ""
    print_header "OWASP Top 10 Checklist Results"
    echo -e "${GREEN}Passed: $checks_passed / $checks_total${NC}"

    if [ $checks_passed -eq $checks_total ]; then
        print_success "All OWASP Top 10 checks passed!"
    elif [ $checks_passed -ge 7 ]; then
        print_warning "Good security posture, but some items need attention"
    else
        print_error "Security improvements needed"
    fi
}

# ============================================================================
# Secret Detection
# ============================================================================

detect_secrets() {
    print_header "Secret Detection"

    print_info "Scanning for hardcoded secrets..."

    local secrets_found=0

    # Common secret patterns
    local patterns=(
        "password\s*=\s*['\"][^'\"]*['\"]"
        "api_key\s*=\s*['\"][^'\"]*['\"]"
        "secret_key\s*=\s*['\"][^'\"]*['\"]"
        "aws_access_key_id\s*=\s*['\"][^'\"]*['\"]"
        "private_key"
    )

    for pattern in "${patterns[@]}"; do
        if grep -rn -E "$pattern" "$BACKEND_DIR" --exclude-dir=tests --exclude="*.pyc" | grep -v "os.getenv\|settings\|config" > "$REPORTS_DIR/secrets_${TIMESTAMP}.txt"; then
            print_warning "Potential hardcoded secrets found - check $REPORTS_DIR/secrets_${TIMESTAMP}.txt"
            ((secrets_found++))
        fi
    done

    if [ $secrets_found -eq 0 ]; then
        print_success "No hardcoded secrets detected"
    else
        print_error "Found $secrets_found potential secret patterns"
    fi
}

# ============================================================================
# Generate Final Report
# ============================================================================

generate_report() {
    print_header "Generating Security Audit Report"

    local report_file="$REPORTS_DIR/security_audit_report_${TIMESTAMP}.md"

    cat > "$report_file" << EOF
# Quantum Admin - Security Audit Report

**Date:** $(date)
**Mode:** $MODE
**Auditor:** $(whoami)

---

## Executive Summary

This report contains the results of automated security scanning performed on Quantum Admin.

## Tools Used

- **Bandit:** Static Application Security Testing (SAST) for Python
- **Safety:** Dependency vulnerability scanning
- **Custom:** OWASP Top 10 checklist
- **Custom:** Secret detection

## Reports Generated

### Dependency Vulnerabilities
- JSON: \`safety_${TIMESTAMP}.json\`
- Text: \`safety_${TIMESTAMP}.txt\`

### Code Security Issues
- JSON: \`bandit_${TIMESTAMP}.json\`
- Text: \`bandit_${TIMESTAMP}.txt\`
- HTML: \`bandit_${TIMESTAMP}.html\`

### OWASP Top 10
- See console output above

### Secret Detection
- Text: \`secrets_${TIMESTAMP}.txt\`

## Recommendations

1. **Review all findings** in the generated reports
2. **Prioritize HIGH severity issues** for immediate remediation
3. **Update vulnerable dependencies** identified by Safety
4. **Fix security issues** identified by Bandit
5. **Implement missing OWASP controls** from checklist
6. **Remove any hardcoded secrets** and use environment variables

## Next Steps

1. Address HIGH severity issues immediately
2. Create GitHub issues for MEDIUM severity items
3. Schedule security audit reviews monthly
4. Integrate security scanning into CI/CD pipeline

---

**All reports saved to:** \`$REPORTS_DIR/\`

EOF

    print_success "Security audit report generated: $report_file"

    # Open HTML report if available
    if [ -f "$REPORTS_DIR/bandit_${TIMESTAMP}.html" ]; then
        print_info "To view detailed HTML report:"
        echo "  open $REPORTS_DIR/bandit_${TIMESTAMP}.html"
    fi
}

# ============================================================================
# Main Execution
# ============================================================================

main() {
    clear
    print_header "🔒 Quantum Admin Security Audit"

    echo "Mode: $MODE"
    echo "Reports Directory: $REPORTS_DIR"
    echo ""

    # Check tools
    check_tools

    case $MODE in
        quick)
            scan_dependencies
            scan_code
            owasp_checklist
            ;;

        full)
            scan_dependencies
            scan_code
            scan_semgrep
            owasp_checklist
            detect_secrets
            generate_report
            ;;

        deps)
            scan_dependencies
            ;;

        code)
            scan_code
            owasp_checklist
            ;;

        report)
            generate_report
            ;;

        *)
            print_error "Unknown mode: $MODE"
            echo ""
            echo "Usage: $0 [quick|full|deps|code|report]"
            exit 1
            ;;
    esac

    print_header "Security Audit Complete!"
    print_success "All reports saved to: $REPORTS_DIR"

    echo ""
    echo "Next steps:"
    echo "  1. Review reports in: $REPORTS_DIR"
    echo "  2. Address HIGH severity issues"
    echo "  3. Run full audit: ./security_audit.sh full"
    echo "  4. Integrate into CI/CD pipeline"
}

# Run main
main
