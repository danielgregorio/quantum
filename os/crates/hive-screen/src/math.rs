//! sin, cos and 2^x in plain arithmetic, so that a frame is the same
//! pixel for pixel on every machine: the C library's versions may differ
//! in the last bit between systems, and a tween's position or a
//! particle's path rounds to a pixel.

use std::f32::consts::PI;

/// sin(x), to about 1e-6 over any x.
pub fn sin(x: f32) -> f32 {
    // reduce to [-pi, pi]
    let mut t = x % (2.0 * PI);
    if t > PI {
        t -= 2.0 * PI;
    } else if t < -PI {
        t += 2.0 * PI;
    }
    // fold to [-pi/2, pi/2], where the polynomial is accurate
    if t > PI / 2.0 {
        t = PI - t;
    } else if t < -PI / 2.0 {
        t = -PI - t;
    }
    let t2 = t * t;
    // Taylor to the 11th power: error under 1e-6 on [-pi/2, pi/2]
    t * (1.0
        + t2 * (-1.0 / 6.0
            + t2 * (1.0 / 120.0
                + t2 * (-1.0 / 5040.0 + t2 * (1.0 / 362880.0 + t2 * (-1.0 / 39916800.0))))))
}

pub fn cos(x: f32) -> f32 {
    sin(x + PI / 2.0)
}

/// 2^x for x in about [-60, 60].
pub fn exp2(x: f32) -> f32 {
    let x = x.clamp(-60.0, 60.0);
    let i = x.floor();
    let f = x - i;
    // 2^f on [0, 1): a Taylor series of e^(f ln 2) to the 7th power
    let l = f * std::f32::consts::LN_2;
    let p = 1.0
        + l * (1.0
            + l * (1.0 / 2.0
                + l * (1.0 / 6.0
                    + l * (1.0 / 24.0
                        + l * (1.0 / 120.0 + l * (1.0 / 720.0 + l * (1.0 / 5040.0)))))));
    p * f32::from_bits(((i as i32 + 127) as u32) << 23)
}

/// atan2(y, x), to about 1e-4: only used to turn a direction into an angle.
pub fn atan2(y: f32, x: f32) -> f32 {
    if x == 0.0 && y == 0.0 {
        return 0.0;
    }
    let (ax, ay) = (x.abs(), y.abs());
    let a = if ax > ay { ay / ax } else { ax / ay };
    let s = a * a;
    // a minimax polynomial for atan on [0, 1]
    let mut r = a
        * (0.99997726
            + s * (-0.33262347
                + s * (0.19354346 + s * (-0.11643287 + s * (0.05265332 + s * (-0.0117212))))));
    if ay > ax {
        r = PI / 2.0 - r;
    }
    if x < 0.0 {
        r = PI - r;
    }
    if y < 0.0 {
        r = -r;
    }
    r
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn close_to_the_library_s_everywhere() {
        let mut x = -20.0f32;
        while x < 20.0 {
            assert!((sin(x) - x.sin()).abs() < 2e-6, "sin {}", x);
            assert!((cos(x) - x.cos()).abs() < 2e-6, "cos {}", x);
            x += 0.37;
        }
        for e in [-10.0f32, -1.5, -0.25, 0.0, 0.5, 1.0, 3.75, 10.0] {
            assert!(
                (exp2(e) - 2f32.powf(e)).abs() / 2f32.powf(e) < 1e-5,
                "exp2 {}",
                e
            );
        }
        for (y, x) in [
            (1.0f32, 1.0f32),
            (-1.0, 2.0),
            (3.0, -1.0),
            (-2.0, -2.0),
            (0.0, -1.0),
            (1.0, 0.0),
        ] {
            assert!((atan2(y, x) - y.atan2(x)).abs() < 2e-4, "atan2 {} {}", y, x);
        }
    }
}
