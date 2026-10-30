//! quantum_world: the world's engine of Quantum's game server (PLAN_WORLD_ENGINE.md). E1: what each player sees,
//! worked out on every core, and (net.rs) the network. The tick is still Python's `World.step`.

pub mod frames;
pub mod net;
pub mod value;

#[cfg(feature = "python")]
mod python;
