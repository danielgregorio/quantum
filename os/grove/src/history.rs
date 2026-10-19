//! Command history management
//!
//! Stores and retrieves command history for the shell.

use std::collections::VecDeque;

/// Maximum history entries to keep
const MAX_HISTORY: usize = 1000;

/// Command history
pub struct History {
    /// History entries (most recent last)
    entries: VecDeque<String>,
    /// Current position when navigating history
    position: usize,
    /// Maximum entries to keep
    max_entries: usize,
}

impl History {
    /// Create a new history
    pub fn new() -> Self {
        Self {
            entries: VecDeque::with_capacity(MAX_HISTORY),
            position: 0,
            max_entries: MAX_HISTORY,
        }
    }

    /// Create with custom max entries
    pub fn with_capacity(max_entries: usize) -> Self {
        Self {
            entries: VecDeque::with_capacity(max_entries),
            position: 0,
            max_entries,
        }
    }

    /// Add a command to history
    pub fn add(&mut self, command: &str) {
        let command = command.trim();
        if command.is_empty() {
            return;
        }

        // Don't add duplicates of the last command
        if self.entries.back().map(|s| s.as_str()) == Some(command) {
            return;
        }

        self.entries.push_back(command.to_string());

        // Trim if over capacity
        while self.entries.len() > self.max_entries {
            self.entries.pop_front();
        }

        // Reset position to end
        self.position = self.entries.len();
    }

    /// Get the previous command (move back in history)
    pub fn previous(&mut self) -> Option<&str> {
        if self.entries.is_empty() {
            return None;
        }

        if self.position > 0 {
            self.position -= 1;
        }

        self.entries.get(self.position).map(|s| s.as_str())
    }

    /// Get the next command (move forward in history)
    pub fn next_entry(&mut self) -> Option<&str> {
        if self.position < self.entries.len() {
            self.position += 1;
        }

        if self.position >= self.entries.len() {
            None // At the end, return empty
        } else {
            self.entries.get(self.position).map(|s| s.as_str())
        }
    }

    /// Reset position to the end (most recent)
    pub fn reset_position(&mut self) {
        self.position = self.entries.len();
    }

    /// Get the current position
    pub fn position(&self) -> usize {
        self.position
    }

    /// Get the total number of entries
    pub fn len(&self) -> usize {
        self.entries.len()
    }

    /// Check if history is empty
    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Get entry by index (0 = oldest)
    pub fn get(&self, index: usize) -> Option<&str> {
        self.entries.get(index).map(|s| s.as_str())
    }

    /// Get the last n entries
    pub fn last_n(&self, n: usize) -> Vec<&str> {
        let start = self.entries.len().saturating_sub(n);
        self.entries
            .iter()
            .skip(start)
            .map(|s| s.as_str())
            .collect()
    }

    /// Search history for commands containing a pattern
    pub fn search(&self, pattern: &str) -> Vec<(usize, &str)> {
        self.entries
            .iter()
            .enumerate()
            .filter(|(_, cmd)| cmd.contains(pattern))
            .map(|(i, cmd)| (i, cmd.as_str()))
            .collect()
    }

    /// Search backwards from current position
    pub fn search_backward(&mut self, pattern: &str) -> Option<&str> {
        if pattern.is_empty() {
            return self.previous();
        }

        let start = if self.position > 0 {
            self.position - 1
        } else {
            return None;
        };

        for i in (0..=start).rev() {
            if let Some(entry) = self.entries.get(i) {
                if entry.contains(pattern) {
                    self.position = i;
                    return Some(entry.as_str());
                }
            }
        }

        None
    }

    /// Clear all history
    pub fn clear(&mut self) {
        self.entries.clear();
        self.position = 0;
    }

    /// Get all entries as an iterator
    pub fn iter(&self) -> impl Iterator<Item = &str> {
        self.entries.iter().map(|s| s.as_str())
    }
}

impl Default for History {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_history_add() {
        let mut history = History::new();
        history.add("ls");
        history.add("pwd");
        history.add("cd /");

        assert_eq!(history.len(), 3);
    }

    #[test]
    fn test_history_navigation() {
        let mut history = History::new();
        history.add("first");
        history.add("second");
        history.add("third");

        assert_eq!(history.previous(), Some("third"));
        assert_eq!(history.previous(), Some("second"));
        assert_eq!(history.previous(), Some("first"));
        assert_eq!(history.previous(), Some("first")); // Stay at beginning

        assert_eq!(history.next_entry(), Some("second"));
        assert_eq!(history.next_entry(), Some("third"));
        assert_eq!(history.next_entry(), None); // At end
    }

    #[test]
    fn test_history_no_duplicates() {
        let mut history = History::new();
        history.add("ls");
        history.add("ls");
        history.add("ls");

        assert_eq!(history.len(), 1);
    }

    #[test]
    fn test_history_search() {
        let mut history = History::new();
        history.add("git status");
        history.add("git commit -m test");
        history.add("git push");
        history.add("ls -la");

        let results = history.search("git");
        assert_eq!(results.len(), 3);
    }

    #[test]
    fn test_history_last_n() {
        let mut history = History::new();
        history.add("one");
        history.add("two");
        history.add("three");

        let last = history.last_n(2);
        assert_eq!(last, vec!["two", "three"]);
    }
}
