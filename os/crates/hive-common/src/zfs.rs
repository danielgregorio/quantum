//! ZFS safety snapshots: which datasets hold the system, and snapshotting
//! them before the Hive (or a user through a Hive tool) changes it.
//!
//! The datasets are found, not assumed: installers name them themselves
//! (Ubuntu's picks `rpool/ROOT/ubuntu_<random>` and `bpool/BOOT/ubuntu_<random>`),
//! so they are read from the kernel's mount table. On a non-ZFS root there is
//! nothing to snapshot, and callers get an empty list rather than an error.

use std::path::{Component, Path};
use std::process::Command;

/// Every snapshot the Hive creates starts with this, so they can be told
/// apart from the admin's own (the actuator whitelist only lets the Hive
/// delete snapshots matching `hive-*`).
pub const SNAPSHOT_PREFIX: &str = "hive-";

/// The datasets that make up the installed system, read from this process's
/// mount table: see [`system_datasets_in`].
pub fn system_datasets() -> Vec<String> {
    std::fs::read_to_string("/proc/self/mountinfo")
        .map(|mountinfo| system_datasets_in(&mountinfo))
        .unwrap_or_default()
}

/// The ZFS datasets holding `/` and `/boot` — what a package change touches.
/// Ubuntu's ZFS layout keeps `/boot` in a pool of its own (`bpool`), and a
/// kernel update rolled back without it would leave the boot loader pointing
/// at kernels that are gone. Empty when `/` isn't ZFS: a system that is only
/// partly on ZFS can't be rolled back as a whole anyway.
pub fn system_datasets_in(mountinfo: &str) -> Vec<String> {
    let Some(root) = dataset_containing(mountinfo, Path::new("/")) else {
        return vec![];
    };
    let boot = dataset_containing(mountinfo, Path::new("/boot"))
        // A /boot inside the root dataset (or a child of it) is already
        // covered by the root's recursive snapshot.
        .filter(|boot| *boot != root && !boot.starts_with(&format!("{root}/")));
    std::iter::once(root).chain(boot).collect()
}

/// The ZFS dataset whose filesystem holds `path`, according to a
/// `/proc/<pid>/mountinfo` table: the mount with the longest mount point
/// that is a prefix of `path` (the last one listed, when several are
/// stacked on the same mount point). `None` if that mount isn't ZFS.
pub fn dataset_containing(mountinfo: &str, path: &Path) -> Option<String> {
    let mut best: Option<(usize, &str, &str)> = None; // (depth, fstype, source)
    for line in mountinfo.lines() {
        let Some(mount) = parse_mountinfo_line(line) else {
            continue;
        };
        let mount_point = unescape(mount.mount_point);
        if !path.starts_with(&mount_point) {
            continue;
        }
        let depth = Path::new(&mount_point)
            .components()
            .filter(|c| matches!(c, Component::Normal(_)))
            .count();
        if best.map_or(true, |(best_depth, _, _)| depth >= best_depth) {
            best = Some((depth, mount.fstype, mount.source));
        }
    }
    match best {
        Some((_, "zfs", source)) => Some(unescape(source)),
        _ => None,
    }
}

struct MountEntry<'a> {
    mount_point: &'a str,
    fstype: &'a str,
    source: &'a str,
}

/// `36 35 98:0 /mnt1 /mnt2 rw,noatime master:1 - ext3 /dev/root rw`: the
/// mount point is the 5th field; after the optional fields, a lone `-`, then
/// the filesystem type and the source.
fn parse_mountinfo_line(line: &str) -> Option<MountEntry<'_>> {
    let mut fields = line.split(' ');
    let mount_point = fields.nth(4)?;
    fields.find(|f| *f == "-")?;
    Some(MountEntry {
        mount_point,
        fstype: fields.next()?,
        source: fields.next()?,
    })
}

/// mountinfo escapes space, tab, newline and backslash as `\ooo` octal.
fn unescape(field: &str) -> String {
    let bytes = field.as_bytes();
    let mut out = Vec::with_capacity(bytes.len());
    let mut i = 0;
    while i < bytes.len() {
        let octal = bytes
            .get(i + 1..i + 4)
            .filter(|d| bytes[i] == b'\\' && d.iter().all(|b| (b'0'..=b'7').contains(b)));
        match octal {
            Some(d) => {
                out.push((d[0] - b'0') * 64 + (d[1] - b'0') * 8 + (d[2] - b'0'));
                i += 4;
            }
            None => {
                out.push(bytes[i]);
                i += 1;
            }
        }
    }
    String::from_utf8_lossy(&out).into_owned()
}

/// `hive-<label>-<UTC timestamp>`, with anything ZFS doesn't allow in a
/// snapshot name (it takes letters, digits and `-_.:`) replaced by `-`.
pub fn snapshot_name(label: &str, now: chrono::DateTime<chrono::Utc>) -> String {
    let label: String = label
        .chars()
        .map(|c| {
            if c.is_ascii_alphanumeric() || matches!(c, '-' | '_' | '.' | ':') {
                c
            } else {
                '-'
            }
        })
        .collect();
    format!(
        "{SNAPSHOT_PREFIX}{}-{}",
        label.trim_matches('-'),
        now.format("%Y%m%d-%H%M%S")
    )
}

/// [`snapshot_name`] as of now.
pub fn snapshot_name_now(label: &str) -> String {
    snapshot_name(label, chrono::Utc::now())
}

/// `zfs snapshot -r <dataset>@<name>` for each of `datasets`, in order.
/// Recursive, because the system is more than one dataset: Ubuntu's layout
/// splits `/var/lib/dpkg`, `/var/lib/apt`, `/usr/local` and friends into
/// children of the root dataset, and a package change rolled back without
/// its dpkg database would leave the system lying about what is installed.
///
/// One `zfs` call per pool: a recursive snapshot is atomic within its pool,
/// but ZFS refuses to take snapshots in several pools in one call ("multiple
/// snapshots of same fs not allowed", even for `rpool` + `bpool`). Callers
/// snapshot right before changing anything, so the pools can't drift apart
/// in between. Returns the snapshot names created; on failure, the error
/// names any that were already taken.
pub fn create_snapshots(datasets: &[String], name: &str) -> anyhow::Result<Vec<String>> {
    create_snapshots_with("zfs", datasets, name)
}

/// [`create_snapshots`] with a specific `zfs` program (tests use a stand-in).
pub fn create_snapshots_with(
    zfs: impl AsRef<std::ffi::OsStr>,
    datasets: &[String],
    name: &str,
) -> anyhow::Result<Vec<String>> {
    if datasets.is_empty() {
        anyhow::bail!("no datasets to snapshot");
    }
    let mut taken = Vec::new();
    for dataset in datasets {
        let snapshot = format!("{dataset}@{name}");
        let output = Command::new(zfs.as_ref())
            .args(["snapshot", "-r", &snapshot])
            .output()
            .map_err(|e| anyhow::anyhow!("could not run zfs: {e}"))?;
        if !output.status.success() {
            let already = if taken.is_empty() {
                String::new()
            } else {
                format!(" (already taken: {})", taken.join(" "))
            };
            anyhow::bail!(
                "zfs snapshot {snapshot} failed: {}{already}",
                String::from_utf8_lossy(&output.stderr).trim()
            );
        }
        taken.push(snapshot);
    }
    Ok(taken)
}

/// When the Hive took a snapshot, from its name: `hive-...-YYYYmmdd-HHMMSS`
/// (see [`snapshot_name`]). `None` for anything else - including every
/// snapshot the Hive didn't name, which pruning must never touch.
pub fn hive_snapshot_time(name: &str) -> Option<chrono::DateTime<chrono::Utc>> {
    let rest = name.strip_prefix(SNAPSHOT_PREFIX)?;
    let stamp = rest.get(rest.len().checked_sub(15)?..)?;
    if rest.len() > 15 && !rest[..rest.len() - 15].ends_with('-') {
        return None;
    }
    let naive = chrono::NaiveDateTime::parse_from_str(stamp, "%Y%m%d-%H%M%S").ok()?;
    Some(naive.and_utc())
}

/// Which of a dataset's snapshot names to prune: Hive snapshots older than
/// `prune_after_days`, sparing the `keep_newest` most recent Hive snapshots
/// whatever their age. Oldest first.
pub fn snapshots_to_prune(
    names: &[String],
    now: chrono::DateTime<chrono::Utc>,
    prune_after_days: u32,
    keep_newest: u32,
) -> Vec<String> {
    let mut hive: Vec<(chrono::DateTime<chrono::Utc>, &String)> = names
        .iter()
        .filter_map(|name| hive_snapshot_time(name).map(|time| (time, name)))
        .collect();
    // Newest first; the name breaks ties between snapshots of one second.
    hive.sort_by(|a, b| b.0.cmp(&a.0).then_with(|| b.1.cmp(a.1)));
    let cutoff = now - chrono::Duration::days(i64::from(prune_after_days));
    let mut prune: Vec<String> = hive
        .into_iter()
        .skip(keep_newest as usize)
        .filter(|(time, _)| *time < cutoff)
        .map(|(_, name)| name.clone())
        .collect();
    prune.reverse();
    prune
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;

    #[test]
    fn a_hive_snapshot_is_dated_by_its_name() {
        let t = |name: &str| hive_snapshot_time(name);
        assert_eq!(
            t("hive-before-install-nginx-20260910-170509"),
            Some(chrono::Utc.with_ymd_and_hms(2026, 9, 10, 17, 5, 9).unwrap())
        );
        assert!(t("hive-20260910-170509").is_some());
        // Not the Hive's, or not a name it gives.
        assert_eq!(t("admin-before-upgrade-20260910-170509"), None);
        assert_eq!(t("hive-before-install-nginx"), None);
        assert_eq!(t("hive-before-install-x20260910-170509"), None);
        assert_eq!(t("hive-before-install-nginx-20261310-170509"), None);
        assert_eq!(t("hive-"), None);
    }

    #[test]
    fn pruning_spares_recent_snapshots_the_newest_few_and_everyone_elses() {
        let now = chrono::Utc.with_ymd_and_hms(2026, 9, 30, 12, 0, 0).unwrap();
        let names: Vec<String> = [
            "hive-before-install-a-20260101-000000", // old
            "hive-before-install-b-20260102-000000", // old
            "hive-before-install-c-20260103-000000", // old, but among the newest 3 old ones
            "hive-before-install-d-20260925-000000", // recent
            "manual-backup-20200101",                // not the Hive's
            "hive-before-install-e-20260926-000000", // recent
        ]
        .iter()
        .map(|s| s.to_string())
        .collect();

        assert_eq!(
            snapshots_to_prune(&names, now, 14, 3),
            vec![
                "hive-before-install-a-20260101-000000",
                "hive-before-install-b-20260102-000000",
            ]
        );
        // keep_newest protects old ones too when there is nothing newer.
        assert!(snapshots_to_prune(&names[..3], now, 14, 3).is_empty());
        assert_eq!(snapshots_to_prune(&names, now, 14, 0).len(), 3);
        // Nothing is old enough under a long enough retention.
        assert!(snapshots_to_prune(&names, now, 3650, 0).is_empty());
    }

    /// From a real DruidOS install with the Ubuntu installer's ZFS layout
    /// (the lab's golden disk), trimmed to a representative subset.
    const UBUNTU_ZFS: &str = "\
31 1 0:28 / / rw,relatime shared:1 - zfs rpool/ROOT/ubuntu_52tka7 rw,xattr,posixacl,casesensitive
25 31 0:23 / /sys rw,nosuid,nodev,noexec,relatime shared:7 - sysfs sysfs rw
33 31 0:30 / /usr/local rw,relatime shared:3 - zfs rpool/ROOT/ubuntu_52tka7/usr/local rw,xattr,posixacl,casesensitive
35 31 0:32 / /var/lib rw,relatime shared:5 - zfs rpool/ROOT/ubuntu_52tka7/var/lib rw,xattr,posixacl,casesensitive
39 35 0:36 / /var/lib/dpkg rw,relatime shared:9 - zfs rpool/ROOT/ubuntu_52tka7/var/lib/dpkg rw,xattr,posixacl,casesensitive
61 31 0:51 / /home rw,nodev,relatime shared:72 - zfs rpool/USERDATA/home_hcs2ks rw,xattr,posixacl,casesensitive
65 31 0:50 / /boot rw,nodev,relatime shared:76 - zfs bpool/BOOT/ubuntu_52tka7 rw,xattr,posixacl,casesensitive
66 65 259:1 / /boot/efi rw,relatime shared:78 - vfat /dev/vda1 rw,fmask=0077
";

    #[test]
    fn the_root_dataset_is_whatever_zfs_dataset_is_mounted_at_slash() {
        assert_eq!(
            dataset_containing(UBUNTU_ZFS, Path::new("/")).as_deref(),
            Some("rpool/ROOT/ubuntu_52tka7")
        );
    }

    #[test]
    fn a_path_belongs_to_its_deepest_mount() {
        let at = |p: &str| dataset_containing(UBUNTU_ZFS, Path::new(p));
        assert_eq!(at("/etc/hive").as_deref(), Some("rpool/ROOT/ubuntu_52tka7"));
        assert_eq!(
            at("/var/lib/dpkg/status").as_deref(),
            Some("rpool/ROOT/ubuntu_52tka7/var/lib/dpkg")
        );
        assert_eq!(
            at("/home/druid/notes").as_deref(),
            Some("rpool/USERDATA/home_hcs2ks")
        );
        // Component-wise: /homestead is not under /home.
        assert_eq!(
            at("/homestead").as_deref(),
            Some("rpool/ROOT/ubuntu_52tka7")
        );
        // The ESP is vfat: nothing to snapshot there.
        assert_eq!(at("/boot/efi/EFI"), None);
    }

    #[test]
    fn the_system_is_the_root_and_boot_datasets() {
        assert_eq!(
            system_datasets_in(UBUNTU_ZFS),
            vec!["rpool/ROOT/ubuntu_52tka7", "bpool/BOOT/ubuntu_52tka7"]
        );
        // /boot as a child dataset of the root one, or not on ZFS at all.
        let one_pool = "\
24 1 0:22 / / rw - zfs rpool/ROOT/druidos rw
25 24 0:23 / /boot rw - zfs rpool/ROOT/druidos/boot rw
";
        assert_eq!(system_datasets_in(one_pool), vec!["rpool/ROOT/druidos"]);
        let ext4_boot = "\
24 1 0:22 / / rw - zfs rpool/ROOT/druidos rw
25 24 252:1 / /boot rw - ext4 /dev/vda2 rw
";
        assert_eq!(system_datasets_in(ext4_boot), vec!["rpool/ROOT/druidos"]);
    }

    #[test]
    fn a_non_zfs_root_has_nothing_to_snapshot() {
        let ext4 = "24 1 252:1 / / rw,relatime shared:1 - ext4 /dev/vda2 rw\n";
        assert_eq!(dataset_containing(ext4, Path::new("/")), None);
        assert!(system_datasets_in(ext4).is_empty());
        assert!(system_datasets_in("").is_empty());
        let zfs_boot_only = "\
24 1 252:1 / / rw - ext4 /dev/vda2 rw
25 24 0:23 / /boot rw - zfs bpool/BOOT/x rw
";
        assert!(system_datasets_in(zfs_boot_only).is_empty());
    }

    #[test]
    fn the_last_mount_stacked_on_a_mount_point_wins() {
        let stacked = "\
24 1 252:1 / / rw - ext4 /dev/vda2 rw
90 24 0:50 / / rw - zfs rpool/ROOT/druidos rw
";
        assert_eq!(
            dataset_containing(stacked, Path::new("/")).as_deref(),
            Some("rpool/ROOT/druidos")
        );
    }

    #[test]
    fn escaped_mount_points_and_sources_are_decoded() {
        let spaced = "\
24 1 0:22 / / rw - ext4 /dev/vda2 rw
80 24 0:45 / /srv/my\\040data rw - zfs tank/my\\040data rw
";
        assert_eq!(
            dataset_containing(spaced, Path::new("/srv/my data/x")).as_deref(),
            Some("tank/my data")
        );
    }

    #[test]
    fn optional_fields_do_not_shift_the_parse() {
        let many = "24 1 0:22 / / rw shared:1 master:2 propagate_from:3 - zfs rpool/ROOT/d rw\n";
        assert_eq!(
            dataset_containing(many, Path::new("/")).as_deref(),
            Some("rpool/ROOT/d")
        );
    }

    #[test]
    fn snapshot_names_are_prefixed_timestamped_and_valid_for_zfs() {
        let now = chrono::Utc.with_ymd_and_hms(2026, 9, 10, 17, 5, 9).unwrap();
        assert_eq!(
            snapshot_name("before-install-nginx", now),
            "hive-before-install-nginx-20260910-170509"
        );
        assert_eq!(
            snapshot_name("before-install-g++ ./x@y", now),
            "hive-before-install-g---.-x-y-20260910-170509"
        );
    }

    #[cfg(unix)]
    #[test]
    fn snapshots_are_taken_recursively_one_zfs_call_per_dataset() {
        use std::os::unix::fs::PermissionsExt;

        let dir = tempfile::tempdir().unwrap();
        let args_file = dir.path().join("args");
        // Records each call; fails any snapshot of a dataset in `bpool`
        // when told to, like a pool without the permission would.
        let fake = |name: &str, fail_bpool: bool| {
            let path = dir.path().join(name);
            let fail = if fail_bpool {
                "case \"$3\" in bpool/*) echo 'permission denied' >&2; exit 1;; esac\n"
            } else {
                ""
            };
            std::fs::write(
                &path,
                format!(
                    "#!/bin/sh\necho \"$@\" >> '{}'\n{fail}exit 0\n",
                    args_file.display()
                ),
            )
            .unwrap();
            std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
            path
        };
        let system = vec!["rpool/ROOT/d".to_string(), "bpool/BOOT/d".to_string()];

        let ok = fake("zfs-ok", false);
        assert_eq!(
            create_snapshots_with(&ok, &system, "hive-x").unwrap(),
            vec!["rpool/ROOT/d@hive-x", "bpool/BOOT/d@hive-x"]
        );
        assert_eq!(
            std::fs::read_to_string(&args_file).unwrap(),
            "snapshot -r rpool/ROOT/d@hive-x\nsnapshot -r bpool/BOOT/d@hive-x\n"
        );

        let failing = fake("zfs-fail", true);
        let err = create_snapshots_with(&failing, &system, "hive-x")
            .unwrap_err()
            .to_string();
        assert!(
            err.contains("bpool/BOOT/d@hive-x failed: permission denied")
                && err.contains("already taken: rpool/ROOT/d@hive-x"),
            "{err}"
        );

        assert!(create_snapshots_with(&ok, &[], "hive-x").is_err());
    }
}
