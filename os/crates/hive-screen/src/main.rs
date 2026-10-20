//! hive-screen: the Hive's screen on the machine's console.
//!
//! It loads the scene Quantum compiled from a `q:application type="screen"`
//! (/etc/hive/screen/screen.toml), connects to hive-cortex's user socket as
//! a dashboard does, and plays the scene: an event of the Hive runs its
//! rule, an offer appears for an administrator to approve with the keys,
//! and the actuator's answer comes back as `done`.
//!
//!     hive-screen [--scene PATH] [--card /dev/dri/card0] [--no-display] [--no-hive] [--play]
//!                 [--pixel-socket PATH | --no-pixel]
//!
//! As a daemon it draws the scene on the console through DRM/KMS
//! (display.rs), reads the keyboard from /dev/input (input.rs) and keeps
//! the kernel's text console off its terminal (vt.rs). How much it shows
//! (particles, two pixels to the scene's one) is a presentation level
//! (level.rs), chosen by the frame time it measures under the ceiling the
//! machine's cores set; a frame is drawn in bands, one thread a core.
//! A page of a Quantum application comes in over the pixel socket
//! (pixel.rs, from `quantum pixel`) and is drawn over the scene
//! (window.rs), the keyboard its own while it shows. `--play` drives it
//! from stdin instead (play.rs): the lab and the tests use it, with no
//! display and at the level they ask for.

mod canvas;
mod display;
mod ease;
mod hive;
mod image;
mod input;
mod level;
mod math;
mod particles;
mod pixel;
mod play;
mod runtime;
mod scene;
mod vt;
mod window;
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
    /// The pixel socket: the daemon's by default, a test's where it says,
    /// none in play mode unless asked.
    pixel: Option<PathBuf>,
}

fn parse_args() -> Result<Args> {
    let mut args = Args {
        scene: PathBuf::from(DEFAULT_SCENE),
        card: PathBuf::from("/dev/dri/card0"),
        play: false,
        hive: true,
        display: true,
        pixel: Some(PathBuf::from(pixel::DEFAULT_PATH)),
    };
    let mut pixel_given = false;
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
            "--pixel-socket" => {
                args.pixel =
                    Some(PathBuf::from(it.next().ok_or_else(|| {
                        anyhow::anyhow!("--pixel-socket needs a path")
                    })?));
                pixel_given = true;
            }
            "--no-pixel" => {
                args.pixel = None;
                pixel_given = true;
            }
            "--help" | "-h" => {
                println!("hive-screen [--scene PATH] [--card /dev/dri/card0] [--no-display] [--no-hive] [--play] [--pixel-socket PATH | --no-pixel]");
                std::process::exit(0);
            }
            other => bail!("unknown argument {} (hive-screen --help)", other),
        }
    }
    if args.play && !pixel_given {
        args.pixel = None;
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
    // the pixel socket: without it the scene still shows, with no page
    let pixel = match &args.pixel {
        Some(path) => match pixel::PixelSocket::bind(path) {
            Ok(s) => Some(s),
            Err(e) if args.play => return Err(e),
            Err(e) => {
                tracing::warn!("no pixel socket, so no page on the screen: {:#}", e);
                None
            }
        },
        None => None,
    };
    let mut runtime = runtime::Runtime::new(world, hive, pixel);
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
        input::Keyboards::open(input::Layout::detect())?
    } else {
        input::Keyboards::none()
    };
    stop_on_signal();
    hive_common::systemd::report_ready();
    // HIVE_SCREEN_LEVEL pins the level (0 plain, 1 effects, 2 fine), for an
    // administrator who knows the machine better than the measure
    let pinned = std::env::var("HIVE_SCREEN_LEVEL")
        .ok()
        .and_then(|s| s.trim().parse::<usize>().ok());
    let mut chooser = match pinned {
        Some(l) => level::Chooser::pinned(l, cores(), Instant::now()),
        None => level::Chooser::new(cores(), Instant::now()),
    };
    runtime.world.set_level(chooser.level());
    runtime.world.set_facts(facts(chooser.cores()));
    // HIVE_SCREEN_MOTION=off: pages appear and go at once
    if std::env::var("HIVE_SCREEN_MOTION")
        .map(|v| {
            matches!(
                v.trim().to_ascii_lowercase().as_str(),
                "off" | "0" | "no" | "false"
            )
        })
        .unwrap_or(false)
    {
        runtime.world.set_motion(false);
        tracing::info!("motion off (HIVE_SCREEN_MOTION)");
    }
    if pinned.is_some() {
        tracing::info!("level {} pinned by HIVE_SCREEN_LEVEL", chooser.level());
    }
    let mut canvas = canvas::Canvas::new(size.0, size.1, level::LEVELS[chooser.level()].scale);
    tracing::info!(
        "level {} ({}): {}; {} cores",
        chooser.level(),
        level::LEVELS[chooser.level()].name,
        level::LEVELS[chooser.level()].describe(size),
        chooser.cores()
    );
    let started = Instant::now();
    let mut last_drawn = Instant::now() - Duration::from_secs(1);
    let mut n: u64 = 0;
    while !STOP.load(Ordering::Relaxed) {
        // another terminal asked for the console: let the display go and
        // say so; when it comes back, take the display and draw whole
        if console.release_asked() {
            if let Some(d) = display.as_mut() {
                d.suspend();
            }
            console.allow_release();
            tracing::info!("the console went to another terminal: the scene waits");
        }
        if console.acquire_asked() {
            console.acknowledge_acquire();
            match display.as_mut().map(|d| d.resume()) {
                Some(Err(e)) => {
                    tracing::warn!("the console is ours again, but the display is not: {:#}", e)
                }
                _ => tracing::info!("the console is ours again"),
            }
            runtime.world.touch();
        }
        let active = display.as_ref().map_or(true, |d| d.is_active());
        for key in keyboards.poll() {
            if active {
                runtime.press(key)?;
            }
        }
        runtime.step()?;
        n += 1;
        // the cores, twice a second: a vCPU plugged in counts at once
        if n % 30 == 0 {
            if chooser.set_cores(cores(), Instant::now()) {
                tracing::info!(
                    "cores: {}, level up to {}",
                    chooser.cores(),
                    level::ceiling(chooser.cores())
                );
            }
            // what the bars say: the machine's name, its cores, the time
            runtime.world.set_facts(facts(chooser.cores()));
        }
        if chooser.level() != runtime.world.level() {
            let lv = chooser.level();
            runtime.world.set_level(lv);
            canvas = canvas::Canvas::new(size.0, size.1, level::LEVELS[lv].scale);
            tracing::info!(
                "level {} ({}): {}; {} cores, {:.1} ms a frame before",
                lv,
                level::LEVELS[lv].name,
                level::LEVELS[lv].describe(size),
                chooser.cores(),
                chooser.before_ms()
            );
        }
        // at most as many pictures a second as the level says, none while
        // nothing moves, and none while another terminal has the console
        if active
            && last_drawn.elapsed() >= level::LEVELS[chooser.level()].period()
            && runtime.world.take_dirty()
        {
            let t0 = Instant::now();
            runtime.world.render(&mut canvas, chooser.threads());
            if let Some(d) = display.as_mut() {
                d.present(&canvas.image, chooser.threads())?;
            }
            last_drawn = Instant::now();
            chooser.frame(last_drawn - t0, last_drawn);
            if let Some(cost) = chooser.take_judged_ms() {
                tracing::info!(
                    "level {} ({}): {:.1} ms a frame over the first {} frames",
                    chooser.level(),
                    level::LEVELS[chooser.level()].name,
                    cost,
                    level::FRAMES_TO_JUDGE
                );
            }
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

/// The cores the daemon may run on now: what the kernel lets it (a vCPU
/// plugged in, once online, is one more; a cgroup quota, fewer).
fn cores() -> usize {
    std::thread::available_parallelism()
        .map(|n| n.get())
        .unwrap_or(1)
}

/// What the bars of the scene say of the machine: its name as the kernel
/// has it now (so a name set while the daemon runs shows), the cores the
/// chooser counts, the local time.
fn facts(cores: usize) -> world::Facts {
    let host = std::fs::read_to_string("/proc/sys/kernel/hostname")
        .map(|s| s.trim().to_string())
        .unwrap_or_default();
    world::Facts {
        host,
        cores,
        clock: Some(chrono::Local::now().format("%H:%M").to_string()),
    }
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
