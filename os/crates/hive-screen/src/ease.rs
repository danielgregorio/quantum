//! The games' curves (`qg:tween`, `qs:tween`): the same transitions and
//! eases the Godot runtime applies, so a tween means the same on the
//! screen and in a game.

use crate::math::{cos, exp2, sin};
use std::f32::consts::PI;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Trans {
    Linear,
    Sine,
    Quad,
    Cubic,
    Back,
    Bounce,
    Elastic,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Ease {
    In,
    Out,
    InOut,
}

impl Trans {
    pub fn parse(name: &str) -> Option<Trans> {
        Some(match name {
            "linear" => Trans::Linear,
            "sine" => Trans::Sine,
            "quad" => Trans::Quad,
            "cubic" => Trans::Cubic,
            "back" => Trans::Back,
            "bounce" => Trans::Bounce,
            "elastic" => Trans::Elastic,
            _ => return None,
        })
    }
}

impl Ease {
    pub fn parse(name: &str) -> Option<Ease> {
        Some(match name {
            "in" => Ease::In,
            "out" => Ease::Out,
            "in-out" => Ease::InOut,
            _ => return None,
        })
    }
}

/// The value at `t` of `d`, starting at `b` and changing by `c`.
pub fn interpolate(b: f32, c: f32, t: f32, d: f32, trans: Trans, ease: Ease) -> f32 {
    match (trans, ease) {
        (Trans::Linear, _) => c * t / d + b,
        (Trans::Sine, Ease::In) => -c * cos(t / d * PI / 2.0) + c + b,
        (Trans::Sine, Ease::Out) => c * sin(t / d * PI / 2.0) + b,
        (Trans::Sine, Ease::InOut) => -c / 2.0 * (cos(PI * t / d) - 1.0) + b,
        (Trans::Quad, Ease::In) => {
            let t = t / d;
            c * t * t + b
        }
        (Trans::Quad, Ease::Out) => {
            let t = t / d;
            -c * t * (t - 2.0) + b
        }
        (Trans::Quad, Ease::InOut) => {
            let t = t / d * 2.0;
            if t < 1.0 {
                c / 2.0 * t * t + b
            } else {
                let t = t - 1.0;
                -c / 2.0 * (t * (t - 2.0) - 1.0) + b
            }
        }
        (Trans::Cubic, Ease::In) => {
            let t = t / d;
            c * t * t * t + b
        }
        (Trans::Cubic, Ease::Out) => {
            let t = t / d - 1.0;
            c * (t * t * t + 1.0) + b
        }
        (Trans::Cubic, Ease::InOut) => {
            let t = t / d * 2.0;
            if t < 1.0 {
                c / 2.0 * t * t * t + b
            } else {
                let t = t - 2.0;
                c / 2.0 * (t * t * t + 2.0) + b
            }
        }
        (Trans::Back, Ease::In) => {
            let s = 1.70158;
            let t = t / d;
            c * t * t * ((s + 1.0) * t - s) + b
        }
        (Trans::Back, Ease::Out) => {
            let s = 1.70158;
            let t = t / d - 1.0;
            c * (t * t * ((s + 1.0) * t + s) + 1.0) + b
        }
        (Trans::Back, Ease::InOut) => {
            let s = 1.70158 * 1.525;
            let t = t / d * 2.0;
            if t < 1.0 {
                c / 2.0 * (t * t * ((s + 1.0) * t - s)) + b
            } else {
                let t = t - 2.0;
                c / 2.0 * (t * t * ((s + 1.0) * t + s) + 2.0) + b
            }
        }
        (Trans::Bounce, Ease::Out) => bounce_out(t, b, c, d),
        (Trans::Bounce, Ease::In) => c - bounce_out(d - t, 0.0, c, d) + b,
        (Trans::Bounce, Ease::InOut) => {
            if t < d / 2.0 {
                (c - bounce_out(d - t * 2.0, 0.0, c, d)) * 0.5 + b
            } else {
                bounce_out(t * 2.0 - d, 0.0, c, d) * 0.5 + c * 0.5 + b
            }
        }
        (Trans::Elastic, Ease::In) => {
            if t == 0.0 {
                return b;
            }
            let t = t / d;
            if t == 1.0 {
                return b + c;
            }
            let p = d * 0.3;
            let s = p / 4.0;
            let t = t - 1.0;
            -(c * exp2(10.0 * t) * sin((t * d - s) * (2.0 * PI) / p)) + b
        }
        (Trans::Elastic, Ease::Out) => {
            if t == 0.0 {
                return b;
            }
            let t = t / d;
            if t == 1.0 {
                return b + c;
            }
            let p = d * 0.3;
            let s = p / 4.0;
            c * exp2(-10.0 * t) * sin((t * d - s) * (2.0 * PI) / p) + c + b
        }
        (Trans::Elastic, Ease::InOut) => {
            if t == 0.0 {
                return b;
            }
            let t = t / d * 2.0;
            if t == 2.0 {
                return b + c;
            }
            let p = d * 0.3 * 1.5;
            let s = p / 4.0;
            if t < 1.0 {
                let t = t - 1.0;
                -0.5 * (c * exp2(10.0 * t) * sin((t * d - s) * (2.0 * PI) / p)) + b
            } else {
                let t = t - 1.0;
                c * exp2(-10.0 * t) * sin((t * d - s) * (2.0 * PI) / p) * 0.5 + c + b
            }
        }
    }
}

fn bounce_out(t: f32, b: f32, c: f32, d: f32) -> f32 {
    let t = t / d;
    if t < 1.0 / 2.75 {
        c * (7.5625 * t * t) + b
    } else if t < 2.0 / 2.75 {
        let t = t - 1.5 / 2.75;
        c * (7.5625 * t * t + 0.75) + b
    } else if t < 2.5 / 2.75 {
        let t = t - 2.25 / 2.75;
        c * (7.5625 * t * t + 0.9375) + b
    } else {
        let t = t - 2.625 / 2.75;
        c * (7.5625 * t * t + 0.984375) + b
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_curve_starts_where_it_starts_and_ends_where_it_ends() {
        for trans in [
            Trans::Linear,
            Trans::Sine,
            Trans::Quad,
            Trans::Cubic,
            Trans::Back,
            Trans::Bounce,
            Trans::Elastic,
        ] {
            for ease in [Ease::In, Ease::Out, Ease::InOut] {
                let start = interpolate(10.0, 20.0, 0.0, 30.0, trans, ease);
                let end = interpolate(10.0, 20.0, 30.0, 30.0, trans, ease);
                assert!(
                    (start - 10.0).abs() < 1e-3,
                    "{:?} {:?} starts at {}",
                    trans,
                    ease,
                    start
                );
                assert!(
                    (end - 30.0).abs() < 1e-3,
                    "{:?} {:?} ends at {}",
                    trans,
                    ease,
                    end
                );
            }
        }
    }

    #[test]
    fn linear_is_linear_and_ease_out_is_ahead_of_ease_in() {
        assert_eq!(
            interpolate(0.0, 10.0, 5.0, 10.0, Trans::Linear, Ease::In),
            5.0
        );
        let quad_in = interpolate(0.0, 10.0, 5.0, 10.0, Trans::Quad, Ease::In);
        let quad_out = interpolate(0.0, 10.0, 5.0, 10.0, Trans::Quad, Ease::Out);
        assert!(quad_in < 5.0 && quad_out > 5.0);
        assert_eq!(Trans::parse("bounce"), Some(Trans::Bounce));
        assert_eq!(Ease::parse("in-out"), Some(Ease::InOut));
        assert_eq!(Trans::parse("expo"), None);
    }
}
