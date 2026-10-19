# Fish shell completions for DruidOS Hive Stack
# Place in ~/.config/fish/completions/ or /usr/share/fish/completions/

# =============================================================================
# hive-cortex
# =============================================================================
complete -c hive-cortex -s h -l help -d "Show help message"
complete -c hive-cortex -s V -l version -d "Show version"
complete -c hive-cortex -s c -l config -r -F -d "Configuration file"
complete -c hive-cortex -s l -l log-level -x -a "trace debug info warn error" -d "Log level"
complete -c hive-cortex -s f -l foreground -d "Run in foreground"
complete -c hive-cortex -s s -l socket -r -F -d "Socket path"

# =============================================================================
# hive-synapse
# =============================================================================
complete -c hive-synapse -s h -l help -d "Show help message"
complete -c hive-synapse -s V -l version -d "Show version"
complete -c hive-synapse -s c -l config -r -F -d "Configuration file"
complete -c hive-synapse -s m -l model -r -d "Model file (GGUF)"
complete -c hive-synapse -l context-size -x -a "512 1024 2048 4096" -d "Context window size"
complete -c hive-synapse -l max-tokens -x -d "Maximum tokens to generate"
complete -c hive-synapse -l temperature -x -d "Generation temperature"
complete -c hive-synapse -l test-model -r -d "Test model loading"

# =============================================================================
# hive-apt
# =============================================================================
set -l hive_apt_commands install remove update upgrade search show info autoremove clean

complete -c hive-apt -s h -l help -d "Show help message"
complete -c hive-apt -s V -l version -d "Show version"
complete -c hive-apt -s y -l yes -d "Assume yes to prompts"
complete -c hive-apt -l no-snapshot -d "Skip ZFS snapshot"
complete -c hive-apt -s q -l quiet -d "Quiet mode"

complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a install -d "Install packages"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a remove -d "Remove packages"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a update -d "Update package lists"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a upgrade -d "Upgrade packages"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a search -d "Search for packages"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a show -d "Show package details"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a info -d "Show package information"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a autoremove -d "Remove unused dependencies"
complete -c hive-apt -n "not __fish_seen_subcommand_from $hive_apt_commands" -a clean -d "Clean package cache"

# Package completion for install/remove/show
function __hive_apt_packages
    apt-cache --no-generate pkgnames 2>/dev/null | head -100
end

complete -c hive-apt -n "__fish_seen_subcommand_from install remove show info" -a "(__hive_apt_packages)" -d "Package"

# =============================================================================
# hive-zfs
# =============================================================================
set -l hive_zfs_commands snapshot rollback list destroy clean status

complete -c hive-zfs -s h -l help -d "Show help message"
complete -c hive-zfs -s V -l version -d "Show version"
complete -c hive-zfs -s d -l dataset -x -d "Dataset name"
complete -c hive-zfs -s r -l recursive -d "Recursive operation"
complete -c hive-zfs -s k -l keep -x -a "1 3 5 7 10 14 30" -d "Snapshots to keep"
complete -c hive-zfs -s o -l older-than -x -a "1d 7d 14d 30d 90d" -d "Remove older than"

complete -c hive-zfs -n "not __fish_seen_subcommand_from $hive_zfs_commands" -a snapshot -d "Create a snapshot"
complete -c hive-zfs -n "not __fish_seen_subcommand_from $hive_zfs_commands" -a rollback -d "Rollback to a snapshot"
complete -c hive-zfs -n "not __fish_seen_subcommand_from $hive_zfs_commands" -a list -d "List snapshots"
complete -c hive-zfs -n "not __fish_seen_subcommand_from $hive_zfs_commands" -a destroy -d "Destroy a snapshot"
complete -c hive-zfs -n "not __fish_seen_subcommand_from $hive_zfs_commands" -a clean -d "Clean old snapshots"
complete -c hive-zfs -n "not __fish_seen_subcommand_from $hive_zfs_commands" -a status -d "Show ZFS status"

# ZFS dataset completion
function __hive_zfs_datasets
    command zfs list -H -o name 2>/dev/null
end

complete -c hive-zfs -n "__fish_seen_subcommand_from snapshot rollback destroy" -a "(__hive_zfs_datasets)" -d "Dataset"

# =============================================================================
# hive-shell
# =============================================================================
set -l hive_shell_commands toggle show hide quiet detach full test-notification status

complete -c hive-shell -s h -l help -d "Show help message"
complete -c hive-shell -s V -l version -d "Show version"
complete -c hive-shell -s c -l config -r -F -d "Configuration file"

complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a toggle -d "Toggle overlay visibility"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a show -d "Show overlay"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a hide -d "Hide overlay"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a quiet -d "Enter quiet mode"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a detach -d "Detach current terminal"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a full -d "Enter full anonymous mode"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a test-notification -d "Send test notification"
complete -c hive-shell -n "not __fish_seen_subcommand_from $hive_shell_commands" -a status -d "Show current status"

# =============================================================================
# hive-term
# =============================================================================
complete -c hive-term -s h -l help -d "Show help message"
complete -c hive-term -s V -l version -d "Show version"
complete -c hive-term -s c -l config -r -F -d "Configuration file"
complete -c hive-term -s e -l command -x -a "(__fish_complete_command)" -d "Command to execute"
complete -c hive-term -s d -l working-directory -r -a "(__fish_complete_directories)" -d "Working directory"
complete -c hive-term -s a -l anonymous -x -a "quiet detach full" -d "Anonymous mode"
complete -c hive-term -l class -x -d "Window class"
complete -c hive-term -l title -x -d "Window title"

# =============================================================================
# hive-dock
# =============================================================================
set -l hive_dock_commands show hide toggle reload pin unpin

complete -c hive-dock -s h -l help -d "Show help message"
complete -c hive-dock -s V -l version -d "Show version"
complete -c hive-dock -s c -l config -r -F -d "Configuration file"
complete -c hive-dock -s p -l position -x -a "bottom top left right" -d "Dock position"

complete -c hive-dock -n "not __fish_seen_subcommand_from $hive_dock_commands" -a show -d "Show dock"
complete -c hive-dock -n "not __fish_seen_subcommand_from $hive_dock_commands" -a hide -d "Hide dock"
complete -c hive-dock -n "not __fish_seen_subcommand_from $hive_dock_commands" -a toggle -d "Toggle dock visibility"
complete -c hive-dock -n "not __fish_seen_subcommand_from $hive_dock_commands" -a reload -d "Reload configuration"
complete -c hive-dock -n "not __fish_seen_subcommand_from $hive_dock_commands" -a pin -d "Pin application"
complete -c hive-dock -n "not __fish_seen_subcommand_from $hive_dock_commands" -a unpin -d "Unpin application"

# Desktop file completion for pin/unpin
function __hive_dock_apps
    for f in /usr/share/applications/*.desktop
        basename $f .desktop
    end
end

complete -c hive-dock -n "__fish_seen_subcommand_from pin unpin" -a "(__hive_dock_apps)" -d "Application"

# =============================================================================
# hive-actuator
# =============================================================================
complete -c hive-actuator -s h -l help -d "Show help message"
complete -c hive-actuator -s V -l version -d "Show version"
complete -c hive-actuator -s c -l config -r -F -d "Configuration file"
complete -c hive-actuator -s w -l whitelist -r -F -d "Whitelist file"
complete -c hive-actuator -s n -l dry-run -d "Dry run mode"
complete -c hive-actuator -s l -l log-level -x -a "trace debug info warn error" -d "Log level"

# =============================================================================
# Nerve components (minimal completions)
# =============================================================================
for cmd in hive-nerve-process hive-nerve-journal hive-nerve-network hive-nerve-fs
    complete -c $cmd -s h -l help -d "Show help message"
    complete -c $cmd -s V -l version -d "Show version"
    complete -c $cmd -s c -l config -r -F -d "Configuration file"
    complete -c $cmd -s l -l log-level -x -a "trace debug info warn error" -d "Log level"
end
