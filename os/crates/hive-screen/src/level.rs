//! The presentation levels: what the screen affords with the cores the
//! machine gives it, chosen by the frame time it measures. `plain` is the
//! scene as declared, without particles, drawn 15 times a second at most;
//! `effects` adds the particles, at 30; `fine` draws the scene with two
//! pixels to the scene's one (positions keep their fractions, particles
//! their size) and the effects a scene keeps for it (`qs:emitter
//! level="2"`). A level never changes what happens, only how it shows:
//! the same ticks run at every level, and a frame at a level is the same
//! picture however many threads draw it.
//!
//! The chooser climbs while frames are cheap and comes down when they are
//! dear, never above the ceiling the cores set, read as the daemon runs
//! (a vCPU plugged in counts within half a second).

use std::time::{Duration, Instant};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Level {
    pub name: &'static str,
    /// Canvas pixels per scene pixel.
    pub scale: u32,
    /// Whether particles play at all.
    pub effects: bool,
    /// Pictures a second, at most.
    pub fps: u32,
    /// The cores a machine needs for the level to be on offer.
    pub cores: usize,
}

pub const LEVELS: [Level; 3] = [
    Level {
        name: "plain",
        scale: 1,
        effects: false,
        fps: 15,
        cores: 1,
    },
    Level {
        name: "effects",
        scale: 1,
        effects: true,
        fps: 30,
        cores: 2,
    },
    Level {
        name: "fine",
        scale: 2,
        effects: true,
        fps: 30,
        cores: 4,
    },
];

/// The level a scene plays at with no chooser: the lab, the tests and
/// `--play` draw the scene as declared, with its effects.
pub const DEFAULT: usize = 1;

impl Level {
    pub fn period(&self) -> Duration {
        Duration::from_secs_f64(1.0 / self.fps as f64)
    }

    pub fn describe(&self, scene: (u32, u32)) -> String {
        format!(
            "{}x{}, effects {}, {} fps",
            scene.0 * self.scale,
            scene.1 * self.scale,
            if self.effects { "on" } else { "off" },
            self.fps
        )
    }
}

/// The highest level that many cores are enough for.
pub fn ceiling(cores: usize) -> usize {
    LEVELS.iter().rposition(|l| l.cores <= cores).unwrap_or(0)
}

/// A frame under this share of its level's period, over enough frames,
/// makes the level above affordable.
const CALM: f64 = 0.15;
/// A frame over this share of its level's period brings the level down.
const BUSY: f64 = 0.6;
/// Frames measured at a level before judging it.
pub const FRAMES_TO_JUDGE: u32 = 20;
/// Time at a level before climbing from it.
const SETTLE: Duration = Duration::from_secs(2);
/// After a level proved too dear, how long before trying it again.
const HOLD_AFTER_A_DROP: Duration = Duration::from_secs(30);

pub struct Chooser {
    level: usize,
    /// A level pinned from outside (HIVE_SCREEN_LEVEL): never changed.
    pinned: bool,
    cores: usize,
    /// The frame cost, smoothed, in seconds, since the level began.
    ema: Option<f64>,
    frames: u32,
    since: Instant,
    no_climb_before: Instant,
    /// The last smoothed cost at the level before this one.
    before: f64,
    /// The smoothed cost when the level was first judged, to say once.
    judged: Option<f64>,
}

impl Chooser {
    /// Starts at the default level, or under the cores' ceiling.
    pub fn new(cores: usize, now: Instant) -> Chooser {
        Chooser {
            level: DEFAULT.min(ceiling(cores)),
            pinned: false,
            cores,
            ema: None,
            frames: 0,
            since: now,
            no_climb_before: now,
            before: 0.0,
            judged: None,
        }
    }

    /// The smoothed frame cost at this level, in milliseconds, the first
    /// time the level has enough frames to be judged on; then nothing.
    pub fn take_judged_ms(&mut self) -> Option<f64> {
        self.judged.take().map(|s| s * 1000.0)
    }

    /// Pinned at `level` whatever the frames and the cores say: for an
    /// administrator who knows better than the measure.
    pub fn pinned(level: usize, cores: usize, now: Instant) -> Chooser {
        let mut c = Chooser::new(cores, now);
        c.level = level.min(LEVELS.len() - 1);
        c.pinned = true;
        c
    }

    pub fn level(&self) -> usize {
        self.level
    }

    /// Whether the level was pinned from outside.
    pub fn is_pinned(&self) -> bool {
        self.pinned
    }

    pub fn cores(&self) -> usize {
        self.cores
    }

    /// Threads to draw with: one a core, up to eight.
    pub fn threads(&self) -> usize {
        self.cores.clamp(1, 8)
    }

    /// The smoothed frame cost at the level before this one, in
    /// milliseconds: what the change was decided on.
    pub fn before_ms(&self) -> f64 {
        self.before * 1000.0
    }

    /// The cores now. A level above their ceiling comes down at once.
    /// Whether the count changed.
    pub fn set_cores(&mut self, cores: usize, now: Instant) -> bool {
        if cores == self.cores {
            return false;
        }
        self.cores = cores;
        let top = ceiling(cores);
        if self.level > top && !self.pinned {
            self.go(top, now);
        }
        true
    }

    /// A frame drawn and presented in `cost`: the level it leads to, when
    /// it changes one.
    pub fn frame(&mut self, cost: Duration, now: Instant) -> Option<usize> {
        if self.pinned {
            return None;
        }
        let cost = cost.as_secs_f64();
        let ema = match self.ema {
            None => cost,
            Some(e) => e * 0.8 + cost * 0.2,
        };
        self.ema = Some(ema);
        self.frames += 1;
        if self.frames < FRAMES_TO_JUDGE {
            return None;
        }
        if self.frames == FRAMES_TO_JUDGE {
            self.judged = Some(ema);
        }
        let period = LEVELS[self.level].period().as_secs_f64();
        if ema > period * BUSY && self.level > 0 {
            self.no_climb_before = now + HOLD_AFTER_A_DROP;
            self.go(self.level - 1, now);
            return Some(self.level);
        }
        let next = self.level + 1;
        if next <= ceiling(self.cores)
            && ema < period * CALM
            && now >= self.no_climb_before
            && now.duration_since(self.since) >= SETTLE
        {
            self.go(next, now);
            return Some(next);
        }
        None
    }

    fn go(&mut self, level: usize, now: Instant) {
        self.before = self.ema.unwrap_or(0.0);
        self.level = level;
        self.ema = None;
        self.frames = 0;
        self.since = now;
        self.judged = None;
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn ms(n: u64) -> Duration {
        Duration::from_millis(n)
    }

    #[test]
    fn the_cores_set_the_ceiling() {
        assert_eq!(ceiling(1), 0);
        assert_eq!(ceiling(2), 1);
        assert_eq!(ceiling(3), 1);
        assert_eq!(ceiling(4), 2);
        assert_eq!(ceiling(64), 2);
        let now = Instant::now();
        assert_eq!(Chooser::new(1, now).level(), 0);
        assert_eq!(Chooser::new(2, now).level(), 1);
        assert_eq!(Chooser::new(8, now).level(), 1, "fine is earned, not given");
        assert_eq!(Chooser::new(64, now).threads(), 8);
    }

    #[test]
    fn cheap_frames_climb_up_to_the_ceiling() {
        let t0 = Instant::now();
        let mut c = Chooser::new(2, t0);
        for i in 0..40 {
            assert_eq!(c.frame(ms(1), t0 + ms(100 * i)), None, "2 cores: no fine");
        }
        assert_eq!(c.level(), 1);
        // two more cores: the frames measured already prove the level cheap
        assert!(c.set_cores(4, t0 + ms(4000)));
        assert!(!c.set_cores(4, t0 + ms(4000)));
        assert_eq!(c.frame(ms(1), t0 + ms(4100)), Some(2));
        assert_eq!(c.level(), 2);
        assert_eq!(c.take_judged_ms(), None, "a new level is not judged yet");
        assert!((c.before_ms() - 1.0).abs() < 0.01);
        // a fresh chooser judges a level on enough frames, once settled
        let mut c = Chooser::new(4, t0);
        let mut climbed = None;
        for i in 0..40 {
            if let Some(l) = c.frame(ms(1), t0 + ms(150 * i)) {
                climbed = Some((i, l));
                break;
            }
        }
        assert_eq!(climbed, Some((u64::from(FRAMES_TO_JUDGE) - 1, 2)));
        // the level it climbed from was judged, and said so once
        let mut c = Chooser::new(2, t0);
        for i in 0..40 {
            c.frame(ms(1), t0 + ms(100 * i));
            let said = c.take_judged_ms();
            assert_eq!(said.is_some(), i == u64::from(FRAMES_TO_JUDGE) - 1, "{}", i);
            if let Some(ms_) = said {
                assert!((ms_ - 1.0).abs() < 0.01);
            }
        }
    }

    #[test]
    fn dear_frames_come_down_and_the_level_is_held_off_for_a_while() {
        let t0 = Instant::now();
        let mut c = Chooser::new(4, t0);
        assert_eq!(c.level(), 1);
        // 25 ms a frame at 30 fps: three quarters of the period
        let mut dropped = None;
        for i in 0..40 {
            if let Some(l) = c.frame(ms(25), t0 + ms(40 * i)) {
                dropped = Some(l);
                break;
            }
        }
        assert_eq!(dropped, Some(0));
        // cheap frames right after do not climb back: the level is held off
        for i in 0..100 {
            assert_eq!(c.frame(ms(1), t0 + ms(2000 + 100 * i)), None);
        }
        assert_eq!(c.level(), 0);
        // half a minute later they do
        let mut climbed = None;
        for i in 0..40 {
            if let Some(l) = c.frame(ms(1), t0 + ms(32_000 + 100 * i)) {
                climbed = Some(l);
                break;
            }
        }
        assert_eq!(climbed, Some(1));
    }

    #[test]
    fn fewer_cores_bring_a_level_down_at_once() {
        let t0 = Instant::now();
        let mut c = Chooser::new(4, t0);
        for i in 0..40 {
            c.frame(ms(1), t0 + ms(100 * i));
        }
        assert_eq!(c.level(), 2);
        assert!(c.set_cores(2, t0 + ms(5000)));
        assert_eq!(c.level(), 1);
        assert!(c.set_cores(1, t0 + ms(5000)));
        assert_eq!(c.level(), 0);
        assert_eq!(c.threads(), 1);
    }

    #[test]
    fn a_pinned_level_never_moves() {
        let t0 = Instant::now();
        let mut c = Chooser::pinned(2, 4, t0);
        assert_eq!(c.level(), 2);
        for i in 0..40 {
            assert_eq!(
                c.frame(ms(100), t0 + ms(100 * i)),
                None,
                "dear frames move it not"
            );
        }
        assert!(c.set_cores(1, t0 + ms(5000)));
        assert_eq!(c.level(), 2, "nor fewer cores");
        assert_eq!(c.take_judged_ms(), None);
        assert_eq!(Chooser::pinned(9, 4, t0).level(), 2);
    }

    #[test]
    fn a_level_says_what_it_shows() {
        assert_eq!(
            LEVELS[0].describe((320, 180)),
            "320x180, effects off, 15 fps"
        );
        assert_eq!(
            LEVELS[2].describe((320, 180)),
            "640x360, effects on, 30 fps"
        );
        assert_eq!(LEVELS[1].period(), Duration::from_secs_f64(1.0 / 30.0));
    }
}
