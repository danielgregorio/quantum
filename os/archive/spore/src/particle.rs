//! Simple particle system for visual effects
//!
//! Provides a lightweight particle system for effects like sparks,
//! smoke, explosions, and other visual flourishes.

use crate::canvas::Canvas;
use crate::color::Color;

/// A single particle
#[derive(Debug, Clone, Copy)]
pub struct Particle {
    /// Position X
    pub x: f32,
    /// Position Y
    pub y: f32,
    /// Velocity X
    pub vx: f32,
    /// Velocity Y
    pub vy: f32,
    /// Remaining lifetime in seconds
    pub lifetime: f32,
    /// Initial lifetime (for calculating alpha fade)
    pub initial_lifetime: f32,
    /// Particle size
    pub size: f32,
    /// Particle color
    pub color: Color,
    /// Is this particle still alive?
    pub alive: bool,
}

impl Particle {
    /// Create a new particle
    pub fn new(x: f32, y: f32, vx: f32, vy: f32, lifetime: f32, size: f32, color: Color) -> Self {
        Self {
            x,
            y,
            vx,
            vy,
            lifetime,
            initial_lifetime: lifetime,
            size,
            color,
            alive: true,
        }
    }

    /// Update the particle
    pub fn update(&mut self, dt: f32, gravity: f32) {
        if !self.alive {
            return;
        }

        self.x += self.vx * dt;
        self.y += self.vy * dt;
        self.vy += gravity * dt;
        self.lifetime -= dt;

        if self.lifetime <= 0.0 {
            self.alive = false;
        }
    }

    /// Get the current alpha based on lifetime
    pub fn current_alpha(&self) -> f32 {
        if self.initial_lifetime > 0.0 {
            (self.lifetime / self.initial_lifetime).clamp(0.0, 1.0)
        } else {
            1.0
        }
    }

    /// Draw the particle
    pub fn draw(&self, canvas: &mut Canvas) {
        if !self.alive {
            return;
        }

        let alpha = (self.current_alpha() * 255.0) as u8;
        let color = self.color.with_alpha(alpha);
        let half_size = (self.size / 2.0) as i32;

        // Draw as a filled circle for size > 2, otherwise as a pixel
        if self.size > 2.0 {
            canvas.fill_circle(self.x as i32, self.y as i32, half_size as u32, color);
        } else {
            canvas.set_pixel(self.x as i32, self.y as i32, color);
        }
    }
}

/// Particle emitter configuration
#[derive(Debug, Clone)]
pub struct EmitterConfig {
    /// Particles per second
    pub emit_rate: f32,
    /// Particle lifetime range (min, max)
    pub lifetime: (f32, f32),
    /// Particle size range (min, max)
    pub size: (f32, f32),
    /// Initial velocity X range (min, max)
    pub velocity_x: (f32, f32),
    /// Initial velocity Y range (min, max)
    pub velocity_y: (f32, f32),
    /// Gravity effect
    pub gravity: f32,
    /// Start color
    pub color_start: Color,
    /// End color (lerped over lifetime)
    pub color_end: Color,
    /// Spread angle in radians (0 = straight, PI = full circle)
    pub spread: f32,
    /// Base angle in radians
    pub angle: f32,
}

impl Default for EmitterConfig {
    fn default() -> Self {
        Self {
            emit_rate: 100.0,
            lifetime: (0.5, 1.5),
            size: (2.0, 4.0),
            velocity_x: (-50.0, 50.0),
            velocity_y: (-100.0, -50.0),
            gravity: 200.0,
            color_start: Color::WHITE,
            color_end: Color::TRANSPARENT,
            spread: std::f32::consts::PI,
            angle: -std::f32::consts::FRAC_PI_2, // Point up
        }
    }
}

impl EmitterConfig {
    /// Create a fire-like emitter
    pub fn fire() -> Self {
        Self {
            emit_rate: 50.0,
            lifetime: (0.3, 0.8),
            size: (3.0, 6.0),
            velocity_x: (-20.0, 20.0),
            velocity_y: (-80.0, -40.0),
            gravity: -50.0, // Negative gravity makes particles rise
            color_start: Color::rgba(255, 200, 50, 255),
            color_end: Color::rgba(255, 50, 0, 0),
            spread: 0.3,
            angle: -std::f32::consts::FRAC_PI_2,
        }
    }

    /// Create a smoke-like emitter
    pub fn smoke() -> Self {
        Self {
            emit_rate: 20.0,
            lifetime: (1.0, 2.0),
            size: (4.0, 8.0),
            velocity_x: (-10.0, 10.0),
            velocity_y: (-30.0, -10.0),
            gravity: -10.0,
            color_start: Color::rgba(100, 100, 100, 200),
            color_end: Color::rgba(50, 50, 50, 0),
            spread: 0.5,
            angle: -std::f32::consts::FRAC_PI_2,
        }
    }

    /// Create a spark-like emitter
    pub fn sparks() -> Self {
        Self {
            emit_rate: 200.0,
            lifetime: (0.2, 0.5),
            size: (1.0, 2.0),
            velocity_x: (-100.0, 100.0),
            velocity_y: (-100.0, 100.0),
            gravity: 300.0,
            color_start: Color::rgba(255, 255, 200, 255),
            color_end: Color::rgba(255, 100, 0, 0),
            spread: std::f32::consts::PI * 2.0,
            angle: 0.0,
        }
    }

    /// Create a snow-like emitter
    pub fn snow() -> Self {
        Self {
            emit_rate: 30.0,
            lifetime: (3.0, 5.0),
            size: (2.0, 4.0),
            velocity_x: (-20.0, 20.0),
            velocity_y: (30.0, 60.0),
            gravity: 10.0,
            color_start: Color::WHITE,
            color_end: Color::rgba(255, 255, 255, 100),
            spread: 0.2,
            angle: std::f32::consts::FRAC_PI_2, // Point down
        }
    }
}

/// A particle system managing multiple particles
pub struct ParticleSystem {
    particles: Vec<Particle>,
    config: EmitterConfig,
    emit_x: f32,
    emit_y: f32,
    emit_accumulator: f32,
    active: bool,
    rng_state: u32,
}

impl ParticleSystem {
    /// Create a new particle system
    pub fn new(config: EmitterConfig, max_particles: usize) -> Self {
        Self {
            particles: Vec::with_capacity(max_particles),
            config,
            emit_x: 0.0,
            emit_y: 0.0,
            emit_accumulator: 0.0,
            active: true,
            rng_state: 12345,
        }
    }

    /// Simple pseudo-random number generator
    fn rand(&mut self) -> f32 {
        self.rng_state = self.rng_state.wrapping_mul(1103515245).wrapping_add(12345);
        ((self.rng_state >> 16) & 0x7FFF) as f32 / 32768.0
    }

    /// Random value in range
    fn rand_range(&mut self, min: f32, max: f32) -> f32 {
        min + self.rand() * (max - min)
    }

    /// Set emitter position
    pub fn set_position(&mut self, x: f32, y: f32) {
        self.emit_x = x;
        self.emit_y = y;
    }

    /// Start/resume emitting
    pub fn start(&mut self) {
        self.active = true;
    }

    /// Stop emitting (existing particles continue)
    pub fn stop(&mut self) {
        self.active = false;
    }

    /// Clear all particles
    pub fn clear(&mut self) {
        self.particles.clear();
    }

    /// Emit a burst of particles
    pub fn burst(&mut self, count: u32) {
        for _ in 0..count {
            self.emit_particle();
        }
    }

    /// Emit a single particle
    fn emit_particle(&mut self) {
        // Create the particle first to avoid borrow issues
        let new_particle = self.create_particle();

        if self.particles.len() >= self.particles.capacity() {
            // Find a dead particle to reuse
            if let Some(p) = self.particles.iter_mut().find(|p| !p.alive) {
                *p = new_particle;
                return;
            }
            return; // At capacity
        }

        self.particles.push(new_particle);
    }

    /// Create a new particle with randomized properties
    fn create_particle(&mut self) -> Particle {
        let angle = self.config.angle
            + self.rand_range(-self.config.spread / 2.0, self.config.spread / 2.0);
        let speed = self.rand_range(
            (self.config.velocity_x.0.powi(2) + self.config.velocity_y.0.powi(2)).sqrt(),
            (self.config.velocity_x.1.powi(2) + self.config.velocity_y.1.powi(2)).sqrt(),
        );

        let vx = angle.cos() * speed
            + self.rand_range(self.config.velocity_x.0, self.config.velocity_x.1) * 0.3;
        let vy = angle.sin() * speed
            + self.rand_range(self.config.velocity_y.0, self.config.velocity_y.1) * 0.3;

        Particle::new(
            self.emit_x,
            self.emit_y,
            vx,
            vy,
            self.rand_range(self.config.lifetime.0, self.config.lifetime.1),
            self.rand_range(self.config.size.0, self.config.size.1),
            self.config.color_start,
        )
    }

    /// Update all particles
    pub fn update(&mut self, dt: f32) {
        // Emit new particles
        if self.active {
            self.emit_accumulator += self.config.emit_rate * dt;
            while self.emit_accumulator >= 1.0 {
                self.emit_particle();
                self.emit_accumulator -= 1.0;
            }
        }

        // Update existing particles
        for particle in &mut self.particles {
            if particle.alive {
                particle.update(dt, self.config.gravity);

                // Lerp color based on lifetime
                let t = 1.0 - particle.current_alpha();
                particle.color = self.config.color_start.lerp(self.config.color_end, t);
            }
        }
    }

    /// Draw all particles
    pub fn draw(&self, canvas: &mut Canvas) {
        for particle in &self.particles {
            particle.draw(canvas);
        }
    }

    /// Get the number of active particles
    pub fn active_count(&self) -> usize {
        self.particles.iter().filter(|p| p.alive).count()
    }

    /// Check if any particles are still alive
    pub fn has_particles(&self) -> bool {
        self.particles.iter().any(|p| p.alive)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_particle_lifecycle() {
        let mut particle = Particle::new(0.0, 0.0, 10.0, -10.0, 1.0, 2.0, Color::WHITE);
        assert!(particle.alive);

        particle.update(0.5, 0.0);
        assert!(particle.alive);
        assert!(particle.x > 0.0);

        particle.update(0.6, 0.0);
        assert!(!particle.alive);
    }

    #[test]
    fn test_particle_system() {
        let config = EmitterConfig::default();
        let mut system = ParticleSystem::new(config, 100);
        system.set_position(100.0, 100.0);

        system.update(0.1);
        assert!(system.active_count() > 0);

        // Let particles die
        for _ in 0..50 {
            system.stop();
            system.update(0.1);
        }
    }

    #[test]
    fn test_burst() {
        let config = EmitterConfig::default();
        let mut system = ParticleSystem::new(config, 100);
        system.stop();

        system.burst(50);
        assert_eq!(system.active_count(), 50);
    }
}
