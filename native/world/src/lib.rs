//! quantum_world: the world's engine of Quantum's game server (PLAN_WORLD_ENGINE.md). E1: what each player sees,
//! worked out on every core (frames.rs), and the network (net.rs). E2: the rules as bytecode (vm.rs) and Python's
//! random (rng.rs). E3: the world's state and tick (world.rs), part by part.

pub mod frames;
pub mod net;
pub mod rng;
pub mod value;
pub mod vm;
pub mod world;

#[cfg(feature = "python")]
mod python;
