//! hive-screen: the Hive's screen on the machine's console.
//!
//! It loads the scene Quantum compiled from a `q:application type="screen"`
//! (/etc/hive/screen/screen.toml), connects to hive-cortex's user socket as
//! a dashboard does, and plays the scene: an event of the Hive runs its
//! rule, an offer appears for an administrator to approve with the keys,
//! and the actuator's answer comes back as `done`.
//!
//!     hive-screen [--scene PATH] [--card /dev/dri/card0] [--no-display] [--no-hive] [--play]
//!
//! As a daemon it draws the scene on the console through DRM/KMS
//! (display.rs), reads the keyboard from /dev/input (input.rs) and keeps
//! the kernel's text console off its terminal (vt.rs). `--play` drives it
//! from stdin instead (play.rs): the lab and the tests use it, with no
//! display.

mod canvas;
mod display;
mod ease;
mod hive;
mod image;
mod input;
mod math;
mod particles;
mod play;
mod runtime;
mod scene;
mod vt;
mod world;

use anyhow::{bail, Result};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::{Duration, Instant};

const DEFAULT_SCENE: &str = "/etc/hive/screen/screen.toml";

struct Args {
    scene: PathBuf,
    card: PathBuf,
    play: bool,
    hive: bool,
    display: bool,
}

fn parse_args() -> Result<Args> {
    let mut args = Args {
        scene: PathBuf::from(DEFAULT_SCENE),
        card: PathBuf::from("/dev/dri/card0"),
        play: false,
        hive: true,
        display: true,
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
            "--card" => {
                args.card = PathBuf::from(
                    it.next()
                        .ok_or_else(|| anyhow::anyhow!("--card needs a path"))?,
                )
            }
            "--play" => {
                args.play = true;
                args.display = false;
            }
            "--no-hive" => args.hive = false,
            "--no-display" => args.display = false,
            "--help" | "-h" => {
                println!("hive-screen [--scene PATH] [--card /dev/dri/card0] [--no-display] [--no-hive] [--play]");
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
    let size = (runtime.world.scene.width, runtime.world.scene.height);
    let mut console = if args.display {
        vt::Console::take()
    } else {
        vt::Console::none()
    };
    let mut display = if args.display {
        Some(display::Display::open(&args.card, size)?)
    } else {
        None
    };
    let mut keyboards = if args.display {
        input::Keyboards::open()?
    } else {
        input::Keyboards::none()
    };
    stop_on_signal();
    hive_common::systemd::report_ready();
    let mut canvas = canvas::Canvas::new(size.0, size.1);
    let started = Instant::now();
    let mut last_drawn = Instant::now() - Duration::from_secs(1);
    let mut n: u64 = 0;
    while !STOP.load(Ordering::Relaxed) {
        for key in keyboards.poll() {
            runtime.press(key)?;
        }
        runtime.step()?;
        n += 1;
        // at most 30 pictures a second, and none while nothing moves
        if runtime.world.take_dirty() && last_drawn.elapsed() >= Duration::from_millis(33) {
            runtime.world.draw(&mut canvas);
            if let Some(d) = display.as_mut() {
                d.present(&canvas.image)?;
            }
            last_drawn = Instant::now();
        }
        let due = started + Duration::from_secs_f64(n as f64 / world::TICK_RATE as f64);
        if let Some(wait) = due.checked_duration_since(Instant::now()) {
            std::thread::sleep(wait);
        }
    }
    tracing::info!("stopping");
    display.take();
    console.release();
    Ok(())
}

static STOP: AtomicBool = AtomicBool::new(false);

extern "C" fn on_signal(_: libc::c_int) {
    STOP.store(true, Ordering::Relaxed);
}

/// SIGTERM and SIGINT end the loop, so the console goes back to text mode
/// and the display is released on the way out.
fn stop_on_signal() {
    // SAFETY: installing a signal handler that only stores a flag.
    unsafe {
        libc::signal(libc::SIGTERM, on_signal as *const () as libc::sighandler_t);
        libc::signal(libc::SIGINT, on_signal as *const () as libc::sighandler_t);
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
