//! Hive APT - Intelligent Package Manager Wrapper
//!
//! Wraps apt/dpkg commands with Hive intelligence:
//! - Shows package knowledge before installation
//! - Warns about resource usage and security implications
//! - Snapshots the system (ZFS) before changing packages
//! - Provides alternatives and related packages

mod knowledge;

use anyhow::{Context, Result};
use clap::{Parser, Subcommand};
use colored::Colorize;
use std::path::Path;
use std::process::{Command, Stdio};

use crate::knowledge::PackageKnowledge;

/// Hive-enhanced package manager
#[derive(Parser)]
#[command(name = "hive-apt")]
#[command(about = "Intelligent apt wrapper with Hive knowledge", long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,

    /// Skip Hive analysis and the pre-change snapshot, and run plain apt
    #[arg(long, global = true)]
    skip_hive: bool,

    /// Don't prompt for confirmation
    #[arg(short = 'y', long, global = true)]
    yes: bool,
}

#[derive(Subcommand)]
enum Commands {
    /// Install packages
    Install {
        /// Packages to install
        packages: Vec<String>,
    },
    /// Remove packages
    Remove {
        /// Packages to remove
        packages: Vec<String>,
        /// Also purge configuration
        #[arg(long)]
        purge: bool,
    },
    /// Update package lists
    Update,
    /// Upgrade installed packages
    Upgrade {
        /// Full upgrade (allows removing packages)
        #[arg(long)]
        full: bool,
    },
    /// Search for packages
    Search {
        /// Search term
        query: String,
    },
    /// Show package information
    Show {
        /// Package name
        package: String,
    },
    /// List installed packages
    List {
        /// Only show upgradable
        #[arg(long)]
        upgradable: bool,
    },
    /// Clean package cache
    Clean,
    /// Auto-remove unused packages
    Autoremove,
}

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize color output
    colored::control::set_override(true);

    match cli.command {
        Commands::Install { packages } => {
            install_packages(&packages, cli.skip_hive, cli.yes).await?;
        }
        Commands::Remove { packages, purge } => {
            remove_packages(&packages, purge, cli.skip_hive, cli.yes).await?;
        }
        Commands::Update => {
            run_apt(&["update"], cli.yes)?;
        }
        Commands::Upgrade { full } => {
            upgrade(full, cli.skip_hive, cli.yes)?;
        }
        Commands::Search { query } => {
            run_apt(&["search", &query], false)?;
        }
        Commands::Show { package } => {
            show_package(&package, cli.skip_hive).await?;
        }
        Commands::List { upgradable } => {
            if upgradable {
                run_apt(&["list", "--upgradable"], false)?;
            } else {
                run_apt(&["list", "--installed"], false)?;
            }
        }
        Commands::Clean => {
            run_apt(&["clean"], cli.yes)?;
        }
        Commands::Autoremove => {
            if !cli.skip_hive {
                snapshot_system("before-autoremove")?;
            }
            let mut args = vec!["autoremove"];
            if cli.yes {
                args.push("-y");
            }
            run_apt(&args, false)?;
        }
    }

    Ok(())
}

async fn install_packages(packages: &[String], skip_hive: bool, auto_yes: bool) -> Result<()> {
    if !skip_hive {
        // Load knowledge for each package
        for package in packages {
            if let Some(knowledge) = load_package_knowledge(package).await {
                print_package_knowledge(&knowledge);
            }
        }

        // Confirm
        if !auto_yes && !confirm("Proceed with installation?")? {
            println!("{}", "Installation cancelled.".yellow());
            return Ok(());
        }

        snapshot_system(&format!("before-install-{}", package_label(packages)))?;
    }

    // Run apt install
    let mut args = vec!["install"];
    if auto_yes {
        args.push("-y");
    }
    for pkg in packages {
        args.push(pkg);
    }

    run_apt(&args, false)
}

async fn remove_packages(
    packages: &[String],
    purge: bool,
    skip_hive: bool,
    auto_yes: bool,
) -> Result<()> {
    if !skip_hive {
        println!(
            "\n{} {}",
            "⚠".yellow(),
            "This will remove the following packages:".yellow()
        );
        for pkg in packages {
            println!("  - {}", pkg.red());
        }

        // Confirm
        if !auto_yes && !confirm("Proceed with removal?")? {
            println!("{}", "Removal cancelled.".yellow());
            return Ok(());
        }

        snapshot_system(&format!("before-remove-{}", package_label(packages)))?;
    }

    let cmd = if purge { "purge" } else { "remove" };
    let mut args = vec![cmd];
    if auto_yes {
        args.push("-y");
    }
    for pkg in packages {
        args.push(pkg);
    }

    run_apt(&args, false)
}

fn upgrade(full: bool, skip_hive: bool, auto_yes: bool) -> Result<()> {
    if !auto_yes && !confirm("Proceed with upgrade?")? {
        println!("{}", "Upgrade cancelled.".yellow());
        return Ok(());
    }

    let cmd = if full { "full-upgrade" } else { "upgrade" };
    if !skip_hive {
        snapshot_system(&format!("before-{cmd}"))?;
    }
    let mut args = vec![cmd];
    if auto_yes {
        args.push("-y");
    }

    run_apt(&args, false)
}

async fn show_package(package: &str, skip_hive: bool) -> Result<()> {
    // Show apt info
    run_apt(&["show", package], false)?;

    // Show Hive knowledge if available
    if !skip_hive {
        if let Some(knowledge) = load_package_knowledge(package).await {
            println!("\n{}", "═".repeat(60).blue());
            println!("{}", " Hive Knowledge ".blue().bold());
            println!("{}", "═".repeat(60).blue());
            print_package_knowledge(&knowledge);
        }
    }

    Ok(())
}

async fn load_package_knowledge(package: &str) -> Option<PackageKnowledge> {
    // Check local knowledge base first
    let knowledge_paths = [
        format!("/var/lib/hive/knowledge/packages/{}.yaml", package),
        format!(
            "{}/knowledge/packages/{}.yaml",
            env!("CARGO_MANIFEST_DIR"),
            package
        ),
    ];

    for path in &knowledge_paths {
        if Path::new(path).exists() {
            if let Ok(content) = std::fs::read_to_string(path) {
                if let Ok(knowledge) = serde_yaml::from_str(&content) {
                    return Some(knowledge);
                }
            }
        }
    }

    // Check repository knowledge base
    let repo_path = format!(
        "{}/../../knowledge/packages/{}.yaml",
        env!("CARGO_MANIFEST_DIR"),
        package
    );
    if Path::new(&repo_path).exists() {
        if let Ok(content) = std::fs::read_to_string(&repo_path) {
            if let Ok(knowledge) = serde_yaml::from_str(&content) {
                return Some(knowledge);
            }
        }
    }

    None
}

fn print_package_knowledge(knowledge: &PackageKnowledge) {
    println!("\n{}", "═".repeat(60).blue());
    println!("{} {}", "📦".blue(), knowledge.package.blue().bold());
    println!("{}", "═".repeat(60).blue());

    if let Some(desc) = &knowledge.description {
        println!("\n{}", desc);
    }

    // Install notes
    if !knowledge.install_notes.is_empty() {
        println!("\n{}", "📋 Install Notes:".green());
        for note in &knowledge.install_notes {
            println!("  • {}", note);
        }
    }

    // Warnings
    if !knowledge.warnings.is_empty() {
        println!("\n{}", "⚠ Warnings:".yellow());
        for warning in &knowledge.warnings {
            let severity_icon = match warning.severity.as_deref() {
                Some("high") | Some("critical") => "🔴",
                Some("medium") => "🟡",
                _ => "🟢",
            };
            println!(
                "  {} [{}] {}",
                severity_icon,
                warning
                    .warning_type
                    .as_deref()
                    .unwrap_or("info")
                    .to_uppercase(),
                warning.message
            );
        }
    }

    // Common issues
    if !knowledge.common_issues.is_empty() {
        println!("\n{}", "🔧 Common Issues:".cyan());
        for issue in &knowledge.common_issues {
            println!("  • Pattern: {}", issue.pattern.yellow());
            println!("    Solution: {}", issue.solution);
        }
    }

    // Alternatives
    if !knowledge.alternatives.is_empty() {
        println!("\n{}", "🔄 Alternatives:".magenta());
        for alt in &knowledge.alternatives {
            println!("  • {}: {}", alt.name.bold(), alt.reason);
        }
    }

    // Post-install commands
    if !knowledge.post_install.is_empty() {
        println!("\n{}", "🚀 Post-Install Commands:".green());
        for cmd in &knowledge.post_install {
            println!(
                "  $ {}",
                cmd.command.as_deref().unwrap_or("").bright_white()
            );
            if let Some(desc) = &cmd.description {
                println!("    {}", desc.dimmed());
            }
        }
    }

    println!();
}

/// Snapshot the system before apt changes it, so the change can be rolled
/// back. Nothing to do when the root filesystem isn't ZFS; when it is and
/// the snapshot fails, the package change doesn't happen either.
fn snapshot_system(label: &str) -> Result<()> {
    use hive_common::zfs;

    let datasets = zfs::system_datasets();
    if datasets.is_empty() {
        println!(
            "\n{} {}",
            "💾".blue(),
            "Root filesystem is not on ZFS: no snapshot taken".dimmed()
        );
        return Ok(());
    }
    let snapshots = zfs::create_snapshots(&datasets, &zfs::snapshot_name_now(label)).context(
        "Could not snapshot the system before changing packages \
         (run as root, or pass --skip-hive to go ahead without a snapshot)",
    )?;
    println!("\n{} {}", "💾".blue(), "Snapshot taken:".blue());
    for snapshot in &snapshots {
        println!("   {}", snapshot.bright_white());
    }
    println!();
    Ok(())
}

/// The packages as a snapshot label: `nginx`, a local `./foo_1.0_all.deb`
/// as `foo_1.0_all`, and `nginx-and-2-more` for several.
fn package_label(packages: &[String]) -> String {
    let Some(first) = packages.first() else {
        return "packages".to_string();
    };
    let name = Path::new(first)
        .file_name()
        .and_then(|name| name.to_str())
        .unwrap_or(first);
    let name = name.strip_suffix(".deb").unwrap_or(name);
    match packages.len() {
        1 => name.to_string(),
        n => format!("{name}-and-{}-more", n - 1),
    }
}

fn confirm(prompt: &str) -> Result<bool> {
    use std::io::{self, Write};

    print!("{} [y/N] ", prompt.yellow());
    io::stdout().flush()?;

    let mut input = String::new();
    io::stdin().read_line(&mut input)?;

    Ok(input.trim().eq_ignore_ascii_case("y") || input.trim().eq_ignore_ascii_case("yes"))
}

fn run_apt(args: &[&str], _capture: bool) -> Result<()> {
    let status = Command::new("apt")
        .args(args)
        .stdin(Stdio::inherit())
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .status()
        .context("Failed to run apt")?;

    if !status.success() {
        anyhow::bail!("apt exited with status {}", status);
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn loads_real_shipped_package_knowledge() {
        // Exercises the actual production path-resolution chain in
        // load_package_knowledge (checks /var/lib/hive/... first, falls
        // back to the repo's knowledge/packages/ directory) against every
        // package file actually shipped in knowledge/packages/ — catches
        // schema drift between PackageKnowledge and the real YAML files.
        for package in [
            "docker",
            "nginx",
            "nodejs",
            "postgresql",
            "python3",
            "redis",
        ] {
            let knowledge = load_package_knowledge(package).await.unwrap_or_else(|| {
                panic!("knowledge/packages/{}.yaml should load and parse", package)
            });
            assert!(!knowledge.package.is_empty());
            assert!(
                !knowledge.install_notes.is_empty(),
                "{} knowledge should have install notes",
                package
            );
        }
    }

    #[test]
    fn snapshots_are_labelled_after_the_packages() {
        let label = |packages: &[&str]| {
            package_label(&packages.iter().map(|p| p.to_string()).collect::<Vec<_>>())
        };
        assert_eq!(label(&["nginx"]), "nginx");
        assert_eq!(
            label(&["/tmp/x/druidos-e2e-dummy.deb"]),
            "druidos-e2e-dummy"
        );
        assert_eq!(label(&["nginx", "redis", "vim"]), "nginx-and-2-more");
    }

    #[tokio::test]
    async fn missing_package_knowledge_returns_none() {
        assert!(load_package_knowledge("definitely-not-a-real-package-xyz")
            .await
            .is_none());
    }
}
