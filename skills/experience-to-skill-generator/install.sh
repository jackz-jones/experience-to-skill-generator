#!/usr/bin/env bash

set -Eeuo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_PACKAGE_DIR="$SCRIPT_DIR"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
AGENT_TYPE="auto"
INSTALL_MODE="${ESG_INSTALL_MODE:-auto}"
NON_INTERACTIVE="${ESG_NON_INTERACTIVE:-0}"
TARGET_SKILL_DIR="${ESG_SKILL_DIR:-}"
TARGET_CONFIG_DIR="${ESG_CONFIG_DIR:-}"
TARGET_BIN_DIR="${ESG_BIN_DIR:-$HOME/.local/bin}"
EXAMPLES_DIR="${ESG_EXAMPLES_DIR:-$HOME/.experience-to-skill-generator/examples}"
PROJECT_DIR="${ESG_PROJECT_DIR:-$REPO_DIR}"
OPENCLAW_AVAILABLE=0
INSTALL_STRATEGY="generic"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1" >&2; }
fatal() { log_error "$1"; exit 1; }

rollback_items=()
register_rollback() {
    rollback_items+=("$1")
}

rollback_on_error() {
    local exit_code=$?
    if [ "$exit_code" -ne 0 ]; then
        log_error "安装失败，正在清理本次创建的临时文件..."
        for item in "${rollback_items[@]+"${rollback_items[@]}"}"; do
            if [ -e "$item" ]; then
                rm -rf "$item" || true
            fi
        done
        log_error "安装未完成。请根据上方错误信息修复后重试。"
    fi
    exit "$exit_code"
}
trap rollback_on_error EXIT

confirm_install() {
    if [ "$NON_INTERACTIVE" = "1" ] || [ "$NON_INTERACTIVE" = "true" ]; then
        return 0
    fi
    read -r -p "是否继续安装？(y/N): " reply
    [[ "$reply" =~ ^[Yy]$ ]] || { log_info "安装已取消"; exit 0; }
}

check_python() {
    if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
        fatal "未找到 Python3。请安装 Python 3.8+，或通过 PYTHON_BIN 指定 Python 路径。"
    fi

    local version
    version="$($PYTHON_BIN -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')"
    log_info "检测到 Python: $version"

    if ! "$PYTHON_BIN" - <<'PY'
import sys
raise SystemExit(0 if sys.version_info >= (3, 8) else 1)
PY
    then
        fatal "Python 版本过低，需要 Python 3.8+。"
    fi
    log_success "Python 版本满足要求"
}

check_optional_dependencies() {
    log_info "检查可选 Python 依赖..."
    local missing=()
    for pkg in numpy sklearn; do
        if ! "$PYTHON_BIN" -c "import $pkg" >/dev/null 2>&1; then
            missing+=("$pkg")
        fi
    done

    if [ "${#missing[@]}" -gt 0 ]; then
        log_warning "以下可选依赖未安装: ${missing[*]}"
        log_warning "核心通用 CLI 可继续使用；旧版高级评分功能可能需要安装: pip3 install numpy scikit-learn"
    else
        log_success "可选依赖已满足"
    fi
}

detect_agent_environment() {
    if [ "$AGENT_TYPE" = "openclaw" ] || { [ "$AGENT_TYPE" = "auto" ] && command -v openclaw >/dev/null 2>&1; }; then
        OPENCLAW_AVAILABLE=1
        INSTALL_STRATEGY="openclaw"
        TARGET_SKILL_DIR="${TARGET_SKILL_DIR:-$HOME/.openclaw/skills/experience-to-skill-generator}"
        TARGET_CONFIG_DIR="${TARGET_CONFIG_DIR:-$HOME/.openclaw/config/skills/experience-to-skill-generator}"
        log_info "使用 OpenClaw 适配策略"
        if command -v openclaw >/dev/null 2>&1; then
            log_info "检测到 OpenClaw: $(openclaw --version 2>/dev/null | head -n1 || echo unknown)"
        else
            log_warning "指定 OpenClaw 策略但未找到 openclaw 命令，将仅复制文件到目标目录"
            OPENCLAW_AVAILABLE=0
        fi
    else
        INSTALL_STRATEGY="generic"
        TARGET_SKILL_DIR="${TARGET_SKILL_DIR:-$HOME/.experience-to-skill-generator/skills/experience-to-skill-generator}"
        TARGET_CONFIG_DIR="${TARGET_CONFIG_DIR:-$HOME/.experience-to-skill-generator/config}"
        log_info "使用通用兼容安装策略"
    fi
}

check_project_files() {
    [ -f "$SKILL_PACKAGE_DIR/SKILL.md" ] || fatal "找不到技能主文件: $SKILL_PACKAGE_DIR/SKILL.md"
    [ -f "$SCRIPT_DIR/config.json" ] || fatal "找不到技能配置文件: $SCRIPT_DIR/config.json"
    [ -f "$PROJECT_DIR/python-scripts/universal_skill_generator.py" ] || fatal "找不到通用 CLI: $PROJECT_DIR/python-scripts/universal_skill_generator.py"
    log_success "项目文件检查通过"
}

safe_copy_dir() {
    local source_dir="$1"
    local target_dir="$2"
    local parent_dir
    parent_dir="$(dirname "$target_dir")"
    mkdir -p "$parent_dir"

    if [ -e "$target_dir" ]; then
        local backup_dir="${target_dir}.bak.$(date +%Y%m%d%H%M%S)"
        log_warning "目标目录已存在，将备份到: $backup_dir"
        mv "$target_dir" "$backup_dir"
    else
        register_rollback "$target_dir"
    fi

    cp -R "$source_dir" "$target_dir"
}

install_files() {
    log_info "安装技能文件..."
    safe_copy_dir "$SKILL_PACKAGE_DIR" "$TARGET_SKILL_DIR"

    mkdir -p "$TARGET_CONFIG_DIR"
    register_rollback "$TARGET_CONFIG_DIR"
    cp "$SCRIPT_DIR/config.json" "$TARGET_CONFIG_DIR/config.json"

    mkdir -p "$TARGET_BIN_DIR"
    local cli_path="$TARGET_BIN_DIR/experience-to-skill-generator"
    cat > "$cli_path" <<EOF
#!/usr/bin/env bash
exec "$PYTHON_BIN" "$PROJECT_DIR/python-scripts/universal_skill_generator.py" "\$@"
EOF
    chmod +x "$cli_path"
    register_rollback "$cli_path"

    log_success "文件安装完成"
    log_info "技能目录: $TARGET_SKILL_DIR"
    log_info "配置目录: $TARGET_CONFIG_DIR"
    log_info "命令入口: $cli_path"
}

install_openclaw_skill() {
    if [ "$INSTALL_STRATEGY" != "openclaw" ] || [ "$OPENCLAW_AVAILABLE" -ne 1 ]; then
        return 0
    fi
    if [ "$INSTALL_MODE" = "copy-only" ]; then
        log_info "ESG_INSTALL_MODE=copy-only，跳过 openclaw skills install"
        return 0
    fi

    log_info "注册 OpenClaw 技能..."
    if openclaw skills list 2>/dev/null | grep -q "experience-to-skill-generator"; then
        openclaw skills update "$TARGET_SKILL_DIR" || {
            log_warning "OpenClaw 更新失败，尝试重新安装"
            openclaw skills uninstall experience-to-skill-generator || true
            openclaw skills install "$TARGET_SKILL_DIR"
        }
    else
        openclaw skills install "$TARGET_SKILL_DIR"
    fi
    log_success "OpenClaw 技能注册完成"
}

setup_examples() {
    log_info "创建示例数据..."
    mkdir -p "$EXAMPLES_DIR"
    cat > "$EXAMPLES_DIR/blockchain-monitor-session.json" <<'EOF'
{
  "title": "区块链监控 API 开发会话",
  "timestamp": "2026-04-29T14:30:00+08:00",
  "messages": [
    {"role": "user", "content": "我需要一个区块链 gas 价格监控 API，支持以太坊和 BSC 网络"},
    {"role": "assistant", "content": "建议先定义 REST API，再封装链网络适配器，最后增加缓存、错误处理和部署验证。"},
    {"role": "user", "content": "如何设计架构保持扩展性？"},
    {"role": "assistant", "content": "1. 抽象 NetworkAdapter 接口\n2. 为每条链实现独立适配器\n3. 将外部 API 调用、缓存和告警解耦\n4. 添加端到端测试验证新增链路"}
  ]
}
EOF
    log_success "示例数据已保存到: $EXAMPLES_DIR"
}

show_usage() {
    echo ""
    echo "=== Experience-to-Skill Generator 安装完成 ==="
    echo ""
    echo "安装策略: $INSTALL_STRATEGY"
    echo "技能目录: $TARGET_SKILL_DIR"
    echo "配置目录: $TARGET_CONFIG_DIR"
    echo "示例目录: $EXAMPLES_DIR"
    echo ""
    echo "可用命令:"
    echo "  experience-to-skill-generator --input '$EXAMPLES_DIR' diagnose"
    echo "  experience-to-skill-generator --input '$EXAMPLES_DIR/blockchain-monitor-session.json' analyze"
    echo "  experience-to-skill-generator --input '$EXAMPLES_DIR/blockchain-monitor-session.json' --output-dir './generated_skills' generate"
    echo "  experience-to-skill-generator config"
    echo ""
    echo "常用环境变量:"
    echo "  ESG_SKILL_DIR=/custom/skills/experience-to-skill-generator"
    echo "  ESG_CONFIG_DIR=/custom/config"
    echo "  ESG_OUTPUT_DIR=/custom/generated_skills"
    echo "  ESG_SESSION_DIR=/custom/sessions"
    echo "  ESG_NON_INTERACTIVE=1"
    echo ""
    if ! echo "$PATH" | tr ':' '\n' | grep -qx "$TARGET_BIN_DIR"; then
        echo "提示: $TARGET_BIN_DIR 不在 PATH 中，可执行:"
        echo "  export PATH=\"$TARGET_BIN_DIR:\$PATH\""
    fi
}

main() {
    echo ""
    echo "🦍 Experience-to-Skill Generator 通用安装程序"
    echo "================================================"
    echo "版本: v0.2.0"
    echo "描述: 自动分析 agent 会话并生成可复用 SKILL"
    echo ""

    confirm_install
    check_python
    check_optional_dependencies
    detect_agent_environment
    check_project_files
    install_files
    install_openclaw_skill
    setup_examples
    show_usage

    trap - EXIT
    log_success "🎉 安装完成！"
}

main "$@"