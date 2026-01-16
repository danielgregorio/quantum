#!/bin/bash
###############################################################################
# Quantum Admin - Native Shell Installer
# Enterprise-grade installation for Linux & macOS
###############################################################################

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
WHITE='\033[1;37m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Symbols
CHECK="${GREEN}✓${NC}"
CROSS="${RED}✗${NC}"
ARROW="${CYAN}→${NC}"
INFO="${BLUE}ℹ${NC}"
WARN="${YELLOW}⚠${NC}"

###############################################################################
# ASCII Art
###############################################################################

show_banner() {
    clear
    echo -e "${CYAN}${BOLD}"
    cat << "EOF"
   ██████╗ ██╗   ██╗ █████╗ ███╗   ██╗████████╗██╗   ██╗███╗   ███╗
  ██╔═══██╗██║   ██║██╔══██╗████╗  ██║╚══██╔══╝██║   ██║████╗ ████║
  ██║   ██║██║   ██║███████║██╔██╗ ██║   ██║   ██║   ██║██╔████╔██║
  ██║▄▄ ██║██║   ██║██╔══██║██║╚██╗██║   ██║   ██║   ██║██║╚██╔╝██║
  ╚██████╔╝╚██████╔╝██║  ██║██║ ╚████║   ██║   ╚██████╔╝██║ ╚═╝ ██║
   ╚══▀▀═╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝   ╚═╝    ╚═════╝ ╚═╝     ╚═╝
EOF
    echo -e "${NC}"
    echo -e "${WHITE}${BOLD}           A D M I N   -   N A T I V E   I N S T A L L E R${NC}"
    echo -e "${BLUE}              Enterprise Administration Interface${NC}"
    echo ""
    echo -e "${YELLOW}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

###############################################################################
# System Detection
###############################################################################

detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        if [ -f /etc/debian_version ]; then
            DISTRO="debian"
        elif [ -f /etc/redhat-release ]; then
            DISTRO="redhat"
        elif [ -f /etc/arch-release ]; then
            DISTRO="arch"
        else
            DISTRO="unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        DISTRO="macos"
    else
        OS="unknown"
        DISTRO="unknown"
    fi
}

###############################################################################
# Dependency Checking
###############################################################################

check_python() {
    echo -e "${ARROW} Checking Python installation..."

    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

        if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
            echo -e "  ${CHECK} Python ${PYTHON_VERSION} ${GREEN}(OK)${NC}"
            PYTHON_CMD="python3"
            return 0
        else
            echo -e "  ${WARN} Python ${PYTHON_VERSION} ${YELLOW}(Need 3.9+)${NC}"
            return 1
        fi
    else
        echo -e "  ${CROSS} Python 3 ${RED}not found${NC}"
        return 1
    fi
}

install_python() {
    echo -e "\n${YELLOW}Python 3.9+ is required but not found.${NC}"
    read -p "Would you like to install Python now? (y/N) " -n 1 -r
    echo

    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Installation cancelled.${NC}"
        exit 1
    fi

    echo -e "\n${ARROW} Installing Python..."

    case $DISTRO in
        debian)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
            ;;
        redhat)
            sudo yum install -y python3 python3-pip
            ;;
        arch)
            sudo pacman -S python python-pip
            ;;
        macos)
            if command -v brew &> /dev/null; then
                brew install python@3.11
            else
                echo -e "${RED}Homebrew not found. Please install from https://brew.sh${NC}"
                exit 1
            fi
            ;;
        *)
            echo -e "${RED}Unsupported distribution. Please install Python 3.9+ manually.${NC}"
            exit 1
            ;;
    esac

    echo -e "${CHECK} Python installed successfully"
}

check_git() {
    echo -e "${ARROW} Checking Git installation..."
    if command -v git &> /dev/null; then
        GIT_VERSION=$(git --version | awk '{print $3}')
        echo -e "  ${CHECK} Git ${GIT_VERSION} ${GREEN}(OK)${NC}"
        return 0
    else
        echo -e "  ${INFO} Git ${YELLOW}not found (optional)${NC}"
        return 0
    fi
}

check_docker() {
    echo -e "${ARROW} Checking Docker installation..."
    if command -v docker &> /dev/null; then
        if docker ps &> /dev/null; then
            DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
            echo -e "  ${CHECK} Docker ${DOCKER_VERSION} ${GREEN}(running)${NC}"
            return 0
        else
            echo -e "  ${WARN} Docker ${YELLOW}(installed but not running)${NC}"
            return 1
        fi
    else
        echo -e "  ${INFO} Docker ${YELLOW}not found (optional)${NC}"
        return 0
    fi
}

check_ports() {
    echo -e "${ARROW} Checking port availability..."

    for port in 8000 5432 6379; do
        if lsof -i :$port &> /dev/null || netstat -an | grep ":$port " &> /dev/null 2>&1; then
            echo -e "  ${WARN} Port $port ${YELLOW}in use${NC}"
        else
            echo -e "  ${CHECK} Port $port ${GREEN}available${NC}"
        fi
    done
}

###############################################################################
# System Verification
###############################################################################

verify_system() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  STEP 1: System Verification${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    detect_os
    echo -e "${INFO} Operating System: ${BOLD}$OS${NC} ($DISTRO)"
    echo ""

    if ! check_python; then
        install_python
    fi

    check_git
    check_docker
    check_ports

    echo -e "\n${CHECK} ${GREEN}System verification complete!${NC}"
    sleep 1
}

###############################################################################
# Installation Menu
###############################################################################

show_menu() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  STEP 2: Installation Method${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    echo -e "${BOLD}Choose installation method:${NC}\n"
    echo -e "  ${CYAN}1)${NC} ${BOLD}Interactive Installer${NC} ${GREEN}(Recommended)${NC}"
    echo -e "     Full wizard with step-by-step configuration"
    echo ""
    echo -e "  ${CYAN}2)${NC} ${BOLD}Quick Install${NC}"
    echo -e "     Auto-install with default settings (SQLite, dev mode)"
    echo ""
    echo -e "  ${CYAN}3)${NC} ${BOLD}Docker Compose${NC}"
    echo -e "     Full stack with PostgreSQL and Redis containers"
    echo ""
    echo -e "  ${CYAN}4)${NC} ${BOLD}Manual Setup${NC}"
    echo -e "     Install dependencies only, configure manually"
    echo ""
    echo -e "  ${CYAN}q)${NC} Quit\n"
}

###############################################################################
# Installation Methods
###############################################################################

interactive_install() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  Interactive Installation${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    echo -e "${ARROW} Launching interactive installer...\n"

    # Install Rich if needed
    $PYTHON_CMD -c "import rich" 2>/dev/null || {
        echo -e "${INFO} Installing Rich terminal library..."
        $PYTHON_CMD -m pip install rich --quiet
    }

    # Run Python installer
    $PYTHON_CMD install.py
}

quick_install() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  Quick Installation${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    # Install dependencies
    echo -e "${ARROW} Installing Python dependencies..."
    cd quantum_admin
    $PYTHON_CMD -m pip install -r requirements.txt --quiet
    cd ..

    # Create default .env
    echo -e "${ARROW} Creating configuration file..."
    cat > .env << EOF
DATABASE_URL=sqlite:///quantum_admin.db
JWT_SECRET_KEY=$(openssl rand -hex 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_hex(32))")
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@quantum.local
REDIS_ENABLED=false
DEBUG=true
EOF

    echo -e "\n${CHECK} ${GREEN}Quick installation complete!${NC}"
    show_completion
}

docker_install() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  Docker Compose Installation${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    if ! command -v docker &> /dev/null; then
        echo -e "${CROSS} Docker not found. Please install Docker first."
        return 1
    fi

    echo -e "${ARROW} Starting Docker Compose stack..."
    docker-compose up -d

    echo -e "\n${CHECK} ${GREEN}Docker stack started!${NC}"
    echo -e "\n${BOLD}Services running:${NC}"
    docker-compose ps

    show_completion
}

manual_install() {
    echo -e "\n${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}${BOLD}  Manual Installation${NC}"
    echo -e "${CYAN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    echo -e "${ARROW} Installing Python dependencies..."
    cd quantum_admin
    $PYTHON_CMD -m pip install -r requirements.txt
    cd ..

    echo -e "\n${CHECK} ${GREEN}Dependencies installed!${NC}"
    echo -e "\n${BOLD}Next steps:${NC}"
    echo -e "  1. Copy .env.example to .env"
    echo -e "  2. Edit .env with your configuration"
    echo -e "  3. Run: python quantum-cli.py start"
}

###############################################################################
# Completion
###############################################################################

show_completion() {
    echo -e "\n${GREEN}${BOLD}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║               🎉  INSTALLATION COMPLETE!  🎉                     ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"

    echo -e "\n${BOLD}Next Steps:${NC}\n"
    echo -e "  ${CYAN}1.${NC} Start the server:"
    echo -e "     ${YELLOW}python quantum-cli.py start${NC}"
    echo ""
    echo -e "  ${CYAN}2.${NC} Access the admin interface:"
    echo -e "     ${YELLOW}http://localhost:8000/static/login.html${NC}"
    echo ""
    echo -e "  ${CYAN}3.${NC} Default credentials:"
    echo -e "     ${YELLOW}Username: admin${NC}"
    echo -e "     ${YELLOW}Password: admin123${NC}"
    echo ""
    echo -e "${BOLD}Useful Commands:${NC}\n"
    echo -e "  ${CYAN}python quantum-cli.py status${NC}   - Check server status"
    echo -e "  ${CYAN}python quantum-cli.py logs${NC}     - View logs"
    echo -e "  ${CYAN}python quantum-cli.py stop${NC}     - Stop server"
    echo ""
    echo -e "${BOLD}Documentation:${NC}"
    echo -e "  ${CYAN}http://localhost:8000/docs${NC}     - API Documentation"
    echo ""
    echo -e "${BLUE}Thank you for choosing Quantum Admin!${NC}\n"
}

###############################################################################
# Main
###############################################################################

main() {
    show_banner

    echo -e "${WHITE}${BOLD}Welcome to Quantum Admin Installer!${NC}\n"
    echo -e "This script will help you install and configure Quantum Admin."
    echo ""

    read -p "$(echo -e ${BOLD}Ready to begin? [Y/n]:${NC} )" -n 1 -r
    echo

    if [[ $REPLY =~ ^[Nn]$ ]]; then
        echo -e "\n${YELLOW}Installation cancelled.${NC}"
        exit 0
    fi

    verify_system

    while true; do
        show_menu
        read -p "$(echo -e ${BOLD}Select option [1-4, q]:${NC} )" -n 1 -r choice
        echo

        case $choice in
            1)
                interactive_install
                break
                ;;
            2)
                quick_install
                break
                ;;
            3)
                docker_install
                break
                ;;
            4)
                manual_install
                break
                ;;
            q|Q)
                echo -e "\n${YELLOW}Installation cancelled.${NC}"
                exit 0
                ;;
            *)
                echo -e "\n${RED}Invalid option. Please try again.${NC}"
                sleep 1
                ;;
        esac
    done
}

# Run main function
main "$@"
