//! Particle effects: the games' presets (`qg:particles`), played on the
//! CPU. Only seen: nothing the screen reports depends on them, and their
//! own random numbers come from a fixed seed, so a frame is the same on
//! every run.

use crate::canvas::Band;
use crate::image::{alpha, argb, blue, green, parse_color, red};
use crate::math::{atan2, cos, sin};

#[derive(Debug, Clone)]
pub struct Preset {
    pub amount: u32,
    pub lifetime: f32,
    pub one_shot: bool,
    pub explosiveness: f32,
    pub spread: f32,
    pub direction: (f32, f32),
    pub speed: (f32, f32),
    pub gravity: (f32, f32),
    pub size: (f32, f32),
    pub color: u32,
    pub fade: bool,
    pub grow: bool,
    pub shrink: bool,
    pub streak: bool,
    pub width: bool,
    pub rainbow: bool,
}

impl Preset {
    pub fn named(name: &str) -> Option<Preset> {
        let base = Preset {
            amount: 12,
            lifetime: 0.45,
            one_shot: true,
            explosiveness: 1.0,
            spread: 180.0,
            direction: (0.0, 0.0),
            speed: (30.0, 70.0),
            gravity: (0.0, 0.0),
            size: (2.0, 3.0),
            color: 0xFFFFFFFF,
            fade: true,
            grow: false,
            shrink: false,
            streak: false,
            width: false,
            rainbow: false,
        };
        Some(match name {
            "puff" => base,
            "sparks" => Preset {
                amount: 16,
                lifetime: 0.5,
                speed: (80.0, 160.0),
                gravity: (0.0, 300.0),
                size: (1.0, 2.0),
                color: 0xFFFFD34D,
                ..base
            },
            "smoke" => Preset {
                amount: 14,
                lifetime: 1.2,
                explosiveness: 0.6,
                spread: 30.0,
                direction: (0.0, -1.0),
                speed: (15.0, 35.0),
                gravity: (0.0, -20.0),
                size: (3.0, 6.0),
                color: 0xFF8A8A8A,
                grow: true,
                ..base
            },
            "dust" => Preset {
                amount: 10,
                lifetime: 0.4,
                spread: 40.0,
                direction: (0.0, -1.0),
                speed: (20.0, 50.0),
                gravity: (0.0, 120.0),
                size: (1.5, 3.0),
                color: 0xFFC8B48C,
                ..base
            },
            "fire" => Preset {
                amount: 40,
                lifetime: 0.8,
                one_shot: false,
                explosiveness: 0.0,
                spread: 25.0,
                direction: (0.0, -1.0),
                speed: (25.0, 55.0),
                gravity: (0.0, -40.0),
                size: (3.0, 6.0),
                color: 0xFFFF8A2A,
                shrink: true,
                ..base
            },
            "rain" => Preset {
                amount: 60,
                lifetime: 0.8,
                one_shot: false,
                explosiveness: 0.0,
                spread: 2.0,
                direction: (0.1, 1.0),
                speed: (260.0, 320.0),
                size: (1.0, 1.0),
                color: 0xFF9FC4FF,
                fade: false,
                streak: true,
                width: true,
                ..base
            },
            "snow" => Preset {
                amount: 40,
                lifetime: 3.0,
                one_shot: false,
                explosiveness: 0.0,
                spread: 20.0,
                direction: (0.0, 1.0),
                speed: (15.0, 30.0),
                gravity: (0.0, 5.0),
                size: (1.5, 2.5),
                fade: false,
                width: true,
                ..base
            },
            "confetti" => Preset {
                amount: 40,
                lifetime: 1.4,
                spread: 50.0,
                direction: (0.0, -1.0),
                speed: (120.0, 220.0),
                gravity: (0.0, 260.0),
                size: (2.0, 3.0),
                fade: false,
                rainbow: true,
                ..base
            },
            "stars" => Preset {
                amount: 8,
                lifetime: 0.6,
                explosiveness: 0.8,
                speed: (15.0, 40.0),
                size: (2.0, 4.0),
                color: 0xFFFFF6A8,
                grow: true,
                ..base
            },
            _ => return None,
        })
    }

    /// The preset with a `qs:particles`' overrides, as the Godot runtime
    /// applies them: a speed or a size given is a range of 0.7 to 1.3 of it.
    pub fn with(
        mut self,
        color: Option<&str>,
        amount: Option<u32>,
        lifetime: Option<f32>,
        speed: Option<f32>,
        size: Option<f32>,
    ) -> Preset {
        if let Some(c) = color.and_then(parse_color) {
            self.color = c;
        }
        if let Some(a) = amount {
            self.amount = a.max(1);
        }
        if let Some(l) = lifetime {
            self.lifetime = l;
        }
        if let Some(s) = speed {
            self.speed = (s * 0.7, s * 1.3);
        }
        if let Some(z) = size {
            self.size = (z * 0.7, z * 1.3);
        }
        self
    }
}

/// A small deterministic generator (xorshift32): the same seed, the same
/// particles, so a frame compares exactly with a reference.
#[derive(Debug, Clone)]
pub struct Rng(u32);

impl Rng {
    pub fn new(seed: u32) -> Rng {
        Rng(if seed == 0 { 0x9E37_79B9 } else { seed })
    }

    pub fn next(&mut self) -> u32 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 17;
        x ^= x << 5;
        self.0 = x;
        x
    }

    /// Uniform in [0, 1).
    pub fn unit(&mut self) -> f32 {
        (self.next() >> 8) as f32 / (1u32 << 24) as f32
    }

    pub fn between(&mut self, lo: f32, hi: f32) -> f32 {
        lo + (hi - lo) * self.unit()
    }
}

#[derive(Debug, Clone)]
struct Particle {
    x: f32,
    y: f32,
    vx: f32,
    vy: f32,
    age: f32,
    life: f32,
    size: f32,
    color: u32,
}

/// One effect going: a burst (one shot) or an emitter (keeps going).
#[derive(Debug, Clone)]
pub struct Emitter {
    preset: Preset,
    x: f32,
    y: f32,
    width: f32,
    particles: Vec<Particle>,
    emitted: u32,
    clock: f32,
    stream: f32,
    rng: Rng,
}

const DT: f32 = 1.0 / 60.0;

impl Emitter {
    pub fn new(preset: Preset, x: f32, y: f32, width: f32, seed: u32) -> Emitter {
        Emitter {
            preset,
            x,
            y,
            width,
            particles: Vec::new(),
            emitted: 0,
            clock: 0.0,
            stream: 0.0,
            rng: Rng::new(seed),
        }
    }

    /// Whether a one-shot effect has nothing left to show.
    pub fn finished(&self) -> bool {
        self.preset.one_shot && self.emitted >= self.preset.amount && self.particles.is_empty()
    }

    fn spawn(&mut self) {
        let p = &self.preset;
        let angle = if p.direction == (0.0, 0.0) {
            self.rng.between(0.0, std::f32::consts::TAU)
        } else {
            let base = atan2(p.direction.1, p.direction.0);
            let half = p.spread.to_radians();
            base + self.rng.between(-half, half)
        };
        let speed = self.rng.between(p.speed.0, p.speed.1);
        let x = if p.width && self.width > 0.0 {
            self.x + self.rng.between(0.0, self.width)
        } else {
            self.x
        };
        let color = if p.rainbow {
            let hue = self.rng.unit();
            hsv(hue)
        } else {
            p.color
        };
        self.particles.push(Particle {
            x,
            y: self.y,
            vx: cos(angle) * speed,
            vy: sin(angle) * speed,
            age: 0.0,
            life: p.lifetime,
            size: self.rng.between(p.size.0, p.size.1),
            color,
        });
        self.emitted += 1;
    }

    pub fn tick(&mut self) {
        let p = self.preset.clone();
        if p.one_shot {
            // all at once at explosiveness 1; spread over the lifetime at 0
            let window = p.lifetime * (1.0 - p.explosiveness);
            let due = if window <= 0.0 {
                p.amount
            } else {
                ((self.clock / window) * p.amount as f32)
                    .ceil()
                    .min(p.amount as f32) as u32
            };
            while self.emitted < due.max(1) && self.emitted < p.amount {
                self.spawn();
            }
        } else {
            // a steady stream: `amount` alive at a time, each living `lifetime`
            self.stream += p.amount as f32 * DT / p.lifetime;
            while self.stream >= 1.0 {
                self.stream -= 1.0;
                if (self.particles.len() as u32) < p.amount {
                    self.spawn();
                }
            }
        }
        self.clock += DT;
        for q in &mut self.particles {
            q.vx += p.gravity.0 * DT;
            q.vy += p.gravity.1 * DT;
            q.x += q.vx * DT;
            q.y += q.vy * DT;
            q.age += DT;
        }
        self.particles.retain(|q| q.age < q.life);
    }

    pub fn draw(&self, canvas: &mut Band) {
        let p = &self.preset;
        for q in &self.particles {
            let t = (q.age / q.life).clamp(0.0, 1.0);
            let size = if p.grow {
                q.size * (0.5 + t)
            } else if p.shrink {
                q.size * (1.0 - t * 0.8)
            } else {
                q.size
            };
            let a = if p.fade {
                ((1.0 - t) * alpha(q.color) as f32) as u8
            } else {
                alpha(q.color)
            };
            let color = argb(a, red(q.color), green(q.color), blue(q.color));
            if p.streak {
                let len = 3;
                let (dx, dy) = (q.vx.signum(), q.vy.signum());
                for i in 0..len {
                    canvas.fill_rect_f(q.x - dx * i as f32, q.y - dy * i as f32, size, size, color);
                }
            } else {
                canvas.fill_rect_f(q.x - size / 2.0, q.y - size / 2.0, size, size, color);
            }
        }
    }
}

/// A fully saturated colour by hue (0 to 1), for confetti.
fn hsv(hue: f32) -> u32 {
    let h = hue * 6.0;
    let x = ((h % 2.0) - 1.0).abs();
    let x = ((1.0 - x) * 255.0) as u8;
    let (r, g, b) = match h as u32 {
        0 => (255, x, 0),
        1 => (x, 255, 0),
        2 => (0, 255, x),
        3 => (0, x, 255),
        4 => (x, 0, 255),
        _ => (255, 0, x),
    };
    argb(255, r, g, b)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn a_burst_plays_once_and_is_then_finished() {
        let mut e = Emitter::new(Preset::named("puff").unwrap(), 10.0, 10.0, 0.0, 1);
        e.tick();
        assert_eq!(e.particles.len(), 12);
        for _ in 0..60 {
            e.tick();
        }
        assert!(e.finished());
    }

    #[test]
    fn an_emitter_keeps_going_and_the_same_seed_gives_the_same_particles() {
        let mut a = Emitter::new(Preset::named("snow").unwrap(), 0.0, 0.0, 100.0, 7);
        let mut b = Emitter::new(Preset::named("snow").unwrap(), 0.0, 0.0, 100.0, 7);
        for _ in 0..200 {
            a.tick();
            b.tick();
        }
        assert!(!a.finished() && !a.particles.is_empty());
        assert_eq!(
            a.particles.iter().map(|p| (p.x, p.y)).collect::<Vec<_>>(),
            b.particles.iter().map(|p| (p.x, p.y)).collect::<Vec<_>>()
        );
    }

    #[test]
    fn overrides_apply_as_in_a_game() {
        let p = Preset::named("sparks").unwrap().with(
            Some("#ff0000"),
            Some(3),
            Some(2.0),
            Some(10.0),
            Some(2.0),
        );
        assert_eq!(p.color, 0xFFFF0000);
        assert_eq!(p.amount, 3);
        assert_eq!(p.lifetime, 2.0);
        assert_eq!(p.speed, (7.0, 13.0));
        assert_eq!(p.size, (1.4, 2.6));
        assert!(Preset::named("lava").is_none());
    }
}
