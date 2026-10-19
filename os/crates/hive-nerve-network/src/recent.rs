//! Report each conflict once, not once per retry.
//!
//! A service with `Restart=always` that can't bind its port fails again every
//! few seconds, each time logging the same error. One report per (port,
//! requester) within a window is plenty.

use std::collections::HashMap;
use std::time::{Duration, Instant};

pub struct RecentReports {
    window: Duration,
    reported: HashMap<(u16, String), Instant>,
}

impl RecentReports {
    pub fn new(window: Duration) -> Self {
        Self {
            window,
            reported: HashMap::new(),
        }
    }

    /// Whether a conflict on `port` for `requester` should be reported now;
    /// if so, it counts as reported from `now`.
    pub fn should_report(&mut self, port: u16, requester: &str, now: Instant) -> bool {
        let window = self.window;
        self.reported
            .retain(|_, at| now.saturating_duration_since(*at) < window);

        let key = (port, requester.to_string());
        if self.reported.contains_key(&key) {
            return false;
        }
        self.reported.insert(key, now);
        true
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_retrying_service_is_reported_once_per_window() {
        let mut recent = RecentReports::new(Duration::from_secs(300));
        let start = Instant::now();

        assert!(recent.should_report(80, "nginx.service", start));
        assert!(!recent.should_report(80, "nginx.service", start + Duration::from_secs(5)));
        assert!(recent.should_report(80, "nginx.service", start + Duration::from_secs(301)));
    }

    #[test]
    fn different_ports_and_requesters_are_separate_conflicts() {
        let mut recent = RecentReports::new(Duration::from_secs(300));
        let now = Instant::now();

        assert!(recent.should_report(80, "nginx.service", now));
        assert!(recent.should_report(443, "nginx.service", now));
        assert!(recent.should_report(80, "apache2.service", now));
    }
}
