//! Watching whole directory trees as an unprivileged observer.
//!
//! inotify watches are per directory. notify's `RecursiveMode::Recursive`
//! adds them for a whole tree, but aborts the walk at the first directory it
//! may not watch — and `hive-nerve-fs` runs as `_hive-sense`, so that happens
//! right away (`/etc/ssl/private`, `/etc/credstore`, 0750 home directories),
//! leaving everything after that point silently unwatched. Here each
//! directory is watched on its own, and only the ones that fail are skipped.

use std::path::{Path, PathBuf};

/// Outcome of watching a directory tree.
#[derive(Debug, Default, PartialEq, Eq)]
pub struct TreeWatch {
    /// Directories now being watched.
    pub watched: usize,
    /// Directories that could not be watched or listed. Nothing below them
    /// is covered.
    pub skipped: Vec<PathBuf>,
}

/// Watch `root` and every directory below it, calling `watch_dir` once per
/// directory. Symlinks are not followed (no loops, no escaping the tree).
///
/// A directory that can't be watched or listed goes into
/// [`TreeWatch::skipped`] and isn't descended into; the rest of the tree is
/// still walked.
pub fn watch_tree<E>(root: &Path, mut watch_dir: impl FnMut(&Path) -> Result<(), E>) -> TreeWatch {
    let mut result = TreeWatch::default();
    let mut pending = vec![root.to_path_buf()];

    while let Some(dir) = pending.pop() {
        if watch_dir(&dir).is_err() {
            result.skipped.push(dir);
            continue;
        }
        result.watched += 1;

        let entries = match std::fs::read_dir(&dir) {
            Ok(entries) => entries,
            Err(_) => {
                result.skipped.push(dir);
                continue;
            }
        };
        for entry in entries.flatten() {
            // file_type() doesn't follow symlinks: a link to a directory
            // reports as a symlink and is left alone.
            if entry.file_type().is_ok_and(|t| t.is_dir()) {
                pending.push(entry.path());
            }
        }
    }

    result.skipped.sort();
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;

    #[test]
    fn watches_every_directory_but_not_files_or_symlinks() {
        let root = tempfile::tempdir().unwrap();
        fs::create_dir_all(root.path().join("a/b")).unwrap();
        fs::create_dir(root.path().join("c")).unwrap();
        fs::write(root.path().join("a/file.conf"), "x").unwrap();
        std::os::unix::fs::symlink(root.path(), root.path().join("c/loop")).unwrap();

        let mut seen = Vec::new();
        let result = watch_tree(root.path(), |dir| {
            seen.push(dir.to_path_buf());
            Ok::<_, ()>(())
        });

        seen.sort();
        let mut expected = vec![
            root.path().to_path_buf(),
            root.path().join("a"),
            root.path().join("a/b"),
            root.path().join("c"),
        ];
        expected.sort();
        assert_eq!(seen, expected);
        assert_eq!(
            result,
            TreeWatch {
                watched: 4,
                skipped: vec![]
            }
        );
    }

    #[test]
    fn a_directory_that_cant_be_watched_is_skipped_without_losing_the_rest() {
        // What notify's recursive mode got wrong: one forbidden directory
        // (think /etc/ssl/private) must not cost the watches on its siblings
        // or on anything walked after it.
        let root = tempfile::tempdir().unwrap();
        let denied = root.path().join("private");
        fs::create_dir_all(denied.join("inside")).unwrap();
        fs::create_dir_all(root.path().join("sibling/child")).unwrap();

        let mut seen = Vec::new();
        let result = watch_tree(root.path(), |dir| {
            seen.push(dir.to_path_buf());
            if dir == denied {
                Err("permission denied")
            } else {
                Ok(())
            }
        });

        assert_eq!(result.watched, 3); // root, sibling, sibling/child
        assert_eq!(result.skipped, vec![denied.clone()]);
        assert!(seen.contains(&root.path().join("sibling/child")));
        assert!(
            !seen.contains(&denied.join("inside")),
            "must not descend into a directory it couldn't watch"
        );
    }

    #[test]
    fn a_root_that_cant_be_watched_is_reported_as_skipped() {
        let root = tempfile::tempdir().unwrap();

        let result = watch_tree(root.path(), |_| Err(()));

        assert_eq!(
            result,
            TreeWatch {
                watched: 0,
                skipped: vec![root.path().to_path_buf()]
            }
        );
    }
}
