//! Time and timing utilities for DruidOS
//!
//! Provides monotonic time, sleeping, and frame timing.
//! Used by SPORE for frame rate limiting and animations.

use std::time::Duration;

/// Get current monotonic time in milliseconds
///
/// Uses CLOCK_MONOTONIC for consistent timing that doesn't
/// jump when system time changes.
pub fn get_time_ms() -> u64 {
    let mut ts = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };

    unsafe {
        libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut ts);
    }

    (ts.tv_sec as u64) * 1000 + (ts.tv_nsec as u64) / 1_000_000
}

/// Get current monotonic time in microseconds (higher precision)
pub fn get_time_us() -> u64 {
    let mut ts = libc::timespec {
        tv_sec: 0,
        tv_nsec: 0,
    };

    unsafe {
        libc::clock_gettime(libc::CLOCK_MONOTONIC, &mut ts);
    }

    (ts.tv_sec as u64) * 1_000_000 + (ts.tv_nsec as u64) / 1_000
}

/// Sleep for the specified number of milliseconds
pub fn sleep_ms(ms: u64) {
    std::thread::sleep(Duration::from_millis(ms));
}

/// Sleep for the specified number of microseconds
pub fn sleep_us(us: u64) {
    std::thread::sleep(Duration::from_micros(us));
}

/// High-precision instant for measuring elapsed time
#[derive(Debug, Clone, Copy)]
pub struct Instant {
    time_us: u64,
}

impl Instant {
    /// Create a new instant representing "now"
    pub fn now() -> Self {
        Self {
            time_us: get_time_us(),
        }
    }

    /// Get elapsed time since this instant in milliseconds
    pub fn elapsed_ms(&self) -> u64 {
        let now = get_time_us();
        (now.saturating_sub(self.time_us)) / 1000
    }

    /// Get elapsed time since this instant in microseconds
    pub fn elapsed_us(&self) -> u64 {
        let now = get_time_us();
        now.saturating_sub(self.time_us)
    }

    /// Check if at least `ms` milliseconds have elapsed
    pub fn has_elapsed_ms(&self, ms: u64) -> bool {
        self.elapsed_ms() >= ms
    }

    /// Reset the instant to "now"
    pub fn reset(&mut self) {
        self.time_us = get_time_us();
    }
}

impl Default for Instant {
    fn default() -> Self {
        Self::now()
    }
}

/// Frame timer for consistent frame rates
///
/// Used by SPORE to maintain target FPS.
#[derive(Debug)]
pub struct FrameTimer {
    /// Target frame time in microseconds
    target_frame_us: u64,
    /// Last frame start time
    last_frame: Instant,
    /// Accumulated frame times for FPS calculation
    frame_times: [u64; 60],
    /// Current frame index
    frame_index: usize,
    /// Total frames counted
    frame_count: u64,
}

impl FrameTimer {
    /// Create a new frame timer with target FPS
    pub fn new(target_fps: u32) -> Self {
        Self {
            target_frame_us: 1_000_000 / target_fps as u64,
            last_frame: Instant::now(),
            frame_times: [0; 60],
            frame_index: 0,
            frame_count: 0,
        }
    }

    /// Create a timer for 60 FPS (default for SPORE)
    pub fn fps_60() -> Self {
        Self::new(60)
    }

    /// Start timing a new frame
    pub fn begin_frame(&mut self) {
        self.last_frame = Instant::now();
    }

    /// End the frame and sleep to maintain target FPS
    ///
    /// Returns the actual frame time in microseconds.
    pub fn end_frame(&mut self) -> u64 {
        let elapsed = self.last_frame.elapsed_us();

        // Record frame time for FPS calculation
        self.frame_times[self.frame_index] = elapsed;
        self.frame_index = (self.frame_index + 1) % 60;
        self.frame_count += 1;

        // Sleep if we're ahead of target
        if elapsed < self.target_frame_us {
            let sleep_time = self.target_frame_us - elapsed;
            sleep_us(sleep_time);
        }

        elapsed
    }

    /// Get the current FPS based on recent frame times
    pub fn current_fps(&self) -> f32 {
        let count = self.frame_count.min(60) as usize;
        if count == 0 {
            return 0.0;
        }

        let total_us: u64 = self.frame_times[..count].iter().sum();
        if total_us == 0 {
            return 0.0;
        }

        (count as f32 * 1_000_000.0) / total_us as f32
    }

    /// Get the average frame time in milliseconds
    pub fn avg_frame_time_ms(&self) -> f32 {
        let count = self.frame_count.min(60) as usize;
        if count == 0 {
            return 0.0;
        }

        let total_us: u64 = self.frame_times[..count].iter().sum();
        (total_us as f32 / count as f32) / 1000.0
    }

    /// Get total frames rendered
    pub fn total_frames(&self) -> u64 {
        self.frame_count
    }

    /// Set new target FPS
    pub fn set_target_fps(&mut self, fps: u32) {
        self.target_frame_us = 1_000_000 / fps as u64;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_get_time_ms() {
        let t1 = get_time_ms();
        sleep_ms(10);
        let t2 = get_time_ms();
        assert!(t2 >= t1 + 9); // Allow some slack
    }

    #[test]
    fn test_instant_elapsed() {
        let instant = Instant::now();
        sleep_ms(50);
        let elapsed = instant.elapsed_ms();
        assert!(elapsed >= 45 && elapsed <= 100);
    }

    #[test]
    fn test_frame_timer() {
        let mut timer = FrameTimer::fps_60();

        // Simulate a few frames
        for _ in 0..5 {
            timer.begin_frame();
            sleep_ms(5); // Simulate work
            timer.end_frame();
        }

        assert!(timer.total_frames() == 5);
        assert!(timer.current_fps() > 0.0);
    }
}
