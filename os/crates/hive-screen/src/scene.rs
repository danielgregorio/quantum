//! The compiled screen: screen.toml as quantum/runtime/screen writes it,
//! with the font and the sheets beside it, loaded and checked. Anything
//! not what the compiler writes is refused whole: the daemon does not
//! guess at a scene.

use crate::canvas::Font;
use crate::ease::{Ease, Trans};
use crate::image::{parse_color, Image};
use crate::particles::Preset;
use anyhow::{bail, Context as _, Result};
use serde::Deserialize;
use std::collections::BTreeMap;
use std::path::Path;

#[derive(Debug, Deserialize)]
struct File {
    meta: Meta,
    scene: SceneInfo,
    font: FontInfo,
    #[serde(default)]
    sheets: Vec<SheetInfo>,
    #[serde(default)]
    particles: Vec<ParticlesInfo>,
    #[serde(default)]
    nodes: Vec<NodeInfo>,
    #[serde(default)]
    rules: Vec<RuleInfo>,
}

#[derive(Debug, Deserialize)]
struct Meta {
    version: u32,
}

#[derive(Debug, Deserialize)]
struct SceneInfo {
    width: u32,
    height: u32,
    background: String,
}

#[derive(Debug, Deserialize)]
struct FontInfo {
    src: String,
    cell: [u32; 2],
}

#[derive(Debug, Deserialize)]
struct SheetInfo {
    name: String,
    src: String,
    tile: [u32; 2],
    frames: u32,
    #[serde(default)]
    animations: Vec<AnimationInfo>,
}

#[derive(Debug, Deserialize)]
struct AnimationInfo {
    name: String,
    frames: Vec<u32>,
    fps: f32,
    #[serde(rename = "loop")]
    looping: bool,
}

#[derive(Debug, Deserialize)]
struct ParticlesInfo {
    name: String,
    preset: String,
    color: Option<String>,
    amount: Option<u32>,
    lifetime: Option<f32>,
    speed: Option<f32>,
    size: Option<f32>,
}

#[derive(Debug, Deserialize)]
struct NodeInfo {
    kind: String,
    name: Option<String>,
    sheet: Option<String>,
    frame: Option<u32>,
    x: Option<i32>,
    y: Option<i32>,
    animation: Option<String>,
    hidden: Option<bool>,
    value: Option<String>,
    color: Option<String>,
    align: Option<String>,
    particles: Option<String>,
    width: Option<u32>,
    rows: Option<u32>,
    focus: Option<String>,
    level: Option<u32>,
}

#[derive(Debug, Deserialize)]
struct RuleInfo {
    event: String,
    #[serde(default)]
    actions: Vec<ActionInfo>,
}

#[derive(Debug, Deserialize)]
struct ActionInfo {
    kind: String,
    target: Option<String>,
    name: Option<String>,
    frame: Option<u32>,
    visible: Option<bool>,
    property: Option<String>,
    to: Option<f32>,
    from: Option<f32>,
    seconds: Option<f32>,
    trans: Option<String>,
    ease: Option<String>,
    repeat: Option<i32>,
    yoyo: Option<bool>,
    particles: Option<String>,
    at: Option<String>,
    dx: Option<i32>,
    dy: Option<i32>,
    text: Option<String>,
}

// ---------------------------------------------------------------- what the world runs

#[derive(Debug, Clone)]
pub struct Animation {
    pub frames: Vec<u32>,
    pub fps: f32,
    pub looping: bool,
}

#[derive(Debug)]
pub struct Sheet {
    pub name: String,
    pub image: Image,
    pub tile: (u32, u32),
    pub columns: u32,
    pub frames: u32,
    pub animations: BTreeMap<String, Animation>,
}

impl Sheet {
    /// Where a frame is in the sheet.
    pub fn cell(&self, frame: u32) -> (u32, u32) {
        let frame = frame.min(self.frames.saturating_sub(1));
        (
            (frame % self.columns) * self.tile.0,
            (frame / self.columns) * self.tile.1,
        )
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Property {
    X,
    Y,
    Scale,
    Alpha,
}

impl Property {
    fn parse(name: &str) -> Option<Property> {
        Some(match name {
            "x" => Property::X,
            "y" => Property::Y,
            "scale" => Property::Scale,
            "alpha" => Property::Alpha,
            _ => return None,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Align {
    Left,
    Center,
    Right,
}

#[derive(Debug, Clone)]
pub enum Node {
    Sprite {
        name: Option<String>,
        sheet: usize,
        frame: u32,
        x: i32,
        y: i32,
        animation: Option<String>,
        hidden: bool,
    },
    Text {
        value: String,
        x: i32,
        y: i32,
        color: u32,
        align: Align,
    },
    Emitter {
        particles: String,
        x: i32,
        y: i32,
        width: u32,
        /// The presentation level it plays from: 1 with the effects, 2 at
        /// the fine level only (level.rs).
        level: u32,
    },
    Offers {
        x: i32,
        y: i32,
        width: u32,
        rows: u32,
        color: u32,
        focus: u32,
    },
    Notices {
        x: i32,
        y: i32,
        width: u32,
        rows: u32,
        color: u32,
    },
}

#[derive(Debug, Clone)]
pub enum Action {
    Animate {
        target: String,
        name: String,
    },
    Frame {
        target: String,
        frame: u32,
    },
    Show {
        target: String,
        visible: bool,
    },
    Tween {
        target: String,
        property: Property,
        to: f32,
        from: Option<f32>,
        seconds: f32,
        trans: Trans,
        ease: Ease,
        repeat: i32,
        yoyo: bool,
    },
    Emit {
        particles: String,
        at: String,
        dx: i32,
        dy: i32,
    },
    Say {
        text: String,
        seconds: f32,
    },
}

#[derive(Debug, Clone)]
pub struct Rule {
    pub event: String,
    pub actions: Vec<Action>,
}

pub struct Scene {
    pub width: u32,
    pub height: u32,
    pub background: u32,
    pub font: Font,
    pub sheets: Vec<Sheet>,
    pub particles: BTreeMap<String, Preset>,
    pub nodes: Vec<Node>,
    pub rules: Vec<Rule>,
}

fn need<T: Clone>(v: &Option<T>, what: &str, kind: &str) -> Result<T> {
    v.clone().with_context(|| {
        format!(
            "a {} node needs {}: not what the compiler writes",
            kind, what
        )
    })
}

fn color(text: &str, what: &str) -> Result<u32> {
    parse_color(text).with_context(|| format!("{} is not a colour: {}", what, text))
}

impl Scene {
    /// Loads screen.toml and what it names, relative to its own folder.
    pub fn load(path: &Path) -> Result<Scene> {
        let text = std::fs::read_to_string(path)
            .with_context(|| format!("cannot read {}", path.display()))?;
        let file: File = toml::from_str(&text)
            .with_context(|| format!("{} is not a screen file", path.display()))?;
        if file.meta.version != 1 {
            bail!(
                "{} is version {}; this hive-screen reads version 1",
                path.display(),
                file.meta.version
            );
        }
        let dir = path.parent().unwrap_or(Path::new("."));
        let font_image = Image::load(&dir.join(&file.font.src))?;
        let font = Font::new(font_image, (file.font.cell[0], file.font.cell[1]));

        let mut sheets = Vec::new();
        for s in &file.sheets {
            let image = Image::load(&dir.join(&s.src))?;
            let (tw, th) = (s.tile[0].max(1), s.tile[1].max(1));
            let columns = image.width / tw;
            let frames = columns * (image.height / th);
            if frames != s.frames || columns == 0 {
                bail!(
                    "sheet {} is {}x{}, not the {} frames of {}x{} the scene says",
                    s.name,
                    image.width,
                    image.height,
                    s.frames,
                    tw,
                    th
                );
            }
            let mut animations = BTreeMap::new();
            for a in &s.animations {
                if a.frames.is_empty() || a.frames.iter().any(|&f| f >= frames) || a.fps <= 0.0 {
                    bail!(
                        "animation {} of sheet {} is not what the compiler writes",
                        a.name,
                        s.name
                    );
                }
                animations.insert(
                    a.name.clone(),
                    Animation {
                        frames: a.frames.clone(),
                        fps: a.fps,
                        looping: a.looping,
                    },
                );
            }
            sheets.push(Sheet {
                name: s.name.clone(),
                image,
                tile: (tw, th),
                columns,
                frames,
                animations,
            });
        }
        let sheet_index = |name: &str| -> Result<usize> {
            sheets
                .iter()
                .position(|s| s.name == name)
                .with_context(|| format!("no sheet named {}", name))
        };

        let mut particles = BTreeMap::new();
        for p in &file.particles {
            let preset = Preset::named(&p.preset)
                .with_context(|| format!("particles {}: no preset {}", p.name, p.preset))?
                .with(p.color.as_deref(), p.amount, p.lifetime, p.speed, p.size);
            particles.insert(p.name.clone(), preset);
        }

        let mut nodes = Vec::new();
        let mut names: Vec<String> = Vec::new();
        for n in &file.nodes {
            let node = match n.kind.as_str() {
                "sprite" => {
                    let sheet = sheet_index(&need(&n.sheet, "sheet", "sprite")?)?;
                    let frame = n.frame.unwrap_or(0);
                    if frame >= sheets[sheet].frames {
                        bail!(
                            "sprite frame {} is not in sheet {}",
                            frame,
                            sheets[sheet].name
                        );
                    }
                    if let Some(a) = &n.animation {
                        if !sheets[sheet].animations.contains_key(a) {
                            bail!("sheet {} has no animation {}", sheets[sheet].name, a);
                        }
                    }
                    if let Some(name) = &n.name {
                        if names.contains(name) {
                            bail!("two sprites named {}", name);
                        }
                        names.push(name.clone());
                    }
                    Node::Sprite {
                        name: n.name.clone(),
                        sheet,
                        frame,
                        x: need(&n.x, "x", "sprite")?,
                        y: need(&n.y, "y", "sprite")?,
                        animation: n.animation.clone(),
                        hidden: n.hidden.unwrap_or(false),
                    }
                }
                "text" => Node::Text {
                    value: need(&n.value, "value", "text")?,
                    x: need(&n.x, "x", "text")?,
                    y: need(&n.y, "y", "text")?,
                    color: color(n.color.as_deref().unwrap_or("#ffffff"), "text color")?,
                    align: match n.align.as_deref().unwrap_or("left") {
                        "center" => Align::Center,
                        "right" => Align::Right,
                        _ => Align::Left,
                    },
                },
                "emitter" => {
                    let name = need(&n.particles, "particles", "emitter")?;
                    if !particles.contains_key(&name) {
                        bail!("no particles named {}", name);
                    }
                    Node::Emitter {
                        particles: name,
                        x: need(&n.x, "x", "emitter")?,
                        y: need(&n.y, "y", "emitter")?,
                        width: n.width.unwrap_or(0),
                        level: match n.level.unwrap_or(1) {
                            l @ (1 | 2) => l,
                            other => bail!("emitter level {} is not 1 or 2", other),
                        },
                    }
                }
                "offers" => Node::Offers {
                    x: need(&n.x, "x", "offers")?,
                    y: need(&n.y, "y", "offers")?,
                    width: need(&n.width, "width", "offers")?,
                    rows: n.rows.unwrap_or(4).max(1),
                    color: color(n.color.as_deref().unwrap_or("#ffffff"), "offers color")?,
                    focus: color(n.focus.as_deref().unwrap_or("#ffd34d"), "offers focus")?,
                },
                "notices" => Node::Notices {
                    x: need(&n.x, "x", "notices")?,
                    y: need(&n.y, "y", "notices")?,
                    width: need(&n.width, "width", "notices")?,
                    rows: n.rows.unwrap_or(3).max(1),
                    color: color(n.color.as_deref().unwrap_or("#c0c0c0"), "notices color")?,
                },
                other => bail!("a node of kind {}: not what the compiler writes", other),
            };
            nodes.push(node);
        }

        let mut rules = Vec::new();
        for r in &file.rules {
            if rules.iter().any(|x: &Rule| x.event == r.event) {
                bail!("two rules on {}", r.event);
            }
            let mut actions = Vec::new();
            for a in &r.actions {
                let kind = a.kind.as_str();
                let action = match kind {
                    "animate" => Action::Animate {
                        target: need(&a.target, "target", kind)?,
                        name: need(&a.name, "name", kind)?,
                    },
                    "frame" => Action::Frame {
                        target: need(&a.target, "target", kind)?,
                        frame: need(&a.frame, "frame", kind)?,
                    },
                    "show" => Action::Show {
                        target: need(&a.target, "target", kind)?,
                        visible: a.visible.unwrap_or(true),
                    },
                    "tween" => Action::Tween {
                        target: need(&a.target, "target", kind)?,
                        property: Property::parse(&need(&a.property, "property", kind)?)
                            .context("a tween of a property that is not one")?,
                        to: need(&a.to, "to", kind)?,
                        from: a.from,
                        seconds: a.seconds.unwrap_or(0.5),
                        trans: Trans::parse(a.trans.as_deref().unwrap_or("sine"))
                            .context("a tween of a curve that is not one")?,
                        ease: Ease::parse(a.ease.as_deref().unwrap_or("out"))
                            .context("a tween of an ease that is not one")?,
                        repeat: a.repeat.unwrap_or(0),
                        yoyo: a.yoyo.unwrap_or(false),
                    },
                    "emit" => {
                        let name = need(&a.particles, "particles", kind)?;
                        if !particles.contains_key(&name) {
                            bail!("no particles named {}", name);
                        }
                        Action::Emit {
                            particles: name,
                            at: need(&a.at, "at", kind)?,
                            dx: a.dx.unwrap_or(0),
                            dy: a.dy.unwrap_or(0),
                        }
                    }
                    "say" => Action::Say {
                        text: need(&a.text, "text", kind)?,
                        seconds: a.seconds.unwrap_or(4.0),
                    },
                    other => bail!("an action of kind {}: not what the compiler writes", other),
                };
                actions.push(action);
            }
            rules.push(Rule {
                event: r.event.clone(),
                actions,
            });
        }

        Ok(Scene {
            width: file.scene.width.max(1),
            height: file.scene.height.max(1),
            background: color(&file.scene.background, "the background")?,
            font,
            sheets,
            particles,
            nodes,
            rules,
        })
    }

    pub fn rule(&self, event: &str) -> Option<&Rule> {
        self.rules.iter().find(|r| r.event == event)
    }
}
