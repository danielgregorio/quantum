//! Snapshot retention policy.

use chrono::{Datelike, Duration, Utc};
use serde::{Deserialize, Serialize};

use crate::snapshot::SnapshotInfo;

/// Retention policy for automatic snapshots
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RetentionPolicy {
    /// Keep all snapshots from the last N hours
    pub hourly_keep: u32,
    /// Keep daily snapshots for N days
    pub daily_keep: u32,
    /// Keep weekly snapshots for N weeks
    pub weekly_keep: u32,
    /// Keep monthly snapshots for N months
    pub monthly_keep: u32,
    /// Minimum number of snapshots to always keep
    pub min_keep: u32,
    /// Maximum total snapshots (0 = unlimited)
    pub max_total: u32,
}

impl Default for RetentionPolicy {
    fn default() -> Self {
        Self {
            hourly_keep: 24, // Keep 24 hours of hourly snapshots
            daily_keep: 7,   // Keep 7 days of daily snapshots
            weekly_keep: 4,  // Keep 4 weeks of weekly snapshots
            monthly_keep: 3, // Keep 3 months of monthly snapshots
            min_keep: 5,     // Always keep at least 5 snapshots
            max_total: 100,  // Cap at 100 total snapshots
        }
    }
}

impl RetentionPolicy {
    /// Determine which snapshots should be deleted
    pub fn snapshots_to_delete<'a>(
        &self,
        snapshots: &'a [&'a SnapshotInfo],
    ) -> Vec<&'a SnapshotInfo> {
        if snapshots.len() <= self.min_keep as usize {
            return Vec::new();
        }

        let now = Utc::now();
        let mut to_keep: Vec<&'a SnapshotInfo> = Vec::new();
        let mut to_delete: Vec<&'a SnapshotInfo> = Vec::new();

        // Sort by creation date (newest first)
        let mut sorted: Vec<&'a SnapshotInfo> = snapshots.to_vec();
        sorted.sort_by_key(|s| std::cmp::Reverse(s.creation));

        // Categorize snapshots by age
        for &snapshot in &sorted {
            let age = now.signed_duration_since(snapshot.creation);

            let should_keep = if age < Duration::hours(self.hourly_keep as i64) {
                // Within hourly window - keep all
                true
            } else if age < Duration::days(self.daily_keep as i64) {
                // Within daily window - keep if it's the first of its day
                let day = snapshot.creation.date_naive();
                !to_keep.iter().any(|s| s.creation.date_naive() == day)
            } else if age < Duration::weeks(self.weekly_keep as i64) {
                // Within weekly window - keep if it's the first of its week
                let week = snapshot.creation.date_naive().iso_week();
                !to_keep
                    .iter()
                    .any(|s| s.creation.date_naive().iso_week() == week)
            } else if age < Duration::days((self.monthly_keep * 30) as i64) {
                // Within monthly window - keep if it's the first of its month
                let month = (snapshot.creation.year(), snapshot.creation.month());
                !to_keep
                    .iter()
                    .any(|s| (s.creation.year(), s.creation.month()) == month)
            } else {
                // Older than retention window
                false
            };

            if should_keep {
                to_keep.push(snapshot);
            } else {
                to_delete.push(snapshot);
            }
        }

        // Ensure we keep minimum
        while to_keep.len() < self.min_keep as usize && !to_delete.is_empty() {
            if let Some(snapshot) = to_delete.pop() {
                to_keep.push(snapshot);
            }
        }

        // Enforce maximum if set
        if self.max_total > 0 {
            while to_keep.len() > self.max_total as usize {
                // Remove oldest from keep list
                if let Some(oldest) = to_keep.pop() {
                    to_delete.push(oldest);
                }
            }
        }

        to_delete
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::Duration;

    fn make_snapshot(name: &str, hours_ago: i64) -> SnapshotInfo {
        SnapshotInfo {
            dataset: "rpool/ROOT/druidos".to_string(),
            name: format!("hive-auto-{}", name),
            creation: Utc::now() - Duration::hours(hours_ago),
            used: 1024,
            referenced: 2048,
        }
    }

    #[test]
    fn test_retention_keeps_minimum() {
        let policy = RetentionPolicy {
            min_keep: 3,
            ..Default::default()
        };

        let snapshots = [
            make_snapshot("1", 100 * 24), // Very old
            make_snapshot("2", 99 * 24),
            make_snapshot("3", 98 * 24),
        ];

        let refs: Vec<_> = snapshots.iter().collect();
        let to_delete = policy.snapshots_to_delete(&refs);

        // Should keep all because of min_keep
        assert_eq!(to_delete.len(), 0);
    }

    #[test]
    fn test_retention_keeps_recent() {
        let policy = RetentionPolicy {
            hourly_keep: 24,
            min_keep: 0,
            ..Default::default()
        };

        let snapshots = [
            make_snapshot("1", 1),  // 1 hour ago
            make_snapshot("2", 2),  // 2 hours ago
            make_snapshot("3", 48), // 2 days ago
        ];

        let refs: Vec<_> = snapshots.iter().collect();
        let to_delete = policy.snapshots_to_delete(&refs);

        // Recent ones should be kept
        assert!(to_delete.len() <= 1);
    }

    #[test]
    fn test_empty_list() {
        let policy = RetentionPolicy::default();
        let snapshots: Vec<&SnapshotInfo> = vec![];
        let to_delete = policy.snapshots_to_delete(&snapshots);
        assert!(to_delete.is_empty());
    }
}
