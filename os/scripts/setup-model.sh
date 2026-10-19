#!/bin/bash
# ============================================================================
# DruidOS Model Setup Script
# Downloads and configures the SLM model for hive-synapse
# ============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MODEL_DIR="${HIVE_MODEL_DIR:-/var/lib/hive/models}"
MODEL_NAME="qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_URL="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
MODEL_SHA256="a]Expected SHA256 will be verified after download"

# Alternative models (user can choose)
declare -A MODELS=(
    ["qwen-0.5b-q4"]="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q4_k_m.gguf"
    ["qwen-0.5b-q8"]="https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF/resolve/main/qwen2.5-0.5b-instruct-q8_0.gguf"
    ["qwen-1.5b-q4"]="https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF/resolve/main/qwen2.5-1.5b-instruct-q4_k_m.gguf"
    ["phi-3-mini-q4"]="https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf"
    ["tinyllama-q4"]="https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
)

declare -A MODEL_SIZES=(
    ["qwen-0.5b-q4"]="400MB"
    ["qwen-0.5b-q8"]="700MB"
    ["qwen-1.5b-q4"]="1.1GB"
    ["phi-3-mini-q4"]="2.2GB"
    ["tinyllama-q4"]="700MB"
)

declare -A MODEL_FILES=(
    ["qwen-0.5b-q4"]="qwen2.5-0.5b-instruct-q4_k_m.gguf"
    ["qwen-0.5b-q8"]="qwen2.5-0.5b-instruct-q8_0.gguf"
    ["qwen-1.5b-q4"]="qwen2.5-1.5b-instruct-q4_k_m.gguf"
    ["phi-3-mini-q4"]="Phi-3-mini-4k-instruct-q4.gguf"
    ["tinyllama-q4"]="tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"
)

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_banner() {
    echo -e "${BLUE}"
    cat << 'EOF'
    ____             _     __  ____  _____
   / __ \_______  __(_)___/ / / __ \/ ___/
  / / / / ___/ / / / / __  / / / / /\__ \
 / /_/ / /  / /_/ / / /_/ / / /_/ /___/ /
/_____/_/   \__,_/_/\__,_/  \____//____/

         Model Setup Script
EOF
    echo -e "${NC}"
}

check_dependencies() {
    log_info "Checking dependencies..."

    local missing=()

    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
        missing+=("curl or wget")
    fi

    if ! command -v sha256sum &> /dev/null; then
        missing+=("sha256sum (coreutils)")
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing dependencies: ${missing[*]}"
        log_info "Install with: sudo apt install curl coreutils"
        exit 1
    fi

    log_success "All dependencies satisfied"
}

check_disk_space() {
    local required_mb=$1
    local available_mb

    available_mb=$(df -m "$MODEL_DIR" 2>/dev/null | awk 'NR==2 {print $4}' || echo "0")

    if [ "$available_mb" -lt "$required_mb" ]; then
        log_error "Insufficient disk space. Need ${required_mb}MB, have ${available_mb}MB"
        exit 1
    fi

    log_success "Disk space check passed (${available_mb}MB available)"
}

create_model_dir() {
    if [ ! -d "$MODEL_DIR" ]; then
        log_info "Creating model directory: $MODEL_DIR"
        sudo mkdir -p "$MODEL_DIR"
        sudo chown _hive-ai:hive "$MODEL_DIR" 2>/dev/null || sudo chown root:root "$MODEL_DIR"
        sudo chmod 750 "$MODEL_DIR"
    fi
}

list_models() {
    echo ""
    echo "Available models:"
    echo "================="
    printf "%-20s %-10s %s\n" "Model ID" "Size" "Description"
    echo "-----------------------------------------------------------"
    printf "%-20s %-10s %s\n" "qwen-0.5b-q4" "400MB" "Qwen 2.5 0.5B Q4 (recommended, default)"
    printf "%-20s %-10s %s\n" "qwen-0.5b-q8" "700MB" "Qwen 2.5 0.5B Q8 (higher quality)"
    printf "%-20s %-10s %s\n" "qwen-1.5b-q4" "1.1GB" "Qwen 2.5 1.5B Q4 (smarter, needs more RAM)"
    printf "%-20s %-10s %s\n" "phi-3-mini-q4" "2.2GB" "Phi-3 Mini Q4 (Microsoft, good reasoning)"
    printf "%-20s %-10s %s\n" "tinyllama-q4" "700MB" "TinyLlama 1.1B Q4 (fast, lightweight)"
    echo ""
}

download_model() {
    local model_id="$1"
    local url="${MODELS[$model_id]}"
    local filename="${MODEL_FILES[$model_id]}"
    local filepath="$MODEL_DIR/$filename"

    if [ -f "$filepath" ]; then
        log_warn "Model already exists: $filepath"
        read -p "Re-download? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing model"
            return 0
        fi
    fi

    log_info "Downloading $model_id (${MODEL_SIZES[$model_id]})..."
    log_info "URL: $url"

    # Create temp file
    local temp_file="$filepath.downloading"

    # Download with progress
    if command -v curl &> /dev/null; then
        curl -L --progress-bar -o "$temp_file" "$url"
    else
        wget --show-progress -O "$temp_file" "$url"
    fi

    # Move to final location
    mv "$temp_file" "$filepath"

    # Set permissions
    sudo chown _hive-ai:hive "$filepath" 2>/dev/null || sudo chown root:root "$filepath"
    sudo chmod 640 "$filepath"

    log_success "Downloaded: $filepath"
}

verify_model() {
    local filepath="$1"

    log_info "Verifying model file..."

    # Check file exists and has reasonable size
    if [ ! -f "$filepath" ]; then
        log_error "Model file not found: $filepath"
        return 1
    fi

    local size
    size=$(stat -c%s "$filepath" 2>/dev/null || stat -f%z "$filepath" 2>/dev/null)

    if [ "$size" -lt 100000000 ]; then  # Less than 100MB is suspicious
        log_error "Model file seems too small (${size} bytes). Download may be incomplete."
        return 1
    fi

    # Try to verify it's a valid GGUF file (check magic bytes)
    local magic
    magic=$(head -c 4 "$filepath" | od -A n -t x1 | tr -d ' ')

    if [ "$magic" != "47475546" ]; then  # "GGUF" in hex
        log_warn "File doesn't appear to be a valid GGUF model (magic: $magic)"
        log_warn "Expected GGUF magic bytes. File may be corrupted or wrong format."
    else
        log_success "GGUF magic bytes verified"
    fi

    log_success "Model file size: $(numfmt --to=iec-i --suffix=B "$size" 2>/dev/null || echo "${size} bytes")"
    return 0
}

create_symlink() {
    local model_id="$1"
    local filename="${MODEL_FILES[$model_id]}"
    local filepath="$MODEL_DIR/$filename"
    local symlink="$MODEL_DIR/current.gguf"

    log_info "Creating symlink: current.gguf -> $filename"

    # Remove existing symlink
    sudo rm -f "$symlink"

    # Create new symlink
    sudo ln -s "$filename" "$symlink"

    log_success "Active model set to: $model_id"
}

update_config() {
    local model_id="$1"
    local filename="${MODEL_FILES[$model_id]}"
    local config_file="/etc/hive/config.toml"

    if [ -f "$config_file" ]; then
        log_info "Updating hive config..."

        # Check if model_path line exists
        if grep -q "^model_path" "$config_file" 2>/dev/null; then
            sudo sed -i "s|^model_path.*|model_path = \"$MODEL_DIR/$filename\"|" "$config_file"
        elif grep -q "^# model_path" "$config_file" 2>/dev/null; then
            sudo sed -i "s|^# model_path.*|model_path = \"$MODEL_DIR/$filename\"|" "$config_file"
        else
            log_warn "Could not find model_path in config. Add manually:"
            echo "  model_path = \"$MODEL_DIR/$filename\""
        fi
    else
        log_warn "Config file not found: $config_file"
        log_info "Set model path manually in your config:"
        echo "  model_path = \"$MODEL_DIR/$filename\""
    fi
}

test_model() {
    local filepath="$1"

    log_info "Testing model loading..."

    # Check if hive-synapse exists
    if command -v hive-synapse &> /dev/null; then
        log_info "Running quick model test with hive-synapse..."
        timeout 30 hive-synapse --test-model "$filepath" 2>&1 || {
            log_warn "Model test timed out or failed (this may be normal if synapse isn't fully set up)"
        }
    else
        log_info "hive-synapse not installed, skipping model test"
        log_info "Model will be tested when hive-synapse starts"
    fi
}

show_status() {
    echo ""
    echo "Model Status"
    echo "============"

    if [ -d "$MODEL_DIR" ]; then
        echo "Model directory: $MODEL_DIR"
        echo ""
        echo "Installed models:"
        ls -lh "$MODEL_DIR"/*.gguf 2>/dev/null || echo "  (none)"
        echo ""

        if [ -L "$MODEL_DIR/current.gguf" ]; then
            local current
            current=$(readlink "$MODEL_DIR/current.gguf")
            echo "Active model: $current"
        else
            echo "Active model: (not set)"
        fi
    else
        echo "Model directory does not exist: $MODEL_DIR"
    fi
}

usage() {
    cat << EOF
Usage: $(basename "$0") [OPTIONS] [COMMAND]

Commands:
    install [MODEL_ID]    Download and install a model (default: qwen-0.5b-q4)
    list                  List available models
    status                Show installed models and current selection
    set MODEL_ID          Set the active model
    remove MODEL_ID       Remove an installed model
    test                  Test the current model

Options:
    -d, --dir DIR         Model directory (default: /var/lib/hive/models)
    -h, --help            Show this help message

Examples:
    $(basename "$0") install                    # Install default model
    $(basename "$0") install qwen-1.5b-q4       # Install larger model
    $(basename "$0") list                       # Show available models
    $(basename "$0") set qwen-0.5b-q8           # Switch active model
    $(basename "$0") status                     # Show current status

Environment Variables:
    HIVE_MODEL_DIR        Override default model directory

EOF
}

# Main
main() {
    local command="${1:-}"
    local model_id="${2:-qwen-0.5b-q4}"

    # Parse options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -d|--dir)
                MODEL_DIR="$2"
                shift 2
                ;;
            -h|--help)
                usage
                exit 0
                ;;
            list|status|install|set|remove|test)
                command="$1"
                shift
                model_id="${1:-qwen-0.5b-q4}"
                shift || true
                ;;
            *)
                if [ -z "$command" ]; then
                    command="install"
                    model_id="${1:-qwen-0.5b-q4}"
                fi
                shift
                ;;
        esac
    done

    # Default command
    command="${command:-install}"

    print_banner

    case "$command" in
        list)
            list_models
            ;;
        status)
            show_status
            ;;
        install)
            # Validate model ID
            if [ -z "${MODELS[$model_id]:-}" ]; then
                log_error "Unknown model: $model_id"
                list_models
                exit 1
            fi

            check_dependencies
            create_model_dir

            # Estimate required space (download size + some buffer)
            local size_str="${MODEL_SIZES[$model_id]}"
            local size_mb
            if [[ "$size_str" == *GB ]]; then
                size_mb=$(echo "$size_str" | sed 's/GB//' | awk '{print int($1 * 1024 * 1.1)}')
            else
                size_mb=$(echo "$size_str" | sed 's/MB//' | awk '{print int($1 * 1.1)}')
            fi
            check_disk_space "$size_mb"

            download_model "$model_id"

            local filepath="$MODEL_DIR/${MODEL_FILES[$model_id]}"
            verify_model "$filepath"
            create_symlink "$model_id"
            update_config "$model_id"

            echo ""
            log_success "Model setup complete!"
            echo ""
            echo "Next steps:"
            echo "  1. Restart hive-synapse: sudo systemctl restart hive-synapse"
            echo "  2. Check status: sudo systemctl status hive-synapse"
            echo "  3. Check logs: journalctl -u hive-synapse -f"
            ;;
        set)
            if [ -z "${MODELS[$model_id]:-}" ]; then
                log_error "Unknown model: $model_id"
                list_models
                exit 1
            fi

            local filepath="$MODEL_DIR/${MODEL_FILES[$model_id]}"
            if [ ! -f "$filepath" ]; then
                log_error "Model not installed: $model_id"
                log_info "Install with: $(basename "$0") install $model_id"
                exit 1
            fi

            create_symlink "$model_id"
            update_config "$model_id"
            log_success "Active model changed to: $model_id"
            log_info "Restart hive-synapse to apply: sudo systemctl restart hive-synapse"
            ;;
        remove)
            local filepath="$MODEL_DIR/${MODEL_FILES[$model_id]:-$model_id}"
            if [ -f "$filepath" ]; then
                log_info "Removing: $filepath"
                sudo rm -f "$filepath"
                log_success "Model removed"
            else
                log_error "Model not found: $filepath"
                exit 1
            fi
            ;;
        test)
            local current="$MODEL_DIR/current.gguf"
            if [ -L "$current" ]; then
                test_model "$current"
            else
                log_error "No active model set"
                log_info "Install a model first: $(basename "$0") install"
                exit 1
            fi
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

main "$@"
