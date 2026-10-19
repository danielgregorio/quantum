//! hive-screen: the Hive's screen on the machine's console.
//!
//! It loads the scene Quantum compiled from a `q:application type="screen"`
//! (/etc/hive/screen/screen.toml), connects to hive-cortex's user socket as
//! a dashboard does, and plays the scene: an event of the Hive runs its
//! rule, an offer appears for an administrator to approve with the keys,
//! and the actuator's answer comes back as `done`.
//!
//!     hive-screen [--scene PATH] [--no-hive] [--play]
//!
//! `--play` drives it from stdin (see play.rs): the lab and the tests use
//! it, with no display. Drawing on the console (DRM) is the next slice;
//! without `--play` the daemon runs the scene at 60 ticks a second and
//! draws nothing yet.

mod canvas;
mod ease;
mod hive;
mod image;
mod math;
mod particles;
mod play;
mod runtime;
mod scene;
mod world;

use anyhow::{bail, Result};
use std::path::PathBuf;
use std::time::{Duration, Instant};

const DEFAULT_SCENE: &str = "/etc/hive/screen/screen.toml";

struct Args {
    scene: PathBuf,
    play: bool,
    hive: bool,
}

fn parse_args() -> Result<Args> {
    let mut args = Args {
        scene: PathBuf::from(DEFAULT_SCENE),
        play: false,
        hive: true,
    };
    let mut it = std::env::args().skip(1);
    while let Some(a) = it.next() {
        match a.as_str() {
            "--scene" => {
                args.scene = PathBuf::from(
                    it.next()
                        .ok_or_else(|| anyhow::anyhow!("--scene needs a path"))?,
                )
            }
            "--play" => args.play = true,
            "--no-hive" => args.hive = false,
            "--help" | "-h" => {
                println!("hive-screen [--scene PATH] [--no-hive] [--play]");
                std::process::exit(0);
            }
            other => bail!("unknown argument {} (hive-screen --help)", other),
        }
    }
    Ok(args)
}

fn main() -> Result<()> {
    let args = parse_args()?;
    if args.play {
        // the driver owns stdout; logs go to stderr
        tracing_to_stderr();
    } else {
        hive_common::logging::init("hive_screen")?;
    }
    let scene = scene::Scene::load(&args.scene)?;
    tracing::info!(
        "scene {} ({}x{}, {} sprites, {} rules)",
        args.scene.display(),
        scene.width,
        scene.height,
        scene.nodes.len(),
        scene.rules.len()
    );
    let world = world::World::new(scene);
    let hive = if args.hive {
        let socket = std::env::var("HIVE_USER_SOCKET")
            .unwrap_or_else(|_| hive_common::USER_SOCKET.to_string());
        Some(hive::Hive::connect(&socket)?)
    } else {
        None
    };
    let mut runtime = runtime::Runtime::new(world, hive);
    if args.play {
        return play::run(&mut runtime);
    }
    let started = Instant::now();
    let mut n: u64 = 0;
    loop {
        runtime.step()?;
        n += 1;
        let due = started + Duration::from_secs_f64(n as f64 / world::TICK_RATE as f64);
        if let Some(wait) = due.checked_duration_since(Instant::now()) {
            std::thread::sleep(wait);
        }
    }
}

fn tracing_to_stderr() {
    use tracing_subscriber::EnvFilter;
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            EnvFilter::from_default_env().add_directive("hive_screen=info".parse().unwrap()),
        )
        .with_writer(std::io::stderr)
        .try_init();
}
