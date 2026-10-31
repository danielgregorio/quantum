//! A world's state, a tick at a time, in the engine (PLAN_WORLD_ENGINE.md, E3): quantum/runtime/gameserver/world.py's
//! World, to the byte of its digest. The definition is Python's (model.py reads the .q; native_world.py hands it
//! here with its blocks compiled to bytecode); the state, the tick, the journal that undoes a refused command, the
//! index of cells and the world's own functions are the engine's, and the machine (vm.rs) runs the blocks with the
//! world as its host.
//!
//! E3a holds the world's core: its entities, variables and players, a player's join and leave, the commands (their
//! arguments, their rate, whole or not at all), the rules due (q:every, q:on-join, q:on-leave), q:move, q:emit and
//! q:say, the functions that read the world, the snapshot and the digest. E3b its life (life.py's): spawns, brains,
//! q:kill and q:on-death, q:loot, q:travel, the clock. E3c its players together: the ledger and its books
//! (world/ledger.rs), the chat, parties and trades (world/together.rs), and a q:ask handed off the tick to the minds
//! (world/minds.rs). What a world uses beyond it native_world.py finds first, and that world stays Python's.

use rustc_hash::{FxHashMap as HashMap, FxHashSet as HashSet};
use std::sync::atomic::AtomicUsize;
use std::sync::Arc;

/// An ordered map with a fast hash (the order is Python's dict's).
type IndexMap<K, V> = indexmap::IndexMap<K, V, rustc_hash::FxBuildHasher>;
use sha2::{Digest, Sha256};

use crate::rng::Rng;
use crate::value::{py_eq, write_float, write_str, Map, Value};
use crate::vm::{self, Code, ErrorKind, Function, Functions, Host, Locals, VmError};

mod ledger;
mod minds;
mod together;

pub const MAX_ARGS: usize = 2048;
pub const MAX_ERRORS: usize = 100;
pub const MAX_EVENTS: usize = 10_000;
pub const MAX_LINE: usize = 200;
/// The side of a cell of the index, in tiles.
pub const CELL: i64 = 16;
/// Tiles from a hero within which a brain runs, and how far nearest() looks by default (life.py's AWAKE).
pub const AWAKE: i64 = 32;
/// How far a chase, and a q:travel, look for their way (life.py's).
pub const CHASE_SEARCH: i64 = 12;
pub const TRAVEL_SEARCH: i64 = 40;
/// A wanderer at rest steps with this chance a tick.
pub const WANDER_CHANCE: f64 = 0.3;
/// The eight ways, in the order a way is looked for (straight ones first).
const STEPS: [Tile; 8] = [
    (0, -1),
    (1, 0),
    (0, 1),
    (-1, 0),
    (1, -1),
    (1, 1),
    (-1, 1),
    (-1, -1),
];

pub type Tile = (i64, i64);

const DIRECTIONS: [(&str, Tile); 8] = [
    ("north", (0, -1)),
    ("south", (0, 1)),
    ("east", (1, 0)),
    ("west", (-1, 0)),
    ("northeast", (1, -1)),
    ("northwest", (-1, -1)),
    ("southeast", (1, 1)),
    ("southwest", (-1, 1)),
];

fn chebyshev(a: Tile, b: Tile) -> i64 {
    (a.0 - b.0).abs().max((a.1 - b.1).abs())
}

/// A number of a tile's, as int() takes it (a bool is one).
fn number(v: &Value) -> Option<i64> {
    match v {
        Value::Int(i) => Some(*i),
        Value::Bool(b) => Some(*b as i64),
        Value::Float(f) if f.is_finite() => Some(f.trunc() as i64),
        _ => None,
    }
}

/// The tile of a record: an entity's (its at), or the record's own x and y.
fn tile_of_map(m: &Map) -> Option<Tile> {
    let point = if m.contains_key("id") && m.contains_key("at") {
        match m.get("at") {
            Some(Value::Map(p)) => p,
            _ => return None,
        }
    } else {
        m
    };
    Some((number(point.get("x")?)?, number(point.get("y")?)?))
}

fn facing_of(a: Tile, b: Tile) -> Option<&'static str> {
    let step = ((b.0 - a.0).clamp(-1, 1), (b.1 - a.1).clamp(-1, 1));
    DIRECTIONS.iter().find(|(_, d)| *d == step).map(|(n, _)| *n)
}

// -- the definition, as native_world.py hands it -------------------------------------------------------------------

pub struct MapDef {
    pub width: i64,
    pub height: i64,
    pub walls: HashSet<Tile>,
    pub areas: IndexMap<String, (i64, i64, i64, i64)>,
}

pub struct FieldDef {
    pub name: String,
    pub value: Arc<Code>,
    pub private: bool,
}

/// A state of a brain (model.py's StateDef): what it does, and when it becomes another.
pub struct StateDef {
    pub name: String,
    pub act: String,
    pub within: i64,
    pub target: Option<Arc<Code>>,
    pub away_from: Option<Arc<Code>>,
    pub for_ticks: Option<i64>,
    pub then: Option<String>,
    pub whens: Vec<(Arc<Code>, String)>,
    pub line: u32,
}

/// What an entity may leave (q:loot's q:drop).
pub struct DropDef {
    pub item: Option<String>,
    pub gold: Option<(i64, i64)>,
    pub count: (i64, i64),
    pub chance: f64,
}

pub struct EntityDef {
    pub name: String,
    pub kind: String,
    pub per_player: bool,
    pub persist: bool,
    pub step_ticks: i64,
    pub fields: Vec<FieldDef>,
    pub states: IndexMap<String, StateDef>,
    pub initial: Option<String>,
    pub loot: Vec<DropDef>,
}

pub struct SpawnDef {
    pub entity: String,
    pub area: String,
    pub count: i64,
    pub night_count: Option<i64>,
    pub respawn_ticks: i64,
}

pub struct DeathDef {
    pub kinds: Vec<String>,
    pub as_name: String,
    pub by_name: String,
    pub body: Arc<Code>,
}

pub struct CommandDef {
    pub params: Vec<String>,
    pub limit: Option<(i64, i64)>,
    /// None for a command the world's chat, party or trade brings (its builtin).
    pub body: Option<Arc<Code>>,
    pub builtin: Option<String>,
    pub by_npc: bool,
}

/// A q:quest (model.py's QuestDef): its goal is (kill or bring, the kind or the item, how many).
pub struct QuestDef {
    pub title: String,
    pub goal: (String, String, i64),
    pub level: i64,
    pub reward: Vec<(String, i64)>,
}

/// A q:npc's mind (model.py's NpcDef).
pub struct NpcDef {
    pub name: String,
    pub instruction: String,
    pub tools: IndexMap<String, String>,
    pub model: String,
    pub knowledge: Option<String>,
    pub memory: bool,
    pub budget: i64,
    pub max_tools: i64,
    pub lines: Vec<String>,
}

/// A q:chat: its channels (a reach in tiles; None, the whole world) and the words its filter stars.
pub struct ChatDef {
    pub channels: IndexMap<String, Option<i64>>,
    pub words: Vec<String>,
}

pub struct WorldDef {
    pub name: String,
    pub tick_rate: i64,
    pub players: usize,
    pub map: MapDef,
    pub entities: IndexMap<String, EntityDef>,
    pub hero: String,
    pub commands: IndexMap<String, CommandDef>,
    pub every: Vec<(i64, Arc<Code>)>,
    pub on_join: Vec<Arc<Code>>,
    pub on_leave: Vec<Arc<Code>>,
    pub variables: Vec<(String, Arc<Code>)>,
    pub spawns: Vec<SpawnDef>,
    pub deaths: Vec<DeathDef>,
    pub day_ticks: Option<i64>,
    pub night: f64,
    pub functions: Arc<Functions>,
    /// E3c: the ledger (a currency: what a hero starts with; an item: what it is), the chat, a party's size, the
    /// quests, the NPCs and what they know, how far a player sees, and each kind's private fields.
    pub currencies: IndexMap<String, i64>,
    pub items: IndexMap<String, Map>,
    pub chat: Option<ChatDef>,
    pub party_size: Option<i64>,
    pub quests: IndexMap<String, QuestDef>,
    pub npcs: IndexMap<String, NpcDef>,
    pub knowledge: IndexMap<String, String>,
    pub reach: Option<i64>,
    pub private: IndexMap<String, HashSet<String>>,
}

impl WorldDef {
    /// model.py's ledger: the world keeps one when it has a currency or an item.
    pub fn ledger(&self) -> bool {
        !self.currencies.is_empty() || !self.items.is_empty()
    }

    /// The fields the ledger alone writes: the bag, and each currency.
    pub fn ledger_field(&self, name: &str) -> bool {
        self.ledger() && (name == "bag" || self.currencies.contains_key(name))
    }
}

fn key<'a>(m: &'a Map, k: &str) -> Result<&'a Value, String> {
    m.get(k).ok_or_else(|| format!("the definition has no {k}"))
}

fn int_of(v: &Value) -> Result<i64, String> {
    v.as_whole()
        .ok_or_else(|| "a number was expected".to_string())
}

fn str_of(v: &Value) -> Result<String, String> {
    match v {
        Value::Str(s) => Ok(s.clone()),
        _ => Err("a text was expected".into()),
    }
}

fn list_of(v: &Value) -> Result<&Vec<Value>, String> {
    match v {
        Value::List(x) | Value::Tuple(x) => Ok(x),
        _ => Err("a list was expected".into()),
    }
}

fn opt_int(v: &Value) -> Result<Option<i64>, String> {
    match v {
        Value::Null => Ok(None),
        v => int_of(v).map(Some),
    }
}

fn opt_str(v: &Value) -> Result<Option<String>, String> {
    match v {
        Value::Null => Ok(None),
        v => str_of(v).map(Some),
    }
}

fn pair_of(v: &Value) -> Result<(i64, i64), String> {
    let p = list_of(v)?;
    Ok((int_of(&p[0])?, int_of(&p[1])?))
}

fn map_of(v: &Value) -> Result<&Map, String> {
    match v {
        Value::Map(m) => Ok(m),
        _ => Err("a record was expected".into()),
    }
}

impl WorldDef {
    /// The definition from native_world.py's export, its codes already loaded (by their numbers).
    pub fn from_value(v: &Value, codes: &[Arc<Code>]) -> Result<WorldDef, String> {
        let d = map_of(v)?;
        let code = |v: &Value| -> Result<Arc<Code>, String> {
            let n = int_of(v)? as usize;
            codes.get(n).cloned().ok_or_else(|| format!("no code {n}"))
        };
        let m = map_of(key(d, "map")?)?;
        let mut walls = HashSet::default();
        for w in list_of(key(m, "walls")?)? {
            let w = list_of(w)?;
            walls.insert((int_of(&w[0])?, int_of(&w[1])?));
        }
        let mut areas = IndexMap::default();
        for (name, b) in map_of(key(m, "areas")?)? {
            let b = list_of(b)?;
            areas.insert(
                name.clone(),
                (
                    int_of(&b[0])?,
                    int_of(&b[1])?,
                    int_of(&b[2])?,
                    int_of(&b[3])?,
                ),
            );
        }
        let mut entities = IndexMap::default();
        for (name, e) in map_of(key(d, "entities")?)? {
            let e = map_of(e)?;
            let mut fields = Vec::new();
            for f in list_of(key(e, "fields")?)? {
                let f = map_of(f)?;
                fields.push(FieldDef {
                    name: str_of(key(f, "name")?)?,
                    value: code(key(f, "value")?)?,
                    private: matches!(key(f, "private")?, Value::Bool(true)),
                });
            }
            let opt_code = |v: &Value| -> Result<Option<Arc<Code>>, String> {
                match v {
                    Value::Null => Ok(None),
                    v => code(v).map(Some),
                }
            };
            let mut states = IndexMap::default();
            for (sname, st) in map_of(key(e, "states")?)? {
                let st = map_of(st)?;
                let mut whens = Vec::new();
                for w in list_of(key(st, "whens")?)? {
                    let w = list_of(w)?;
                    whens.push((code(&w[0])?, str_of(&w[1])?));
                }
                states.insert(
                    sname.clone(),
                    StateDef {
                        name: sname.clone(),
                        act: str_of(key(st, "do")?)?,
                        within: int_of(key(st, "within")?)?,
                        target: opt_code(key(st, "target")?)?,
                        away_from: opt_code(key(st, "away_from")?)?,
                        for_ticks: opt_int(key(st, "for_ticks")?)?,
                        then: opt_str(key(st, "then")?)?,
                        whens,
                        line: int_of(key(st, "line")?)? as u32,
                    },
                );
            }
            let mut loot = Vec::new();
            for dr in list_of(key(e, "loot")?)? {
                let dr = map_of(dr)?;
                loot.push(DropDef {
                    item: opt_str(key(dr, "item")?)?,
                    gold: match key(dr, "gold")? {
                        Value::Null => None,
                        g => Some(pair_of(g)?),
                    },
                    count: pair_of(key(dr, "count")?)?,
                    chance: match key(dr, "chance")? {
                        Value::Float(f) => *f,
                        v => int_of(v)? as f64,
                    },
                });
            }
            entities.insert(
                name.clone(),
                EntityDef {
                    name: name.clone(),
                    kind: str_of(key(e, "kind")?)?,
                    per_player: matches!(key(e, "per_player")?, Value::Bool(true)),
                    persist: matches!(key(e, "persist")?, Value::Bool(true)),
                    step_ticks: int_of(key(e, "step_ticks")?)?,
                    fields,
                    states,
                    initial: opt_str(key(e, "initial")?)?,
                    loot,
                },
            );
        }
        let mut commands = IndexMap::default();
        for (name, c) in map_of(key(d, "commands")?)? {
            let c = map_of(c)?;
            let limit = match key(c, "limit")? {
                Value::Null => None,
                l => {
                    let l = list_of(l)?;
                    Some((int_of(&l[0])?, int_of(&l[1])?))
                }
            };
            commands.insert(
                name.clone(),
                CommandDef {
                    params: list_of(key(c, "params")?)?
                        .iter()
                        .map(str_of)
                        .collect::<Result<_, _>>()?,
                    limit,
                    body: match key(c, "body")? {
                        Value::Int(n) if *n < 0 => None,
                        b => Some(code(b)?),
                    },
                    builtin: opt_str(key(c, "builtin")?)?,
                    by_npc: matches!(key(c, "by")?, Value::Str(s) if s == "npc"),
                },
            );
        }
        let codes_of = |k: &str| -> Result<Vec<Arc<Code>>, String> {
            list_of(key(d, k)?)?.iter().map(code).collect()
        };
        let mut every = Vec::new();
        for r in list_of(key(d, "every")?)? {
            let r = list_of(r)?;
            every.push((int_of(&r[0])?, code(&r[1])?));
        }
        let mut variables = Vec::new();
        for r in list_of(key(d, "variables")?)? {
            let r = list_of(r)?;
            variables.push((str_of(&r[0])?, code(&r[1])?));
        }
        let mut spawns = Vec::new();
        for sp in list_of(key(d, "spawns")?)? {
            let sp = map_of(sp)?;
            spawns.push(SpawnDef {
                entity: str_of(key(sp, "entity")?)?,
                area: str_of(key(sp, "area")?)?,
                count: int_of(key(sp, "count")?)?,
                night_count: opt_int(key(sp, "night_count")?)?,
                respawn_ticks: int_of(key(sp, "respawn_ticks")?)?,
            });
        }
        let mut deaths = Vec::new();
        for de in list_of(key(d, "deaths")?)? {
            let de = map_of(de)?;
            deaths.push(DeathDef {
                kinds: list_of(key(de, "kinds")?)?
                    .iter()
                    .map(str_of)
                    .collect::<Result<_, _>>()?,
                as_name: str_of(key(de, "as")?)?,
                by_name: str_of(key(de, "by")?)?,
                body: code(key(de, "body")?)?,
            });
        }
        let mut functions = Functions::default();
        for (name, f) in map_of(key(d, "functions")?)? {
            let f = map_of(f)?;
            functions.insert(
                name.clone(),
                Arc::new(Function {
                    name: name.clone(),
                    code: code(key(f, "body")?)?,
                    params: list_of(key(f, "params")?)?
                        .iter()
                        .map(str_of)
                        .collect::<Result<_, _>>()?,
                    line: int_of(key(f, "line")?)? as u32,
                }),
            );
        }
        Ok(WorldDef {
            name: str_of(key(d, "name")?)?,
            tick_rate: int_of(key(d, "tick_rate")?)?,
            players: int_of(key(d, "players")?)? as usize,
            map: MapDef {
                width: int_of(key(m, "width")?)?,
                height: int_of(key(m, "height")?)?,
                walls,
                areas,
            },
            entities,
            hero: str_of(key(d, "hero")?)?,
            commands,
            every,
            on_join: codes_of("on_join")?,
            on_leave: codes_of("on_leave")?,
            variables,
            spawns,
            deaths,
            day_ticks: match key(d, "day_ticks")? {
                Value::Null => None,
                v => Some(int_of(v)?),
            },
            night: match key(d, "night")? {
                Value::Float(f) => *f,
                v => int_of(v)? as f64,
            },
            functions: Arc::new(functions),
            currencies: map_of(key(d, "currencies")?)?
                .iter()
                .map(|(k, v)| Ok((k.clone(), int_of(v)?)))
                .collect::<Result<_, String>>()?,
            items: map_of(key(d, "items")?)?
                .iter()
                .map(|(k, v)| Ok((k.clone(), map_of(v)?.clone())))
                .collect::<Result<_, String>>()?,
            chat: match key(d, "chat")? {
                Value::Null => None,
                c => {
                    let c = map_of(c)?;
                    Some(ChatDef {
                        channels: map_of(key(c, "channels")?)?
                            .iter()
                            .map(|(k, v)| Ok((k.clone(), opt_int(v)?)))
                            .collect::<Result<_, String>>()?,
                        words: list_of(key(c, "words")?)?
                            .iter()
                            .map(str_of)
                            .collect::<Result<_, _>>()?,
                    })
                }
            },
            party_size: opt_int(key(d, "party_size")?)?,
            quests: map_of(key(d, "quests")?)?
                .iter()
                .map(|(k, q)| {
                    let q = map_of(q)?;
                    let goal = list_of(key(q, "goal")?)?;
                    Ok((
                        k.clone(),
                        QuestDef {
                            title: str_of(key(q, "title")?)?,
                            goal: (str_of(&goal[0])?, str_of(&goal[1])?, int_of(&goal[2])?),
                            level: int_of(key(q, "level")?)?,
                            reward: list_of(key(q, "reward")?)?
                                .iter()
                                .map(|r| {
                                    let r = list_of(r)?;
                                    Ok((str_of(&r[0])?, int_of(&r[1])?))
                                })
                                .collect::<Result<_, String>>()?,
                        },
                    ))
                })
                .collect::<Result<_, String>>()?,
            npcs: map_of(key(d, "npcs")?)?
                .iter()
                .map(|(k, n)| {
                    let n = map_of(n)?;
                    Ok((
                        k.clone(),
                        NpcDef {
                            name: k.clone(),
                            instruction: str_of(key(n, "instruction")?)?,
                            tools: list_of(key(n, "tools")?)?
                                .iter()
                                .map(|t| {
                                    let t = list_of(t)?;
                                    Ok((str_of(&t[0])?, str_of(&t[1])?))
                                })
                                .collect::<Result<_, String>>()?,
                            model: str_of(key(n, "model")?)?,
                            knowledge: opt_str(key(n, "knowledge")?)?,
                            memory: matches!(key(n, "memory")?, Value::Bool(true)),
                            budget: int_of(key(n, "budget")?)?,
                            max_tools: int_of(key(n, "max_tools")?)?,
                            lines: list_of(key(n, "lines")?)?
                                .iter()
                                .map(str_of)
                                .collect::<Result<_, _>>()?,
                        },
                    ))
                })
                .collect::<Result<_, String>>()?,
            knowledge: map_of(key(d, "knowledge")?)?
                .iter()
                .map(|(k, v)| Ok((k.clone(), str_of(v)?)))
                .collect::<Result<_, String>>()?,
            reach: opt_int(key(d, "reach")?)?,
            private: map_of(key(d, "private")?)?
                .iter()
                .map(|(k, v)| {
                    Ok((
                        k.clone(),
                        list_of(v)?
                            .iter()
                            .map(str_of)
                            .collect::<Result<_, String>>()?,
                    ))
                })
                .collect::<Result<_, String>>()?,
        })
    }
}

// -- a tick's outcome, and what the world keeps ---------------------------------------------------------------------

/// What a q:emit (or the world's own tell) said: the event as it is sent, where, and to whom.
#[derive(Clone, Debug)]
pub struct Event {
    pub message: Map,
    pub tile: Option<Tile>,
    pub to: Option<String>,
    pub everyone: bool,
    pub accounts: Option<Vec<String>>,
}

#[derive(Default, Debug)]
pub struct TickOut {
    pub tick: i64,
    pub entries: Vec<Value>,
    pub acks: IndexMap<String, Vec<Value>>,
    pub refused: IndexMap<String, Vec<Value>>,
    pub joined: IndexMap<String, String>,
    pub left: Vec<String>,
    pub full: Vec<String>,
}

/// Where a write went, for its undoing: an entity's field (or a record inside one), a world's variable (or inside
/// one), or an entity of the world itself (made or gone).
#[derive(Clone, Debug)]
enum Root {
    Entities,
    Entity(String),
    Vars,
    /// What a q:spawn keeps (its living, and when the next are due), by its number.
    Spawned(String),
    /// The ledger's books, the parties, the trades.
    Books,
    Parties,
    Trades,
}

#[derive(Clone, Debug)]
struct Undo {
    root: Root,
    path: Vec<String>,
    key: String,
    old: Option<Value>,
}

/// What a tick may raise as Python's World raises it: a world's error with its line, a refusal, or Python's own
/// (int() of a text in a q:loop from=: the world does not catch it).
#[derive(Debug)]
pub enum Raised {
    Rule(String, u32),
    Refused(String),
    Python(VmError),
}

impl Raised {
    fn of(e: VmError) -> Raised {
        match e.kind {
            ErrorKind::Refused => Raised::Refused(e.message),
            ErrorKind::Python(_) | ErrorKind::Host => Raised::Python(e),
            _ => Raised::Rule(e.message, e.line.unwrap_or(0)),
        }
    }
}

fn rule_at(message: impl Into<String>, line: u32) -> VmError {
    VmError {
        kind: ErrorKind::Rule,
        message: message.into(),
        line: Some(line),
    }
}

fn refused(reason: impl Into<String>) -> VmError {
    VmError::new(ErrorKind::Refused, reason)
}

pub struct World {
    pub def: Arc<WorldDef>,
    pub tick: i64,
    pub vars: Map,
    pub entities: Map,
    pub stored: Map,
    pub players: IndexMap<String, String>,
    pub rng: Rng,
    pub rates: IndexMap<String, Vec<i64>>,
    pub counters: IndexMap<String, i64>,
    pub errors: Vec<Map>,
    pub errors_made: usize,
    journal: Option<Vec<Undo>>,
    pub dirty: HashSet<String>,
    pub gone: HashSet<String>,
    pub events: Vec<Event>,
    pub vars_changed: bool,
    cells: HashMap<Tile, HashSet<String>>,
    cell_of: HashMap<String, Tile>,
    /// The same index by kind (a text kind's; kind is the world's: a q:set cannot change it), for nearest(x, kind).
    kinds: HashMap<String, HashMap<Tile, HashSet<String>>>,
    kind_of: HashMap<String, String>,
    events_mark: usize,
    /// Entities that left the world in this tick, as they were: a block that held one reads it still.
    dead: HashMap<String, Map>,
    depth: Arc<AtomicUsize>,
    pub spawned: Map,
    pub books: Map,
    pub parties: Map,
    pub trades: Map,
    /// Those on their way (q:travel), those made for a while (q:spawn for=), those whose on-death is running.
    pub travelers: HashSet<String>,
    pub expiring: HashSet<String>,
    dying: HashSet<String>,
    walkable_areas: HashMap<String, Vec<Tile>>,
    /// Where the world is as the ledger books (world.py's source), and the tick's q:asks for the minds (npc.py).
    pub source: String,
    pub asks: Vec<Value>,
    asks_mark: usize,
}

// -- a world's values, as world.py keeps them ----------------------------------------------------------------------

impl World {
    fn entity_map(&self, id: &str) -> Option<&Map> {
        match self.entities.get(id) {
            Some(Value::Map(m)) => Some(m),
            _ => self.dead.get(id),
        }
    }

    /// world.py's plain(): what the world keeps (an entity is copied as its record); anything else is a RuleError.
    fn plain(&self, v: &Value, depth: usize) -> Result<Value, String> {
        if depth > 16 {
            return Err("a value nested more than 16 deep".into());
        }
        Ok(match v {
            Value::Float(f) if !f.is_finite() => {
                let text = if f.is_nan() {
                    "nan"
                } else if *f > 0.0 {
                    "inf"
                } else {
                    "-inf"
                };
                return Err(format!("{text} is not a number a world keeps"));
            }
            Value::List(x) | Value::Tuple(x) => Value::List(
                x.iter()
                    .map(|i| self.plain(i, depth + 1))
                    .collect::<Result<_, _>>()?,
            ),
            Value::Map(m) => {
                let mut out = Map::with_capacity_and_hasher(m.len(), Default::default());
                for (k, i) in m {
                    out.insert(k.clone(), self.plain(i, depth + 1)?);
                }
                Value::Map(out)
            }
            Value::Entity(id) => match self.entity_map(id) {
                Some(m) => self.plain(&Value::Map(m.clone()), depth)?,
                None => Value::Null,
            },
            other => other.clone(),
        })
    }

    pub fn is_entity(&self, v: &Value) -> bool {
        matches!(v, Value::Entity(id) if self.entities.contains_key(id))
    }

    fn entity_of(&self, v: &Value, line: u32) -> Result<String, VmError> {
        if let Value::Str(s) = v {
            if self.entities.contains_key(s) {
                return Ok(s.clone());
            }
        }
        match v {
            Value::Entity(id) if self.entities.contains_key(id) => Ok(id.clone()),
            _ => Err(rule_at(
                "q:move entity= is not an entity of the world",
                line,
            )),
        }
    }

    fn entity_value(&self, id: &str) -> Value {
        Value::Entity(id.to_string())
    }

    /// world.py's tile_of: a tile ({x, y} or [x, y]), an entity's tile, or the tile of the entity of that id.
    pub fn tile_of(&self, v: &Value) -> Option<Tile> {
        match v {
            Value::Str(s) => match self.entities.get(s) {
                Some(Value::Map(m)) => tile_of_map(m),
                _ => None,
            },
            Value::Entity(id) => self.entity_map(id).and_then(tile_of_map),
            Value::Map(m) => tile_of_map(m),
            Value::List(x) | Value::Tuple(x) if x.len() == 2 => {
                Some((number(&x[0])?, number(&x[1])?))
            }
            _ => None,
        }
    }

    /// The tile of an entity of the world (or one gone this tick), by its id.
    pub fn entity_tile(&self, id: &str) -> Option<Tile> {
        self.entity_map(id).and_then(tile_of_map)
    }

    pub fn walkable(&self, t: Tile) -> bool {
        let m = &self.def.map;
        0 <= t.0 && t.0 < m.width && 0 <= t.1 && t.1 < m.height && !m.walls.contains(&t)
    }

    pub fn area_tile(&self, name: &str, line: u32) -> Result<Tile, VmError> {
        let (x0, y0, x1, y1) = self.def.map.areas[name];
        let middle = ((x0 + x1).div_euclid(2), (y0 + y1).div_euclid(2));
        let mut tiles: Vec<Tile> = (x0..=x1)
            .flat_map(|x| (y0..=y1).map(move |y| (x, y)))
            .collect();
        tiles.sort_by_key(|t| (chebyshev(*t, middle), t.1, t.0));
        tiles
            .into_iter()
            .find(|t| self.walkable(*t))
            .ok_or_else(|| {
                rule_at(
                    format!(
                        "the area {} has no tile one can stand on",
                        vm::str_repr(name)
                    ),
                    line,
                )
            })
    }

    // -- the index ---------------------------------------------------------------------------------------------

    pub fn reindex<'a>(&mut self, ids: impl IntoIterator<Item = &'a String>) {
        for eid in ids {
            let entity = self.entities.get(eid);
            let tile = entity.and_then(|e| self.tile_of(e));
            let cell = tile.map(|t| (t.0.div_euclid(CELL), t.1.div_euclid(CELL)));
            let kind = match entity {
                Some(Value::Map(m)) => match m.get("kind") {
                    Some(Value::Str(k)) => Some(k.clone()),
                    _ => None,
                },
                _ => None,
            };
            let old = self.cell_of.get(eid).copied();
            if old == cell && self.kind_of.get(eid) == kind.as_ref() {
                continue;
            }
            if let Some(old) = old {
                if let Some(members) = self.cells.get_mut(&old) {
                    members.remove(eid);
                    if members.is_empty() {
                        self.cells.remove(&old);
                    }
                }
                self.cell_of.remove(eid);
                if let Some(k) = self.kind_of.remove(eid) {
                    if let Some(cells) = self.kinds.get_mut(&k) {
                        if let Some(members) = cells.get_mut(&old) {
                            members.remove(eid);
                            if members.is_empty() {
                                cells.remove(&old);
                            }
                        }
                    }
                }
            }
            if let Some(cell) = cell {
                self.cells.entry(cell).or_default().insert(eid.clone());
                self.cell_of.insert(eid.clone(), cell);
                if let Some(k) = kind {
                    self.kinds
                        .entry(k.clone())
                        .or_default()
                        .entry(cell)
                        .or_default()
                        .insert(eid.clone());
                    self.kind_of.insert(eid.clone(), k);
                }
            }
        }
    }

    fn reindex_one(&mut self, eid: &str) {
        let id = eid.to_string();
        self.reindex(std::iter::once(&id));
    }

    pub fn cells_near(t: Tile, n: i64) -> Vec<Tile> {
        let mut out = Vec::new();
        for cx in (t.0 - n).div_euclid(CELL)..=(t.0 + n).div_euclid(CELL) {
            for cy in (t.1 - n).div_euclid(CELL)..=(t.1 + n).div_euclid(CELL) {
                out.push((cx, cy));
            }
        }
        out
    }

    pub fn near_ids(&self, t: Tile, n: i64) -> Vec<String> {
        let mut out = Vec::new();
        for cell in World::cells_near(t, n) {
            if let Some(members) = self.cells.get(&cell) {
                out.extend(members.iter().cloned());
            }
        }
        out
    }

    // -- writing, as a transaction ---------------------------------------------------------------------------------

    fn container_mut(&mut self, root: &Root, path: &[String]) -> Option<&mut Map> {
        let mut target: &mut Map = match root {
            Root::Entities => &mut self.entities,
            Root::Vars => &mut self.vars,
            Root::Entity(id) => match self.entities.get_mut(id) {
                Some(Value::Map(m)) => m,
                _ => self.dead.get_mut(id)?,
            },
            Root::Spawned(i) => match self.spawned.get_mut(i) {
                Some(Value::Map(m)) => m,
                _ => return None,
            },
            Root::Books => &mut self.books,
            Root::Parties => &mut self.parties,
            Root::Trades => &mut self.trades,
        };
        for part in path {
            target = match target.get_mut(part) {
                Some(Value::Map(m)) => m,
                _ => return None,
            };
        }
        Some(target)
    }

    /// world.py's write: the value made plain, journaled, set; its entity dirty, or the world's variables changed.
    fn write(
        &mut self,
        root: Root,
        path: Vec<String>,
        key: &str,
        value: &Value,
        line: u32,
    ) -> Result<(), VmError> {
        let value = self.plain(value, 0).map_err(|m| rule_at(m, line))?;
        let live = match &root {
            Root::Entity(id) => self.entities.contains_key(id),
            _ => true,
        };
        let Some(target) = self.container_mut(&root, &path) else {
            return Err(rule_at("the world lost what it was writing", line));
        };
        let old = target.insert(key.to_string(), value);
        if let (true, Some(journal)) = (live, self.journal.as_mut()) {
            journal.push(Undo {
                root: root.clone(),
                path,
                key: key.to_string(),
                old,
            });
        }
        match root {
            Root::Entity(id) if live => {
                self.dirty.insert(id);
            }
            Root::Vars => self.vars_changed = true,
            _ => {}
        }
        Ok(())
    }

    fn write_field(&mut self, id: &str, key: &str, value: Value, line: u32) -> Result<(), VmError> {
        self.write(Root::Entity(id.to_string()), Vec::new(), key, &value, line)
    }

    fn begin(&mut self) {
        self.journal = Some(Vec::new());
        self.events_mark = self.events.len();
        self.asks_mark = self.asks.len();
    }

    fn commit(&mut self) {
        self.journal = None;
    }

    fn rollback(&mut self) {
        let mut touched: Vec<String> = Vec::new();
        for undo in self.journal.take().unwrap_or_default().into_iter().rev() {
            if let Some(target) = self.container_mut(&undo.root, &undo.path) {
                match undo.old {
                    Some(old) => {
                        target.insert(undo.key.clone(), old);
                    }
                    None => {
                        target.shift_remove(&undo.key);
                    }
                }
            }
            match undo.root {
                Root::Entities => touched.push(undo.key),
                Root::Entity(id) => touched.push(id),
                _ => {}
            }
        }
        self.events.truncate(self.events_mark);
        self.asks.truncate(self.asks_mark);
        let entities = &self.entities;
        self.gone.retain(|g| !entities.contains_key(g));
        self.reindex(touched.iter());
        // an entity undone where it was, made or gone again: on its way, or ending, as it now says
        for id in touched {
            let travels = self.entities.contains_key(&id)
                && self.field_of(&id, "_path").is_some_and(vm::truthy);
            let ends = self.entities.contains_key(&id)
                && self.field_of(&id, "_expires").is_some_and(vm::truthy);
            if travels {
                self.travelers.insert(id.clone());
            } else {
                self.travelers.remove(&id);
            }
            if ends {
                self.expiring.insert(id);
            } else {
                self.expiring.remove(&id);
            }
        }
    }

    /// world.py's put: a key of a container of the world set (or, with None, taken out), journaled.
    fn put(&mut self, root: Root, key: &str, value: Option<Value>) {
        self.put_at(root, Vec::new(), key, value)
    }

    /// put, into a record inside the root (an entity's bag, a book of an asset).
    fn put_at(&mut self, root: Root, path: Vec<String>, key: &str, value: Option<Value>) {
        let Some(target) = self.container_mut(&root, &path) else {
            return;
        };
        let old = match value {
            Some(v) => target.insert(key.to_string(), v),
            None => target.shift_remove(key),
        };
        if let Some(journal) = self.journal.as_mut() {
            journal.push(Undo {
                root,
                path,
                key: key.to_string(),
                old,
            });
        }
    }

    fn error(&mut self, place: &str, message: &str, line: u32) {
        let mut e = Map::default();
        e.insert("tick".into(), Value::Int(self.tick));
        e.insert("where".into(), Value::Str(place.into()));
        e.insert(
            "line".into(),
            if line > 0 {
                Value::Int(line as i64)
            } else {
                Value::Null
            },
        );
        e.insert("message".into(), Value::Str(message.into()));
        self.errors.push(e);
        self.errors_made += 1;
        if self.errors.len() > MAX_ERRORS {
            let extra = self.errors.len() - MAX_ERRORS;
            self.errors.drain(..extra);
        }
    }
}

// -- what the world does ----------------------------------------------------------------------------------------------

impl World {
    fn field_of(&self, id: &str, key: &str) -> Option<&Value> {
        self.entity_map(id).and_then(|m| m.get(key))
    }

    fn move_to(&mut self, id: &str, to: Tile, line: u32) -> Result<(), VmError> {
        if !self.walkable(to) {
            return Err(refused("Blocked."));
        }
        let here = self.tile_of(&self.entity_value(id));
        if let Some(here) = here {
            if chebyshev(here, to) == 1 {
                let until = self
                    .field_of(id, "_until")
                    .cloned()
                    .unwrap_or(Value::Int(0));
                let now = Value::Int(self.tick);
                if vm::compare(self, 4, &until, &now)? {
                    return Err(refused("Still moving."));
                }
                let kind = match self.field_of(id, "_type") {
                    Some(Value::Str(s)) => s.clone(),
                    _ => String::new(),
                };
                let step = self
                    .def
                    .entities
                    .get(&kind)
                    .map(|e| e.step_ticks)
                    .unwrap_or(0);
                self.write_field(id, "_until", Value::Int(self.tick + step), line)?;
                let facing = facing_of(here, to).map_or(Value::Null, |f| Value::Str(f.into()));
                self.write_field(id, "facing", facing, line)?;
            }
        }
        let mut at = Map::default();
        at.insert("x".into(), Value::Int(to.0));
        at.insert("y".into(), Value::Int(to.1));
        self.write_field(id, "at", Value::Map(at), line)?;
        self.reindex_one(id);
        Ok(())
    }

    fn stop_travel(&mut self, id: &str, line: u32) -> Result<(), VmError> {
        if self.field_of(id, "_path").is_some_and(vm::truthy) {
            self.write_field(id, "_path", Value::List(vec![]), line)?;
        }
        self.travelers.remove(id);
        Ok(())
    }

    #[allow(clippy::too_many_arguments)]
    fn emit(
        &mut self,
        name: Value,
        value: &Value,
        tile: Option<Tile>,
        of: Option<String>,
        to: Option<String>,
        everyone: bool,
        line: u32,
    ) -> Result<(), VmError> {
        if self.events.len() >= MAX_EVENTS {
            return Err(rule_at(
                format!("q:emit: more than {MAX_EVENTS} events in a tick"),
                line,
            ));
        }
        let mut message = Map::default();
        message.insert("name".into(), name);
        message.insert(
            "value".into(),
            self.plain(value, 0).map_err(|m| rule_at(m, line))?,
        );
        if let Some(t) = tile {
            let mut at = Map::default();
            at.insert("x".into(), Value::Int(t.0));
            at.insert("y".into(), Value::Int(t.1));
            message.insert("at".into(), Value::Map(at));
        }
        if let Some(of) = of {
            message.insert("of".into(), Value::Str(of));
        }
        self.events.push(Event {
            message,
            tile,
            to,
            everyone,
            accounts: None,
        });
        Ok(())
    }

    /// together.py's tell: an event to these players alone.
    fn tell(&mut self, name: &str, value: Value, accounts: Vec<String>) -> Result<(), VmError> {
        let mut message = Map::default();
        message.insert("name".into(), Value::Str(name.into()));
        message.insert(
            "value".into(),
            self.plain(&value, 0).map_err(|m| rule_at(m, 0))?,
        );
        let mut accounts: Vec<String> = accounts
            .into_iter()
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();
        accounts.sort();
        self.events.push(Event {
            message,
            tile: None,
            to: None,
            everyone: false,
            accounts: Some(accounts),
        });
        Ok(())
    }

    /// together.py's hero_of: a player's entity by its id, its account, the name it shows (when no other shows it),
    /// or itself.
    fn hero_of(&self, who: &Value) -> Option<String> {
        let has_player = |id: &str| self.field_of(id, "_player").is_some_and(vm::truthy);
        match who {
            Value::Entity(id) => {
                (self.entities.contains_key(id) && has_player(id)).then(|| id.clone())
            }
            Value::Map(_) => None,
            Value::Str(s) => {
                if let Some(id) = self.players.get(s) {
                    return Some(id.clone());
                }
                if self.entities.contains_key(s) && has_player(s) {
                    return Some(s.clone());
                }
                let named: Vec<&String> = self
                    .players
                    .values()
                    .filter(|e| self.field_of(e, "name").is_some_and(|n| py_eq(n, who)))
                    .collect();
                (named.len() == 1).then(|| named[0].clone())
            }
            _ => None,
        }
    }

    fn say(&mut self, channel: Value, to: &Value, text: &Value, line: u32) -> Result<(), VmError> {
        let accounts = if matches!(to, Value::Null) || matches!(to, Value::Str(s) if s == "all") {
            self.players.keys().cloned().collect()
        } else {
            let Some(hero) = self.hero_of(to) else {
                return Err(rule_at("q:say to= is a player's entity, or all", line));
            };
            match self.field_of(&hero, "_player") {
                Some(Value::Str(a)) => vec![a.clone()],
                _ => vec![],
            }
        };
        let text: String = vm::py_str(text).chars().take(MAX_LINE).collect();
        let mut value = Map::default();
        value.insert("channel".into(), channel);
        value.insert("who".into(), Value::Str("world".into()));
        value.insert("text".into(), Value::Str(text));
        self.tell("chat", Value::Map(value), accounts)
    }

    /// machine.py's place: an area's name as written, else the value (a tile, an entity, an area's name).
    fn place(
        &self,
        kind: &Value,
        value: &Value,
        raw: &Value,
        what: &str,
        line: u32,
    ) -> Result<Tile, VmError> {
        let area = match (kind, value) {
            (Value::Str(k), Value::Str(v)) if k == "area" => Some(v.clone()),
            (_, Value::Str(v)) if self.def.map.areas.contains_key(v) => Some(v.clone()),
            _ => None,
        };
        if let Some(area) = area {
            return self.area_tile(&area, line);
        }
        self.tile_of(value).ok_or_else(|| {
            rule_at(
                format!(
                    "{what}=\"{}\": not a tile, an entity or an area of the map",
                    vm::py_str(raw)
                ),
                line,
            )
        })
    }

    fn effect(&mut self, name: &str, args: Vec<Value>) -> Result<(), VmError> {
        let line = args.first().and_then(|l| l.as_whole()).unwrap_or(0) as u32;
        let a = &args[1..];
        match name {
            "move" => {
                let id = self.entity_of(&a[0], line)?;
                self.stop_travel(&id, line)?;
                let to = self.place(&a[1], &a[2], &a[3], "q:move to", line)?;
                self.move_to(&id, to, line)
            }
            "emit" => {
                // event, has_value, value, kind, spot, at, has_to, to
                let has_value = vm::truthy(&a[1]);
                let (mut tile, mut of, mut player) = (None, None, None);
                if !matches!(a[5], Value::Null) {
                    let at_area = match (&a[3], &a[4]) {
                        (Value::Str(k), Value::Str(v)) if k == "area" => Some(v.clone()),
                        (_, Value::Str(v)) if self.def.map.areas.contains_key(v) => Some(v.clone()),
                        _ => None,
                    };
                    if let Some(area) = at_area {
                        tile = Some(self.area_tile(&area, line)?);
                    } else {
                        let spot = match &a[4] {
                            Value::Str(s) if self.entities.contains_key(s) => {
                                Value::Entity(s.clone())
                            }
                            other => other.clone(),
                        };
                        if self.is_entity(&spot) {
                            tile = self.tile_of(&spot);
                            if let Value::Entity(id) = &spot {
                                of = Some(id.clone());
                            }
                        } else {
                            tile = Some(self.tile_of(&spot).ok_or_else(|| {
                                rule_at(
                                    format!(
                                        "q:emit at=\"{}\": not a tile, an entity or an area of the map",
                                        vm::py_str(&a[5])
                                    ),
                                    line,
                                )
                            })?);
                        }
                    }
                }
                let has_to = vm::truthy(&a[6]);
                if has_to {
                    let target = match &a[7] {
                        Value::Str(s) => {
                            if self.entities.contains_key(s) {
                                Value::Entity(s.clone())
                            } else {
                                Value::Null
                            }
                        }
                        other => other.clone(),
                    };
                    let owner = match &target {
                        Value::Entity(id) if self.entities.contains_key(id) => {
                            self.field_of(id, "_player").cloned()
                        }
                        _ => None,
                    };
                    match owner {
                        Some(Value::Str(account)) => player = Some(account),
                        _ => {
                            return Err(rule_at(
                                "q:emit to= is not a player's entity in the world",
                                line,
                            ))
                        }
                    }
                }
                let value = if has_value { a[2].clone() } else { Value::Null };
                let everyone = matches!(a[5], Value::Null) && !has_to;
                self.emit(a[0].clone(), &value, tile, of, player, everyone, line)
            }
            "say" => self.say(a[0].clone(), &a[1], &a[2], line),
            "travel" => {
                let id = self.entity_of(&a[0], line)?;
                self.stop_travel(&id, line)?;
                let to = self.place(&a[1], &a[2], &a[3], "q:move to", line)?;
                self.travel(&id, to, line)
            }
            "kill" => {
                let id = self.entity_of(&a[0], line)?;
                let by = if vm::truthy(&a[1]) {
                    self.entity_from(&a[2]).map_or(Value::Null, Value::Entity)
                } else {
                    Value::Null
                };
                self.kill(&id, by)
            }
            "loot" => {
                let of = self.entity_of(&a[0], line)?;
                let to = self.entity_of(&a[1], line)?;
                self.loot(&of, &to, line)
            }
            "spawn" => {
                let count = a[2].as_whole().unwrap_or(1);
                let ticks = a[3].as_whole();
                self.spawn_now(&a[0], &a[1], count, ticks, line)
            }
            "give" | "take" => {
                // holder, item, count, amount, currency
                let holder = self.entity_of(&a[0], line)?;
                if name == "give" {
                    self.give(&holder, &a[1], &a[2], &a[3], &a[4], line)
                } else {
                    self.take(&holder, &a[1], &a[2], &a[3], &a[4], line)
                }
            }
            "pay" => {
                let payer = self.entity_of(&a[0], line)?;
                let to = self.entity_of(&a[1], line)?;
                self.pay(&payer, &to, &a[2], &a[3], line)
            }
            "ask" => self.ask(&a[1], &a[0], &a[2], line),
            "reward" => {
                let to = self.entity_of(&a[0], line)?;
                self.reward(&to, &a[1], line)
            }
            other => Err(rule_at(
                format!("<q:{other}> does not run on the engine yet"),
                line,
            )),
        }
    }
}

// -- what a world does by itself (life.py) ------------------------------------------------------------------------

fn far(a: Tile, b: Tile) -> i64 {
    chebyshev(a, b)
}

fn tile_list(t: Tile) -> Value {
    Value::List(vec![Value::Int(t.0), Value::Int(t.1)])
}

impl World {
    fn occupied(&self, tile: Tile, but: Option<&str>) -> bool {
        // near_ids(tile, 0): the one cell the tile is in
        let cell = (tile.0.div_euclid(CELL), tile.1.div_euclid(CELL));
        self.cells.get(&cell).is_some_and(|members| {
            members
                .iter()
                .any(|eid| Some(eid.as_str()) != but && self.entity_tile(eid) == Some(tile))
        })
    }

    fn free(&self, tile: Tile, but: Option<&str>) -> bool {
        self.walkable(tile) && !self.occupied(tile, but)
    }

    /// life.py's way: the shortest way from start to a tile where arrived holds, within limit tiles of start, around
    /// walls (and around entities, unless through): its tiles after start; [] if start is one; None if none.
    fn way(
        &self,
        start: Tile,
        arrived: &dyn Fn(Tile) -> bool,
        limit: i64,
        but: Option<&str>,
        through: bool,
    ) -> Option<Vec<Tile>> {
        if arrived(start) {
            return Some(Vec::new());
        }
        let mut came: HashMap<Tile, Option<Tile>> = HashMap::default();
        came.insert(start, None);
        let mut queue = std::collections::VecDeque::from([start]);
        while let Some(here) = queue.pop_front() {
            for (dx, dy) in STEPS {
                let there = (here.0 + dx, here.1 + dy);
                if came.contains_key(&there) || far(there, start) > limit || !self.walkable(there) {
                    continue;
                }
                if !through && self.occupied(there, but) && !arrived(there) {
                    continue;
                }
                came.insert(there, Some(here));
                if arrived(there) {
                    let mut out = vec![there];
                    while came[out.last().unwrap()] != Some(start) {
                        let back = came[out.last().unwrap()].unwrap();
                        out.push(back);
                    }
                    out.reverse();
                    return Some(out);
                }
                queue.push_back(there);
            }
        }
        None
    }

    fn walkable_in(&mut self, area: &str) -> Vec<Tile> {
        if let Some(kept) = self.walkable_areas.get(area) {
            return kept.clone();
        }
        let (x0, y0, x1, y1) = self.def.map.areas[area];
        let tiles: Vec<Tile> = (y0..=y1)
            .flat_map(|y| (x0..=x1).map(move |x| (x, y)))
            .filter(|t| self.walkable(*t))
            .collect();
        self.walkable_areas.insert(area.to_string(), tiles.clone());
        tiles
    }

    /// life.py's make_at: an entity of the spec at a free tile of the area, from the world's random; None if full.
    fn make_at(&mut self, spec: &str, area: &str) -> Result<Option<String>, VmError> {
        let (x0, y0, x1, y1) = self.def.map.areas[area];
        let mut taken = HashSet::default();
        for cx in x0.div_euclid(CELL)..=x1.div_euclid(CELL) {
            for cy in y0.div_euclid(CELL)..=y1.div_euclid(CELL) {
                if let Some(members) = self.cells.get(&(cx, cy)) {
                    for eid in members {
                        taken.insert(self.entity_tile(eid));
                    }
                }
            }
        }
        let tiles: Vec<Tile> = self
            .walkable_in(area)
            .into_iter()
            .filter(|t| !taken.contains(&Some(*t)))
            .collect();
        if tiles.is_empty() {
            return Ok(None);
        }
        let tile = tiles[self.rng.randrange(tiles.len() as i64).unwrap_or(0) as usize];
        let mut entity = self.make(spec, None, None)?;
        entity.insert("at".into(), tile_value(tile));
        entity.insert("_home".into(), tile_list(tile));
        let id = vm::py_str(&entity["id"]);
        self.put(Root::Entities, &id, Some(Value::Map(entity.clone())));
        self.dirty.insert(id.clone());
        self.reindex_one(&id);
        self.mint_start(&entity);
        Ok(Some(id))
    }

    fn set_own(&mut self, id: &str, key: &str, value: Value) {
        if let Some(Value::Map(m)) = self.entities.get_mut(id) {
            m.insert(key.to_string(), value);
        }
    }

    /// q:spawn in a block: count more now, gone after for_ticks if given.
    fn spawn_now(
        &mut self,
        name: &Value,
        area: &Value,
        count: i64,
        for_ticks: Option<i64>,
        line: u32,
    ) -> Result<(), VmError> {
        let spec = match name {
            Value::Str(n) => self
                .def
                .entities
                .get(n)
                .filter(|e| !e.per_player)
                .map(|e| e.name.clone()),
            _ => None,
        };
        let Some(spec) = spec else {
            return Err(rule_at(
                format!(
                    "q:spawn entity=\"{}\": not an entity of the world it may make",
                    vm::py_str(name)
                ),
                line,
            ));
        };
        let area = match area {
            Value::Str(a) if self.def.map.areas.contains_key(a) => a.clone(),
            other => {
                return Err(rule_at(
                    format!(
                        "q:spawn area=\"{}\": the map has no such area",
                        vm::py_str(other)
                    ),
                    line,
                ))
            }
        };
        for _ in 0..count.max(0) {
            let Some(id) = self.make_at(&spec, &area)? else {
                break;
            };
            if let Some(ticks) = for_ticks.filter(|t| *t != 0) {
                self.set_own(&id, "_expires", Value::Int(self.tick + ticks));
                self.expiring.insert(id);
            }
        }
        Ok(())
    }

    /// An entity out of the world (its spawn makes another respawn= later).
    fn remove(&mut self, id: &str) {
        let entity = match self.entities.get(id) {
            Some(Value::Map(m)) => m.clone(),
            _ => return,
        };
        let kind = entity
            .get("kind")
            .map_or_else(|| "None".to_string(), vm::py_str);
        self.spend_all(&entity, &format!("gone: {kind}"));
        self.dead.insert(id.to_string(), entity.clone());
        self.put(Root::Entities, id, None);
        self.gone.insert(id.to_string());
        self.dirty.remove(id);
        self.travelers.remove(id);
        self.expiring.remove(id);
        if let Some(Value::Str(index)) = entity.get("_spawn") {
            let respawn = index
                .parse::<usize>()
                .ok()
                .and_then(|i| self.def.spawns.get(i))
                .map(|s| s.respawn_ticks)
                .unwrap_or(0);
            if let Some(Value::Map(kept)) = self.spawned.get(index) {
                let alive: Vec<Value> = match kept.get("alive") {
                    Some(Value::List(a)) => {
                        a.iter().filter(|a| vm::py_str(a) != id).cloned().collect()
                    }
                    _ => vec![],
                };
                let mut due = match kept.get("due") {
                    Some(Value::List(d)) => d.clone(),
                    _ => vec![],
                };
                due.push(Value::Int(self.tick + respawn));
                let root = Root::Spawned(index.clone());
                self.put(root.clone(), "alive", Some(Value::List(alive)));
                self.put(root, "due", Some(Value::List(due)));
            }
        }
        self.reindex_one(id);
    }

    /// q:kill: the on-death of its kind, then it goes (a player's stays: its on-death brings it back).
    fn kill(&mut self, id: &str, by: Value) -> Result<(), VmError> {
        if !self.entities.contains_key(id) || self.dying.contains(id) {
            return Ok(());
        }
        self.dying.insert(id.to_string());
        let def = self.def.clone();
        for death in def.deaths.iter() {
            let kind = self.field_of(id, "kind").cloned().unwrap_or(Value::Null);
            if !death
                .kinds
                .iter()
                .any(|k| py_eq(&Value::Str(k.clone()), &kind))
            {
                continue;
            }
            let mut locals = Locals::default();
            locals.insert(death.as_name.clone(), Value::Entity(id.to_string()));
            locals.insert(death.by_name.clone(), by.clone());
            if let Err(e) = self.evaluate(&death.body, locals) {
                self.dying.remove(id);
                return Err(e);
            }
        }
        self.dying.remove(id);
        let player = self.field_of(id, "_player").cloned().unwrap_or(Value::Null);
        if matches!(player, Value::Null) && self.entities.contains_key(id) {
            self.remove(id);
        }
        Ok(())
    }

    /// q:loot (a world with no ledger): the drops of an entity, rolled: an item to the bag, gold to the gold.
    fn loot(&mut self, of: &str, to: &str, line: u32) -> Result<(), VmError> {
        if self.def.ledger() {
            return self.loot_booked(of, to, line);
        }
        let kind = match self.field_of(of, "_type") {
            Some(Value::Str(t)) => t.clone(),
            _ => String::new(),
        };
        let def = self.def.clone();
        let Some(spec) = def.entities.get(&kind) else {
            return Ok(());
        };
        let to_id = self
            .field_of(to, "id")
            .map(vm::py_str)
            .unwrap_or_else(|| "None".into());
        for drop in spec.loot.iter() {
            if self.rng.random() >= drop.chance {
                continue;
            }
            if let Some(item) = &drop.item {
                let current = match self.field_of(to, "bag") {
                    Some(Value::Map(bag)) => bag.get(item).cloned().unwrap_or(Value::Int(0)),
                    _ => {
                        return Err(rule_at(
                            format!(
                                "q:loot: {to_id} has no bag to put {item} in (a field that is a record: \
                                 <q:field name=\"bag\" value=\"{{ {{}} }}\" />)"
                            ),
                            line,
                        ))
                    }
                };
                let n = self.rng.randint(drop.count.0, drop.count.1).unwrap_or(0);
                let sum = python_add(current, n)?;
                self.write(
                    Root::Entity(to.to_string()),
                    vec!["bag".into()],
                    item,
                    &sum,
                    line,
                )?;
            } else {
                let gold = match self.field_of(to, "gold") {
                    Some(g @ (Value::Int(_) | Value::Float(_))) => g.clone(),
                    _ => {
                        return Err(rule_at(
                            format!(
                                "q:loot: {to_id} has no gold to add to (a field that is a number)"
                            ),
                            line,
                        ))
                    }
                };
                let (lo, hi) = drop.gold.unwrap_or((0, 0));
                let n = self.rng.randint(lo, hi).unwrap_or(0);
                self.write_field(to, "gold", python_add(gold, n)?, line)?;
            }
        }
        Ok(())
    }

    /// q:travel: the way there, kept on the entity, walked a step a tick.
    fn travel(&mut self, id: &str, to: Tile, line: u32) -> Result<(), VmError> {
        let Some(here) = self.entity_tile(id) else {
            return Err(rule_at("q:travel: the entity is nowhere", line));
        };
        let through = !matches!(self.field_of(id, "_player"), None | Some(Value::Null));
        let path = self
            .way(here, &|t| t == to, TRAVEL_SEARCH, Some(id), through)
            .ok_or_else(|| refused("No way there."))?;
        let value = Value::List(path.iter().map(|t| tile_list(*t)).collect());
        self.write_field(id, "_path", value, line)?;
        if !path.is_empty() {
            self.travelers.insert(id.to_string());
        }
        Ok(())
    }

    // -- a tick of the world's own life -------------------------------------------------------------------------

    fn live(&mut self) -> Result<(), Raised> {
        self.source = "q:spawn".into();
        self.spawns().map_err(Raised::of)?;
        let mut expiring: Vec<String> = self.expiring.iter().cloned().collect();
        expiring.sort();
        for id in expiring {
            let due = match self.field_of(&id, "_expires") {
                Some(v) => v.as_whole().unwrap_or(0),
                None => 0,
            };
            if self.entities.contains_key(&id) && due <= self.tick {
                self.remove(&id);
            }
        }
        let mut travelers: Vec<String> = self.travelers.iter().cloned().collect();
        travelers.sort();
        for id in travelers {
            self.go(&id);
        }
        self.think()
    }

    fn spawns(&mut self) -> Result<(), VmError> {
        let night = self.is_night();
        let def = self.def.clone();
        for (i, sp) in def.spawns.iter().enumerate() {
            let key = i.to_string();
            let (alive0, due0) = match self.spawned.get(&key) {
                Some(Value::Map(kept)) => (
                    match kept.get("alive") {
                        Some(Value::List(a)) => a.clone(),
                        _ => vec![],
                    },
                    match kept.get("due") {
                        Some(Value::List(d)) => {
                            d.iter().filter_map(|t| t.as_whole()).collect::<Vec<i64>>()
                        }
                        _ => vec![],
                    },
                ),
                _ => (vec![], vec![]),
            };
            let wanted = match (night, sp.night_count) {
                (true, Some(n)) => n,
                _ => sp.count,
            };
            let missing = wanted - alive0.len() as i64 - due0.len() as i64;
            let mut due = due0.clone();
            due.extend(std::iter::repeat_n(self.tick, missing.max(0) as usize));
            let mut later: Vec<i64> = due.iter().copied().filter(|t| *t > self.tick).collect();
            let mut alive = alive0;
            let tick = self.tick;
            let now = due.iter().filter(|t| **t <= tick).count();
            for _ in 0..now {
                if alive.len() as i64 >= wanted {
                    continue;
                }
                match self.make_at(&sp.entity, &sp.area)? {
                    None => later.push(self.tick + 1),
                    Some(id) => {
                        self.set_own(&id, "_spawn", Value::Str(key.clone()));
                        alive.push(Value::Str(id));
                    }
                }
            }
            later.sort();
            let kept = entry(vec![
                ("alive", Value::List(alive)),
                (
                    "due",
                    Value::List(later.into_iter().map(Value::Int).collect()),
                ),
            ]);
            self.spawned.insert(key, kept);
        }
        Ok(())
    }

    fn go(&mut self, id: &str) {
        let path = match self.entities.get(id).and_then(|e| e.get("_path")) {
            Some(Value::List(p)) if !p.is_empty() => p.clone(),
            _ => {
                self.travelers.remove(id);
                return;
            }
        };
        let until = self
            .field_of(id, "_until")
            .and_then(|u| u.as_whole())
            .unwrap_or(0);
        if until > self.tick {
            return;
        }
        self.begin();
        let next = self.tile_of(&path[0]);
        let stepped = match next {
            Some(t) => self
                .move_to(id, t, 0)
                .and_then(|_| self.write_field(id, "_path", Value::List(path[1..].to_vec()), 0)),
            None => Err(rule_at("not a tile", 0)),
        };
        if stepped.is_err() {
            self.rollback();
            let _ = self.write_field(id, "_path", Value::List(vec![]), 0); // blocked: the way ends here
            self.travelers.remove(id);
            return;
        }
        self.commit();
        if !self.field_of(id, "_path").is_some_and(vm::truthy) {
            self.travelers.remove(id);
        }
    }

    fn think(&mut self) -> Result<(), Raised> {
        let mut heroes: Vec<String> = self.players.values().cloned().collect();
        heroes.sort();
        let mut cells = HashSet::default();
        for hid in heroes {
            if let Some(tile) = self.entity_tile(&hid) {
                cells.extend(World::cells_near(tile, AWAKE));
            }
        }
        let mut awake: Vec<String> = cells
            .iter()
            .filter_map(|c| self.cells.get(c))
            .flatten()
            .cloned()
            .collect::<HashSet<_>>()
            .into_iter()
            .collect();
        awake.sort();
        self.source = "q:brain".into();
        let def = self.def.clone();
        for id in awake {
            if !self.entities.contains_key(&id) {
                continue;
            }
            let kind = match self.field_of(&id, "_type") {
                Some(Value::Str(t)) => t.clone(),
                _ => continue,
            };
            let Some(spec) = def.entities.get(&kind) else {
                continue;
            };
            if spec.states.is_empty() {
                continue;
            }
            self.begin();
            match self.brain(&id, spec) {
                Ok(()) => self.commit(),
                Err(e) => match Raised::of(e) {
                    Raised::Rule(message, line) => {
                        self.rollback();
                        self.error(&format!("q:brain of {id}"), &message, line);
                    }
                    Raised::Refused(reason) => {
                        self.rollback();
                        self.error(
                            &format!("q:brain of {id}"),
                            &format!("refused: {reason}"),
                            0,
                        );
                    }
                    python => return Err(python),
                },
            }
        }
        Ok(())
    }

    fn become_state(&mut self, id: &str, state: &str) -> Result<(), VmError> {
        self.write_field(id, "state", Value::Str(state.into()), 0)?;
        self.write_field(id, "_since", Value::Int(self.tick), 0)
    }

    /// life.py's _entity: an entity of the world, by its id or itself.
    fn entity_from(&self, v: &Value) -> Option<String> {
        match v {
            Value::Str(s) if self.entities.contains_key(s) => Some(s.clone()),
            Value::Entity(id) if self.entities.contains_key(id) => Some(id.clone()),
            _ => None,
        }
    }

    fn brain(&mut self, id: &str, spec: &EntityDef) -> Result<(), VmError> {
        let current = self.field_of(id, "state").cloned();
        let mut state = match &current {
            Some(Value::Str(s)) if spec.states.contains_key(s) => &spec.states[s],
            _ => &spec.states[spec.initial.as_deref().unwrap_or("")],
        };
        let mut local = Locals::default();
        local.insert("it".into(), Value::Entity(id.to_string()));
        for (condition, next) in state.whens.iter() {
            if vm::truthy(&self.evaluate(condition, local.clone())?) {
                if *next != state.name {
                    self.become_state(id, next)?;
                    state = &spec.states[next];
                }
                break;
            }
        }
        if let Some(ticks) = state.for_ticks {
            let since = self
                .field_of(id, "_since")
                .and_then(|s| s.as_whole())
                .unwrap_or(0);
            if self.tick - since >= ticks {
                let then = state.then.clone().unwrap_or_default();
                self.become_state(id, &then)?;
                state = &spec.states[&then];
            }
        }
        if let Some(target) = &state.target {
            let found = self.evaluate(target, local.clone())?;
            let found = self.entity_from(&found).unwrap_or_default();
            let had = self
                .field_of(id, "target")
                .cloned()
                .unwrap_or(Value::Str(String::new()));
            if !py_eq(&Value::Str(found.clone()), &had) {
                self.write_field(id, "target", Value::Str(found), state.line)?;
            }
        }
        let Some(here) = self.entity_tile(id) else {
            return Ok(());
        };
        let until = self
            .field_of(id, "_until")
            .and_then(|u| u.as_whole())
            .unwrap_or(0);
        if until > self.tick || state.act == "stand" {
            return Ok(());
        }
        match state.act.as_str() {
            "wander" => {
                if self.rng.random() >= WANDER_CHANCE {
                    return Ok(());
                }
                let home = match self.field_of(id, "_home") {
                    Some(h) if vm::truthy(h) => self.tile_of(h).unwrap_or(here),
                    _ => here,
                };
                let ways: Vec<Tile> = STEPS
                    .iter()
                    .map(|(dx, dy)| (here.0 + dx, here.1 + dy))
                    .filter(|t| self.free(*t, Some(id)) && far(*t, home) <= state.within)
                    .collect();
                if !ways.is_empty() {
                    let pick = ways[self.rng.randrange(ways.len() as i64).unwrap_or(0) as usize];
                    self.move_to(id, pick, state.line)?;
                }
            }
            "chase" => {
                let prey = match self.field_of(id, "target") {
                    Some(Value::Str(t)) if self.entities.contains_key(t) => Some(t.clone()),
                    _ => None,
                };
                let Some(there) = prey.and_then(|p| self.entity_tile(&p)) else {
                    return Ok(());
                };
                if far(here, there) <= 1 {
                    return Ok(());
                }
                let path = self.way(
                    here,
                    &|t| far(t, there) <= 1 && t != there,
                    CHASE_SEARCH,
                    Some(id),
                    false,
                );
                if let Some(first) = path.and_then(|p| p.first().copied()) {
                    self.move_to(id, first, state.line)?;
                }
            }
            "flee" => {
                let Some(code) = &state.away_from else {
                    return Ok(());
                };
                let threat = self.evaluate(code, local)?;
                let Some(there) = self.entity_from(&threat).and_then(|t| self.entity_tile(&t))
                else {
                    return Ok(());
                };
                let ways: Vec<(usize, Tile)> = STEPS
                    .iter()
                    .enumerate()
                    .map(|(i, (dx, dy))| (i, (here.0 + dx, here.1 + dy)))
                    .filter(|(_, t)| self.free(*t, Some(id)) && far(*t, there) > far(here, there))
                    .collect();
                // max by (how far, then the first of the ways)
                if let Some((_, best)) = ways
                    .iter()
                    .max_by_key(|(i, t)| (far(*t, there), -(*i as i64)))
                    .copied()
                {
                    self.move_to(id, best, state.line)?;
                }
            }
            _ => {}
        }
        Ok(())
    }
}

/// Python's `n + k` of a number a world keeps and a whole number; anything else is Python's TypeError.
fn python_add(n: Value, k: i64) -> Result<Value, VmError> {
    match n {
        Value::Int(i) => i
            .checked_add(k)
            .map(Value::Int)
            .ok_or_else(|| VmError::new(ErrorKind::Expression, "a whole number past 64 bits")),
        Value::Bool(b) => Ok(Value::Int(b as i64 + k)),
        Value::Float(f) => Ok(Value::Float(f + k as f64)),
        other => Err(VmError::new(
            ErrorKind::Python(vm::Raise::Type),
            format!(
                "unsupported operand type(s) for +: '{}' and 'int'",
                vm::type_name_of(&other)
            ),
        )),
    }
}

// -- the world's functions (rules.py's _functions) -------------------------------------------------------------------

/// A function of rules.py's: its name as Python says it in a TypeError, its parameters, how many have no default.
fn world_signature(name: &str) -> Option<(&'static str, &'static [&'static str], usize)> {
    Some(match name {
        "tile" => ("Interpreter._functions.<locals>.tile", &["x"], 1),
        "walkable" => ("Interpreter._functions.<locals>.walkable", &["x"], 1),
        "ahead" => (
            "Interpreter._functions.<locals>.ahead",
            &["x", "direction"],
            2,
        ),
        "distance" => ("Interpreter._functions.<locals>.distance", &["a", "b"], 2),
        "near" => ("Interpreter._functions.<locals>.near", &["a", "b", "n"], 2),
        "in_area" => ("Interpreter._functions.<locals>.in_area", &["x", "name"], 2),
        "area" => ("Interpreter._functions.<locals>.area", &["name"], 1),
        "heroes" => ("Interpreter._functions.<locals>.heroes", &[], 0),
        "entities" => ("Interpreter._functions.<locals>.entities", &["kind"], 0),
        "entity" => ("Interpreter._functions.<locals>.entity", &["x"], 1),
        "tick" | "seconds" => ("Interpreter._functions.<locals>.<lambda>", &[], 0),
        "random" => (
            "Interpreter._functions.<locals>.random",
            &["low", "high"],
            0,
        ),
        "chance" => ("Interpreter._functions.<locals>.chance", &["p"], 1),
        "pick" => ("Interpreter._functions.<locals>.pick", &["items"], 1),
        "now" => ("Interpreter._functions.<locals>.now", &[], 0),
        "nearest" => ("Life.nearest", &["x", "kind", "n"], 2),
        "fighting" => ("Life.fighting", &[], 0),
        "in_fight" => ("Life.in_fight", &["x"], 1),
        "sees" => ("Life.line_of_sight", &["a", "b"], 2),
        "is_night" => ("Life.is_night", &[], 0),
        "daytime" => ("Life.daytime", &[], 0),
        "balance" => ("Ledger.balance", &["x", "currency"], 1),
        "has" => ("Ledger.has", &["x", "item", "n"], 2),
        "item" => ("Ledger.item_of", &["name"], 1),
        "party_of" => ("Together.party_of", &["x"], 1),
        "party_near" => ("Together.party_near", &["x", "n"], 1),
        "quest_goal" => ("Together.quest_goal", &["x"], 1),
        "quest_done" => ("Together.quest_done", &["x"], 1),
        "quest_level" | "quest_title" => ("Interpreter._functions.<locals>.<lambda>", &["q"], 1),
        "price" | "heals" | "slot" => ("Interpreter._functions.<locals>.<lambda>", &["i"], 1),
        "bonus" => (
            "Interpreter._functions.<locals>.<lambda>",
            &["i", "name"],
            2,
        ),
        _ => return None,
    })
}

/// The names the engine runs itself (native_world.py checks a world calls no other).
pub const WORLD_FUNCTIONS: [&str; 36] = [
    "tile",
    "walkable",
    "ahead",
    "distance",
    "near",
    "in_area",
    "area",
    "heroes",
    "entities",
    "entity",
    "tick",
    "seconds",
    "random",
    "chance",
    "pick",
    "now",
    "sqrt",
    "nearest",
    "fighting",
    "in_fight",
    "sees",
    "is_night",
    "daytime",
    "balance",
    "has",
    "item",
    "party_of",
    "party_near",
    "quest_goal",
    "quest_done",
    "quest_level",
    "quest_title",
    "price",
    "heals",
    "slot",
    "bonus",
];

fn tile_value(t: Tile) -> Value {
    let mut m = Map::default();
    m.insert("x".into(), Value::Int(t.0));
    m.insert("y".into(), Value::Int(t.1));
    Value::Map(m)
}

fn failed(name: &str, why: impl std::fmt::Display) -> VmError {
    VmError::new(ErrorKind::Expression, format!("{name}() failed: {why}"))
}

impl World {
    fn daytime(&self) -> f64 {
        match self.def.day_ticks {
            Some(day) if day != 0 => self.tick.rem_euclid(day) as f64 / day as f64,
            _ => 0.0,
        }
    }

    fn is_night(&self) -> bool {
        self.def.day_ticks.is_some_and(|d| d != 0) && self.daytime() >= 1.0 - self.def.night
    }

    fn sorted_entity_ids(&self) -> Vec<String> {
        let mut ids: Vec<String> = self.entities.keys().cloned().collect();
        ids.sort();
        ids
    }

    fn nearest(&mut self, x: &Value, kind: &Value, n: &Value) -> Result<Value, VmError> {
        let Some(tile) = self.tile_of(x) else {
            return Ok(Value::Null);
        };
        let me = match x {
            Value::Entity(id) => Some(id.clone()),
            Value::Map(m) => m.get("id").map(vm::py_str),
            other => Some(vm::py_str(other)),
        };
        let n = match vm::native(self, "int", vec![n.clone()], vec![]) {
            Ok(Value::Int(i)) => i,
            Ok(_) => return Err(failed("nearest", "a whole number past 64 bits")),
            Err(e) => {
                let why = e.message.trim_start_matches("int() failed: ").to_string();
                return Err(failed("nearest", why));
            }
        };
        // life.py walks the ids sorted and keeps the first of the nearest: the least (far, id), found in one pass;
        // a kind that is a text is read from the index of that kind (the same members, those of the kind alone)
        let mut best: Option<(i64, &String)> = None;
        let empty = HashMap::default();
        let (index, by_kind) = match kind {
            Value::Str(k) => (self.kinds.get(k).unwrap_or(&empty), true),
            _ => (&self.cells, false),
        };
        for cell in World::cells_near(tile, n) {
            let Some(members) = index.get(&cell) else {
                continue;
            };
            for eid in members {
                if Some(eid) == me.as_ref() {
                    continue;
                }
                // other.get('kind') != kind: one with no kind is None's
                if !by_kind && !py_eq(self.field_of(eid, "kind").unwrap_or(&Value::Null), kind) {
                    continue;
                }
                let Some(there) = self.entity_tile(eid) else {
                    continue;
                };
                let far = chebyshev(tile, there);
                if far <= n && best.is_none_or(|(b, id)| (far, eid) < (b, id)) {
                    best = Some((far, eid));
                }
            }
        }
        let best = best.map(|(f, id)| (f, id.clone()));
        Ok(best.map_or(Value::Null, |(_, id)| Value::Entity(id)))
    }

    fn fighting_ids(&self) -> Vec<String> {
        let mut out = Vec::new();
        for eid in self.sorted_entity_ids() {
            let target = self
                .field_of(&eid, "target")
                .cloned()
                .unwrap_or(Value::Null);
            let prey = match &target {
                Value::Str(s) if !s.is_empty() && self.entities.contains_key(s) => s.clone(),
                _ => continue,
            };
            match self.field_of(&eid, "hp") {
                Some(Value::Int(h)) if *h <= 0 => continue,
                Some(Value::Float(h)) if *h <= 0.0 => continue,
                Some(Value::Bool(false)) => continue,
                _ => {}
            }
            let (a, b) = (self.entity_tile(&eid), self.entity_tile(&prey));
            if let (Some(a), Some(b)) = (a, b) {
                if chebyshev(a, b) <= 1 {
                    out.push(eid);
                }
            }
        }
        out
    }

    fn world_call(
        &mut self,
        name: &str,
        args: Vec<Value>,
        kwargs: Vec<(String, Value)>,
    ) -> Result<Value, VmError> {
        if name == "sqrt" {
            return vm::native(self, "sqrt", args, kwargs);
        }
        let Some(sig) = world_signature(name) else {
            return Err(VmError::new(
                ErrorKind::Expression,
                format!("function {} is not defined", vm::str_repr(name)),
            ));
        };
        let a = vm::bind(sig, args, kwargs).map_err(|why| failed(name, why))?;
        let arg = |i: usize| a.get(i).cloned().unwrap_or(Value::Null);
        match name {
            "tile" => Ok(self.tile_of(&arg(0)).map_or(Value::Null, tile_value)),
            "walkable" => Ok(Value::Bool(
                self.tile_of(&arg(0)).is_some_and(|t| self.walkable(t)),
            )),
            "ahead" => {
                let step = match &arg(1) {
                    Value::Str(d) => DIRECTIONS.iter().find(|(n, _)| n == d).map(|(_, s)| *s),
                    _ => None,
                };
                Ok(match (self.tile_of(&arg(0)), step) {
                    (Some(t), Some(s)) => tile_value((t.0 + s.0, t.1 + s.1)),
                    _ => Value::Null,
                })
            }
            "distance" => Ok(match (self.tile_of(&arg(0)), self.tile_of(&arg(1))) {
                (Some(a), Some(b)) => Value::Int(chebyshev(a, b)),
                _ => Value::Null,
            }),
            "near" => {
                let d = match (self.tile_of(&arg(0)), self.tile_of(&arg(1))) {
                    (Some(a), Some(b)) => Value::Int(chebyshev(a, b)),
                    _ => return Ok(Value::Bool(false)),
                };
                let n = if a.len() > 2 { arg(2) } else { Value::Int(1) };
                // `d <= n`, Python's: not the Core's (no numeric texts)
                if let Value::Str(_) = n {
                    return Err(failed(
                        name,
                        format!(
                            "'<=' not supported between instances of 'int' and '{}'",
                            "str"
                        ),
                    ));
                }
                vm::compare(self, 3, &d, &n)
                    .map(Value::Bool)
                    .map_err(|e| failed(name, e.message.trim_start_matches("cannot compare: ")))
            }
            "in_area" => {
                let t = self.tile_of(&arg(0));
                let b = match &arg(1) {
                    Value::Str(n) => self.def.map.areas.get(n).copied(),
                    _ => None,
                };
                Ok(Value::Bool(match (t, b) {
                    (Some(t), Some(b)) => b.0 <= t.0 && t.0 <= b.2 && b.1 <= t.1 && t.1 <= b.3,
                    _ => false,
                }))
            }
            "area" => match &arg(0) {
                Value::Str(n) if self.def.map.areas.contains_key(n) => {
                    let t = self.area_tile(n, 0).map_err(|e| failed(name, e.message))?;
                    Ok(tile_value(t))
                }
                _ => Ok(Value::Null),
            },
            "heroes" => {
                let mut ids: Vec<String> = self.players.values().cloned().collect();
                ids.sort();
                Ok(Value::List(ids.into_iter().map(Value::Entity).collect()))
            }
            "entities" => {
                let kind = arg(0);
                Ok(Value::List(
                    self.sorted_entity_ids()
                        .into_iter()
                        .filter(|id| {
                            matches!(kind, Value::Null)
                                || self.field_of(id, "kind").is_some_and(|k| py_eq(k, &kind))
                        })
                        .map(Value::Entity)
                        .collect(),
                ))
            }
            "entity" => Ok(match arg(0) {
                Value::Str(s) => {
                    if self.entities.contains_key(&s) {
                        Value::Entity(s)
                    } else {
                        Value::Null
                    }
                }
                v if self.is_entity(&v) => v,
                _ => Value::Null,
            }),
            "tick" => Ok(Value::Int(self.tick)),
            "seconds" => Ok(Value::Float(self.tick as f64 / self.def.tick_rate as f64)),
            "random" => {
                let (low, high) = (arg(0), arg(1));
                match (&low, &high) {
                    (Value::Null, Value::Null) => Ok(Value::Float(self.rng.random())),
                    (Value::Null, _) | (_, Value::Null) => Err(failed(
                        name,
                        "random() takes no arguments, or two: random(a, b)",
                    )),
                    _ => {
                        let lo = self.whole(name, &low)?;
                        let hi = self.whole(name, &high)?;
                        self.rng.randint(lo, hi).map(Value::Int).ok_or_else(|| {
                            failed(name, format!("empty range in randrange({lo}, {})", hi + 1))
                        })
                    }
                }
            }
            "chance" => {
                let p = match vm::native(self, "float", vec![arg(0)], vec![]) {
                    Ok(Value::Float(p)) => p,
                    Ok(_) => 0.0,
                    Err(e) => {
                        return Err(failed(
                            name,
                            e.message.trim_start_matches("float() failed: "),
                        ))
                    }
                };
                if !(0.0..=1.0).contains(&p) {
                    let mut text = String::new();
                    write_float(p, &mut text);
                    return Err(failed(
                        name,
                        format!("chance({text}): the probability is between 0 and 1"),
                    ));
                }
                Ok(Value::Bool(self.rng.random() < p))
            }
            "pick" => {
                let items = match arg(0) {
                    Value::List(x) | Value::Tuple(x) => x,
                    Value::Str(s) => s.chars().map(|c| Value::Str(c.to_string())).collect(),
                    Value::Map(m) => m.keys().map(|k| Value::Str(k.clone())).collect(),
                    Value::Entity(id) => self
                        .entity_map(&id)
                        .map(|m| m.keys().map(|k| Value::Str(k.clone())).collect())
                        .unwrap_or_default(),
                    other => {
                        return Err(failed(
                            name,
                            format!("'{}' object is not iterable", vm::type_name_of(&other)),
                        ))
                    }
                };
                if items.is_empty() {
                    return Err(failed(name, "pick() of an empty list"));
                }
                let i = self.rng.randrange(items.len() as i64).unwrap_or(0) as usize;
                Ok(items[i].clone())
            }
            "now" => Err(failed(
                name,
                "now() is the machine's clock; a world's time is tick() (and seconds())",
            )),
            "nearest" => {
                let n = if a.len() > 2 {
                    arg(2)
                } else {
                    Value::Int(AWAKE)
                };
                self.nearest(&arg(0), &arg(1), &n)
            }
            "fighting" => Ok(Value::List(
                self.fighting_ids().into_iter().map(Value::Entity).collect(),
            )),
            "in_fight" => {
                let id = match arg(0) {
                    Value::Str(s) if self.entities.contains_key(&s) => s,
                    Value::Entity(id) if self.entities.contains_key(&id) => id,
                    _ => return Ok(Value::Bool(false)),
                };
                Ok(Value::Bool(self.fighting_ids().iter().any(|e| {
                    *e == id
                        || self
                            .field_of(e, "target")
                            .is_some_and(|t| matches!(t, Value::Str(s) if *s == id))
                })))
            }
            "sees" => {
                let (Some(ta), Some(tb)) = (self.tile_of(&arg(0)), self.tile_of(&arg(1))) else {
                    return Ok(Value::Bool(false));
                };
                let steps = chebyshev(ta, tb);
                for k in 1..steps {
                    let x = ta.0 + round_half_even((tb.0 - ta.0) as f64 * k as f64 / steps as f64);
                    let y = ta.1 + round_half_even((tb.1 - ta.1) as f64 * k as f64 / steps as f64);
                    if self.def.map.walls.contains(&(x, y)) {
                        return Ok(Value::Bool(false));
                    }
                }
                Ok(Value::Bool(true))
            }
            "is_night" => Ok(Value::Bool(self.is_night())),
            "daytime" => Ok(Value::Float(self.daytime())),
            "party_of" => Ok(Value::List(
                self.party_of(&arg(0))
                    .into_iter()
                    .map(Value::Entity)
                    .collect(),
            )),
            "party_near" => {
                let n = a.get(1).cloned();
                Ok(Value::List(
                    self.party_near(&arg(0), n.as_ref())?
                        .into_iter()
                        .map(Value::Entity)
                        .collect(),
                ))
            }
            other => match self.ledger_call(other, &a) {
                Some(r) => r,
                None => unreachable!(),
            },
        }
    }

    /// Python's int(x) where a world's function takes one: its failure said as the function's.
    fn whole(&mut self, name: &str, v: &Value) -> Result<i64, VmError> {
        match vm::native(self, "int", vec![v.clone()], vec![]) {
            Ok(Value::Int(i)) => Ok(i),
            Ok(_) => Err(failed(name, "a whole number past 64 bits")),
            Err(e) => Err(failed(name, e.message.trim_start_matches("int() failed: "))),
        }
    }
}

/// Python's round() of a float to a whole number: half to even.
fn round_half_even(f: f64) -> i64 {
    let r = f.round();
    if (f - f.trunc()).abs() == 0.5 {
        (2.0 * (f / 2.0).round()) as i64
    } else {
        r as i64
    }
}

// -- the machine's host ---------------------------------------------------------------------------------------------

// What Python's dir() names of a value, without those that start with _ (the Core's suggestions: the same on 3.12
// and 3.13), and of the interpreter's scope, a ChainMap (rules.py's scope).
const INT_NAMES: [&str; 11] = [
    "as_integer_ratio",
    "bit_count",
    "bit_length",
    "conjugate",
    "denominator",
    "from_bytes",
    "imag",
    "is_integer",
    "numerator",
    "real",
    "to_bytes",
];
const FLOAT_NAMES: [&str; 7] = [
    "as_integer_ratio",
    "conjugate",
    "fromhex",
    "hex",
    "imag",
    "is_integer",
    "real",
];
const STR_NAMES: [&str; 47] = [
    "capitalize",
    "casefold",
    "center",
    "count",
    "encode",
    "endswith",
    "expandtabs",
    "find",
    "format",
    "format_map",
    "index",
    "isalnum",
    "isalpha",
    "isascii",
    "isdecimal",
    "isdigit",
    "isidentifier",
    "islower",
    "isnumeric",
    "isprintable",
    "isspace",
    "istitle",
    "isupper",
    "join",
    "ljust",
    "lower",
    "lstrip",
    "maketrans",
    "partition",
    "removeprefix",
    "removesuffix",
    "replace",
    "rfind",
    "rindex",
    "rjust",
    "rpartition",
    "rsplit",
    "rstrip",
    "split",
    "splitlines",
    "startswith",
    "strip",
    "swapcase",
    "title",
    "translate",
    "upper",
    "zfill",
];
const LIST_NAMES: [&str; 11] = [
    "append", "clear", "copy", "count", "extend", "index", "insert", "pop", "remove", "reverse",
    "sort",
];
const TUPLE_NAMES: [&str; 2] = ["count", "index"];
const CHAINMAP_NAMES: [&str; 14] = [
    "clear",
    "copy",
    "fromkeys",
    "get",
    "items",
    "keys",
    "maps",
    "new_child",
    "parents",
    "pop",
    "popitem",
    "setdefault",
    "update",
    "values",
];

impl Host for World {
    fn variable(&mut self, name: &str) -> Option<Value> {
        self.vars.get(name).cloned()
    }

    fn field(&mut self, id: &str, key: &str) -> Result<Option<Value>, VmError> {
        Ok(self.field_of(id, key).cloned())
    }

    fn keys(&mut self, id: &str) -> Result<Vec<String>, VmError> {
        Ok(self
            .entity_map(id)
            .map(|m| m.keys().cloned().collect())
            .unwrap_or_default())
    }

    fn call(
        &mut self,
        name: &str,
        args: Vec<Value>,
        kwargs: Vec<(String, Value)>,
    ) -> Result<Value, VmError> {
        self.world_call(name, args, kwargs)
    }

    fn write_var(&mut self, name: &str, value: &Value, line: u32) -> Result<bool, VmError> {
        if !self.vars.contains_key(name) {
            return Ok(false);
        }
        self.write(Root::Vars, Vec::new(), name, value, line)?;
        Ok(true)
    }

    fn assign_path(
        &mut self,
        name: &str,
        root: Option<Value>,
        value: Value,
        line: u32,
    ) -> Result<Option<Value>, VmError> {
        let parts: Vec<String> = name.split('.').map(String::from).collect();
        let local = root.is_some();
        let root = root.unwrap_or_else(|| self.vars.get(&parts[0]).cloned().unwrap_or(Value::Null));
        let bad = |what: &str| rule_at(format!("q:set name=\"{name}\": {what}"), line);
        match root {
            Value::Entity(id) => {
                let entity = self.entities.contains_key(&id);
                let mut target = self
                    .entity_map(&id)
                    .cloned()
                    .map(Value::Map)
                    .unwrap_or(Value::Null);
                for part in &parts[1..parts.len() - 1] {
                    target = match &target {
                        Value::Map(m) => m.get(part).cloned().unwrap_or(Value::Null),
                        _ => Value::Null,
                    };
                    if !matches!(target, Value::Map(_)) {
                        return Err(bad(&format!("{part} is not a record")));
                    }
                }
                let key = &parts[parts.len() - 1];
                if entity
                    && parts.len() == 2
                    && (key == "id" || key == "kind" || key.starts_with('_'))
                {
                    return Err(bad(&format!("an entity's {key} is the world's")));
                }
                if entity && parts.len() > 1 && self.def.ledger_field(&parts[1]) {
                    return Err(bad(&format!(
                        "{} is the ledger's: q:give, q:take and q:pay change it",
                        parts[1]
                    )));
                }
                self.write(
                    Root::Entity(id),
                    parts[1..parts.len() - 1].to_vec(),
                    key,
                    &value,
                    line,
                )?;
                Ok(None)
            }
            Value::Map(mut m) if local => {
                // a record the block holds: its own copy, changed and handed back
                {
                    let mut target: &mut Map = &mut m;
                    for part in &parts[1..parts.len() - 1] {
                        target = match target.get_mut(part) {
                            Some(Value::Map(t)) => t,
                            _ => return Err(bad(&format!("{part} is not a record"))),
                        };
                    }
                    let plain = self.plain(&value, 0).map_err(|e| rule_at(e, line))?;
                    target.insert(parts[parts.len() - 1].clone(), plain);
                }
                Ok(Some(Value::Map(m)))
            }
            Value::Map(_) => {
                // a world's variable that is a record
                let mut path = parts.clone();
                path.truncate(parts.len() - 1);
                let mut target = self.vars.get(&parts[0]).cloned().unwrap_or(Value::Null);
                for part in &parts[1..parts.len() - 1] {
                    target = match &target {
                        Value::Map(m) => m.get(part).cloned().unwrap_or(Value::Null),
                        _ => Value::Null,
                    };
                    if !matches!(target, Value::Map(_)) {
                        return Err(bad(&format!("{part} is not a record")));
                    }
                }
                self.write(Root::Vars, path, &parts[parts.len() - 1], &value, line)?;
                Ok(None)
            }
            _ => Err(bad(&format!("{} is not an entity or a record", parts[0]))),
        }
    }

    fn effect(&mut self, name: &str, args: Vec<Value>) -> Result<(), VmError> {
        World::effect(self, name, args)
    }

    fn names_of(&mut self, v: &Value) -> Result<Vec<String>, VmError> {
        let own = |names: &[&str]| names.iter().map(|n| n.to_string()).collect();
        Ok(match v {
            Value::Map(m) => m.keys().filter(|k| !k.starts_with('_')).cloned().collect(),
            Value::Entity(id) => self
                .entity_map(id)
                .map(|m| m.keys().filter(|k| !k.starts_with('_')).cloned().collect())
                .unwrap_or_default(),
            Value::Int(_) | Value::Big(_) | Value::Bool(_) => own(&INT_NAMES),
            Value::Float(_) => own(&FLOAT_NAMES),
            Value::Str(_) | Value::Json(_) => own(&STR_NAMES),
            Value::List(_) => own(&LIST_NAMES),
            Value::Tuple(_) => own(&TUPLE_NAMES),
            Value::Null => Vec::new(),
        })
    }

    fn scope_names(&mut self, _locals: &Locals) -> Vec<String> {
        CHAINMAP_NAMES.iter().map(|n| n.to_string()).collect()
    }
}

// -- a tick -----------------------------------------------------------------------------------------------------------

/// world.py's _args_ok: plain values, two levels deep at most.
fn args_ok(v: &Value, depth: usize) -> bool {
    match v {
        Value::Null | Value::Bool(_) | Value::Int(_) | Value::Big(_) | Value::Str(_) => true,
        Value::Float(f) => f.is_finite(),
        _ if depth >= 2 => false,
        Value::List(x) => x.iter().all(|i| args_ok(i, depth + 1)),
        Value::Map(m) => m.values().all(|i| args_ok(i, depth + 1)),
        _ => false,
    }
}

/// Python's json.dumps(v), with its separators; sort_keys sorts every record's keys.
pub fn dumps(v: &Value, sort_keys: bool, out: &mut String) {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(true) => out.push_str("true"),
        Value::Bool(false) => out.push_str("false"),
        Value::Int(i) => out.push_str(&i.to_string()),
        Value::Big(d) => out.push_str(d),
        Value::Float(f) => {
            if f.is_nan() {
                out.push_str("NaN")
            } else if f.is_infinite() {
                out.push_str(if *f > 0.0 { "Infinity" } else { "-Infinity" })
            } else {
                write_float(*f, out)
            }
        }
        Value::Str(s) | Value::Entity(s) => write_str(s, out),
        Value::Json(j) => out.push_str(j),
        Value::List(x) | Value::Tuple(x) => {
            out.push('[');
            for (n, i) in x.iter().enumerate() {
                if n > 0 {
                    out.push_str(", ");
                }
                dumps(i, sort_keys, out);
            }
            out.push(']');
        }
        Value::Map(m) => {
            out.push('{');
            let mut keys: Vec<&String> = m.keys().collect();
            if sort_keys {
                keys.sort();
            }
            for (n, k) in keys.into_iter().enumerate() {
                if n > 0 {
                    out.push_str(", ");
                }
                write_str(k, out);
                out.push_str(": ");
                dumps(&m[k.as_str()], sort_keys, out);
            }
            out.push('}');
        }
    }
}

fn entry(pairs: Vec<(&str, Value)>) -> Value {
    Value::Map(pairs.into_iter().map(|(k, v)| (k.to_string(), v)).collect())
}

impl World {
    /// A new world: its variables evaluated in order, its spawns' books empty, its random seeded.
    pub fn new(def: Arc<WorldDef>, seed: u64) -> Result<World, Raised> {
        let mut spawned = Map::default();
        for i in 0..def.spawns.len() {
            spawned.insert(
                i.to_string(),
                entry(vec![
                    ("alive", Value::List(vec![])),
                    ("due", Value::List(vec![])),
                ]),
            );
        }
        let mut world = World {
            def: def.clone(),
            tick: 0,
            vars: Map::default(),
            entities: Map::default(),
            stored: Map::default(),
            players: IndexMap::default(),
            rng: Rng::seeded(seed),
            rates: IndexMap::default(),
            counters: IndexMap::default(),
            errors: Vec::new(),
            errors_made: 0,
            journal: None,
            dirty: HashSet::default(),
            gone: HashSet::default(),
            events: Vec::new(),
            vars_changed: false,
            cells: HashMap::default(),
            cell_of: HashMap::default(),
            kinds: HashMap::default(),
            kind_of: HashMap::default(),
            events_mark: 0,
            dead: HashMap::default(),
            depth: Arc::new(AtomicUsize::new(0)),
            spawned,
            books: Map::from_iter([
                ("made".to_string(), Value::Map(Map::default())),
                ("spent".to_string(), Value::Map(Map::default())),
            ]),
            parties: Map::default(),
            trades: Map::default(),
            travelers: HashSet::default(),
            expiring: HashSet::default(),
            dying: HashSet::default(),
            walkable_areas: HashMap::default(),
            source: "world".into(),
            asks: Vec::new(),
            asks_mark: 0,
        };
        for (name, code) in def.variables.iter() {
            let value = world
                .evaluate(code, Locals::default())
                .map_err(Raised::of)?;
            let value = world.plain(&value, 0).map_err(|m| Raised::Rule(m, 0))?;
            world.vars.insert(name.clone(), value);
        }
        Ok(world)
    }

    /// A code run with the world as its host: a block's q:return (or null), an expression's value.
    fn evaluate(&mut self, code: &Arc<Code>, mut locals: Locals) -> Result<Value, VmError> {
        let functions = self.def.functions.clone();
        let depth = self.depth.clone();
        let machine = vm::Machine {
            functions: &functions,
            depth: &depth,
        };
        let code = code.clone();
        machine.run(&code, &mut locals, self)
    }

    fn make(
        &mut self,
        spec_name: &str,
        account: Option<&str>,
        name: Option<&str>,
    ) -> Result<Map, VmError> {
        let def = self.def.clone();
        let spec = &def.entities[spec_name];
        let eid = if spec.per_player {
            format!("{}:{}", spec.name, account.unwrap_or(""))
        } else {
            let n = self.counters.get(&spec.name).copied().unwrap_or(0) + 1;
            self.counters.insert(spec.name.clone(), n);
            format!("{}-{n}", spec.name)
        };
        let mut entity = Map::default();
        entity.insert("id".into(), Value::Str(eid));
        entity.insert("kind".into(), Value::Str(spec.kind.clone()));
        entity.insert("at".into(), Value::Null);
        entity.insert("facing".into(), Value::Str("south".into()));
        entity.insert("_type".into(), Value::Str(spec.name.clone()));
        entity.insert(
            "_player".into(),
            account.map_or(Value::Null, |a| Value::Str(a.into())),
        );
        entity.insert("_until".into(), Value::Int(0));
        let account_value = account.map_or(Value::Null, |a| Value::Str(a.into()));
        let shown = match name {
            Some(n) if !n.is_empty() => Value::Str(n.into()),
            _ => account_value.clone(),
        };
        let mut scope = Locals::default();
        scope.insert(
            "account".into(),
            entry(vec![("name", shown), ("id", account_value)]),
        );
        for f in spec.fields.iter() {
            let value = self.evaluate(&f.value, scope.clone())?;
            let value = self.plain(&value, 0).map_err(|m| rule_at(m, 0))?;
            entity.insert(f.name.clone(), value);
        }
        if !spec.states.is_empty() {
            let initial = spec.initial.clone().map_or(Value::Null, Value::Str);
            entity.insert("state".into(), initial);
            entity.insert("_since".into(), Value::Int(self.tick));
        }
        if def.party_size.is_some_and(|s| s != 0) && spec.per_player {
            entity
                .entry("party".into())
                .or_insert(Value::Str(String::new()));
        }
        if def.ledger() && spec.per_player {
            // a hero holds: a bag, and each currency
            entity
                .entry("bag".into())
                .or_insert(Value::Map(Map::default()));
            for (currency, start) in def.currencies.iter() {
                entity.entry(currency.clone()).or_insert(Value::Int(*start));
            }
        }
        Ok(entity)
    }

    /// A rule's run, as a transaction: what fails is undone and kept in the errors.
    fn run_rule(&mut self, code: &Arc<Code>, locals: Locals, place: &str) -> Result<bool, Raised> {
        self.source = place.to_string();
        self.begin();
        match self.evaluate(code, locals) {
            Ok(_) => {
                self.commit();
                Ok(true)
            }
            Err(e) => match Raised::of(e) {
                Raised::Rule(message, line) => {
                    self.rollback();
                    self.error(place, &message, line);
                    Ok(false)
                }
                Raised::Refused(reason) => {
                    self.rollback();
                    self.error(place, &format!("refused: {reason}"), 0);
                    Ok(false)
                }
                python => Err(python),
            },
        }
    }

    fn join(&mut self, account: &str, out: &mut TickOut, name: Option<&str>) -> Result<(), Raised> {
        if self.players.contains_key(account) {
            return Ok(());
        }
        if self.players.len() >= self.def.players {
            out.full.push(account.to_string());
            return Ok(());
        }
        let def = self.def.clone();
        let spec = &def.entities[&def.hero];
        let hero = if spec.persist {
            match self.stored.shift_remove(account) {
                Some(Value::Map(m)) => Some(m),
                _ => None,
            }
        } else {
            None
        };
        let hero = match hero {
            Some(h) => h,
            None => {
                let hero = self
                    .make(&def.hero, Some(account), name)
                    .map_err(Raised::of)?;
                self.mint_start(&hero);
                hero
            }
        };
        let id = vm::py_str(&hero["id"]);
        self.entities.insert(id.clone(), Value::Map(hero));
        self.players.insert(account.to_string(), id.clone());
        self.dirty.insert(id.clone());
        self.gone.remove(&id);
        self.reindex_one(&id);
        out.joined.insert(account.to_string(), id.clone());
        for code in def.on_join.iter() {
            let mut locals = Locals::default();
            locals.insert("me".into(), Value::Entity(id.clone()));
            self.run_rule(code, locals, "q:on-join")?;
        }
        Ok(())
    }

    fn leave(&mut self, account: &str, out: &mut TickOut) -> Result<(), Raised> {
        let Some(id) = self.players.get(account).cloned() else {
            return Ok(());
        };
        let def = self.def.clone();
        for code in def.on_leave.iter() {
            let mut locals = Locals::default();
            locals.insert("me".into(), Value::Entity(id.clone()));
            self.run_rule(code, locals, "q:on-leave")?;
        }
        self.part(&id).map_err(Raised::of)?;
        let hero = self.entities.shift_remove(&id);
        self.players.shift_remove(account);
        if let Some(Value::Map(hero)) = hero {
            self.dead.insert(id.clone(), hero.clone());
            if def.entities[&def.hero].persist {
                self.stored.insert(account.to_string(), Value::Map(hero));
            } else {
                self.spend_all(&hero, "left the world");
            }
        }
        self.gone.insert(id.clone());
        self.dirty.remove(&id);
        self.reindex_one(&id);
        out.left.push(account.to_string());
        Ok(())
    }

    /// A command, as world.py's _command: (it ran, the result the log keeps).
    fn command(
        &mut self,
        account: &str,
        seq: &Value,
        name: &Value,
        args: &Value,
        out: &mut TickOut,
    ) -> Result<(bool, String), Raised> {
        let no = |out: &mut TickOut, reason: String| -> (bool, String) {
            out.refused
                .entry(account.to_string())
                .or_default()
                .push(entry(vec![
                    ("seq", seq.clone()),
                    ("name", name.clone()),
                    ("reason", Value::Str(reason.clone())),
                ]));
            (false, reason)
        };
        let Some(eid) = self.players.get(account).cloned() else {
            return Ok(no(out, "Not in the world.".into()));
        };
        let def = self.def.clone();
        let command = match name {
            Value::Str(n) => def.commands.get(n),
            _ => None,
        };
        let Some(command) = command else {
            return Ok(no(
                out,
                format!("There is no command {}.", vm::py_repr(name)),
            ));
        };
        let name_text = vm::py_str(name);
        if command.by_npc {
            return Ok(no(out, "Only the townsfolk do that: ask them.".into()));
        }
        let fits = match args {
            Value::Map(m) => {
                let given: HashSet<&String> = m.keys().collect();
                let wanted: HashSet<&String> = command.params.iter().collect();
                given == wanted
            }
            _ => false,
        };
        if !fits {
            let wanted = if command.params.is_empty() {
                "nothing".to_string()
            } else {
                command.params.join(", ")
            };
            return Ok(no(out, format!("{name_text} takes {wanted}.")));
        }
        let mut text = String::new();
        dumps(args, false, &mut text);
        if !args_ok(args, 0) || text.chars().count() > MAX_ARGS {
            return Ok(no(
                out,
                format!("{name_text}: an argument is not a plain value."),
            ));
        }
        if let Some((count, window)) = command.limit {
            let key = format!("{account}\u{0}{name_text}");
            let recent: Vec<i64> = self
                .rates
                .get(&key)
                .map(|r| {
                    r.iter()
                        .copied()
                        .filter(|t| *t > self.tick - window)
                        .collect()
                })
                .unwrap_or_default();
            if recent.len() as i64 >= count {
                self.rates.insert(key, recent);
                return Ok(no(out, "Too fast.".into()));
            }
            let mut recent = recent;
            recent.push(self.tick);
            self.rates.insert(key, recent);
        }
        self.source = format!("q:command {name_text}");
        self.begin();
        let ran = match (&command.builtin, &command.body) {
            (Some(builtin), _) => self.builtin(builtin, &eid, args),
            (None, Some(body)) => {
                let mut locals = Locals::default();
                locals.insert("me".into(), Value::Entity(eid));
                if let Value::Map(m) = args {
                    for (k, v) in m {
                        locals.insert(k.clone(), v.clone());
                    }
                }
                self.evaluate(body, locals).map(|_| ())
            }
            (None, None) => Err(rule_at(format!("the command {name_text} has no body"), 0)),
        };
        match ran {
            Ok(_) => {
                self.commit();
                out.acks
                    .entry(account.to_string())
                    .or_default()
                    .push(seq.clone());
                Ok((true, "ok".into()))
            }
            Err(e) => match Raised::of(e) {
                Raised::Refused(reason) => {
                    self.rollback();
                    Ok(no(out, reason))
                }
                Raised::Rule(message, line) => {
                    self.rollback();
                    self.error(&format!("q:command {name_text}"), &message, line);
                    Ok(no(out, "The world could not run it.".into()))
                }
                python => Err(python),
            },
        }
    }

    /// One tick: the inputs in the order they came (join, leave, cmd), then the rules due.
    pub fn step(&mut self, inputs: &[Value]) -> Result<TickOut, Raised> {
        self.tick += 1;
        let mut out = TickOut {
            tick: self.tick,
            ..Default::default()
        };
        self.dirty.clear();
        self.gone.clear();
        self.events.clear();
        self.vars_changed = false;
        self.dead.clear();
        self.asks.clear();
        for item in inputs {
            let item = match item {
                Value::List(x) | Value::Tuple(x) => x,
                _ => continue,
            };
            let kind = vm::py_str(&item[0]);
            let account = vm::py_str(&item[1]);
            match kind.as_str() {
                "join" => {
                    // world.py: item[2] if it is not the account, else None; a name that is empty shows nothing
                    let name = match item.get(2) {
                        Some(Value::Str(n)) if *n != account => Some(n.clone()),
                        _ => None,
                    };
                    self.join(&account, &mut out, name.as_deref())?;
                    let mut e = vec![
                        ("t", Value::Int(self.tick)),
                        ("k", Value::Str("join".into())),
                        ("a", Value::Str(account.clone())),
                    ];
                    if let Some(n) = name.filter(|n| !n.is_empty()) {
                        e.push(("n", Value::Str(n)));
                    }
                    out.entries.push(entry(e));
                }
                "leave" => {
                    self.leave(&account, &mut out)?;
                    out.entries.push(entry(vec![
                        ("t", Value::Int(self.tick)),
                        ("k", Value::Str("leave".into())),
                        ("a", Value::Str(account.clone())),
                    ]));
                }
                "cmd" => {
                    let (seq, name, args) = (&item[2], &item[3], &item[4]);
                    let (ok, result) = self.command(&account, seq, name, args, &mut out)?;
                    out.entries.push(entry(vec![
                        ("t", Value::Int(self.tick)),
                        ("k", Value::Str("cmd".into())),
                        ("a", Value::Str(account.clone())),
                        ("s", seq.clone()),
                        ("n", name.clone()),
                        ("x", args.clone()),
                        ("r", Value::Str(if ok { "ok".into() } else { result })),
                    ]));
                }
                "npc" => {
                    // an NPC's answer, come back from its mind (npc.py)
                    let npc = item.get(2).cloned().unwrap_or(Value::Null);
                    let answer = item.get(3).cloned().unwrap_or(Value::Null);
                    let (npc, answer) = (&npc, &answer);
                    self.answer(&account, npc, answer)?;
                    out.entries.push(entry(vec![
                        ("t", Value::Int(self.tick)),
                        ("k", Value::Str("npc".into())),
                        ("a", Value::Str(account.clone())),
                        ("n", npc.clone()),
                        ("x", answer.clone()),
                    ]));
                }
                _ => {}
            }
        }
        self.live()?;
        let def = self.def.clone();
        for (ticks, code) in def.every.iter() {
            if *ticks != 0 && self.tick.rem_euclid(*ticks) == 0 {
                self.run_rule(code, Locals::default(), "q:every")?;
            }
        }
        let changed: Vec<String> = self.dirty.union(&self.gone).cloned().collect();
        self.reindex(changed.iter());
        Ok(out)
    }

    // -- a hand from outside the tick (a test's, a tool's) -----------------------------------------------------------

    /// Fields of an entity set as they are given, outside any rule: what a test's hand does to world.py's dicts.
    pub fn hand_write(&mut self, id: &str, fields: &Map) -> Result<(), String> {
        let Some(Value::Map(entity)) = self.entities.get_mut(id) else {
            return Err(format!("no entity {id}"));
        };
        for (k, v) in fields {
            entity.insert(k.clone(), v.clone());
        }
        self.dirty.insert(id.to_string());
        self.reindex_one(id);
        Ok(())
    }

    /// world.py's give, called from outside a rule: booked where the world is said to be.
    pub fn hand_give(
        &mut self,
        id: &str,
        item: &Value,
        count: &Value,
        amount: &Value,
        currency: &Value,
        source: &str,
    ) -> Result<(), Raised> {
        self.source = source.to_string();
        self.give(id, item, count, amount, currency, 0)
            .map_err(Raised::of)
    }

    // -- kept, and brought back ------------------------------------------------------------------------------------

    pub fn snapshot(&self) -> Value {
        let (words, index) = self.rng.state();
        let mut state: Vec<Value> = words.into_iter().map(|w| Value::Int(w as i64)).collect();
        state.push(Value::Int(index as i64));
        let rates: Map = self
            .rates
            .iter()
            .map(|(k, v)| {
                (
                    k.clone(),
                    Value::List(v.iter().map(|t| Value::Int(*t)).collect()),
                )
            })
            .collect();
        let counters: Map = self
            .counters
            .iter()
            .map(|(k, v)| (k.clone(), Value::Int(*v)))
            .collect();
        let players: Map = self
            .players
            .iter()
            .map(|(k, v)| (k.clone(), Value::Str(v.clone())))
            .collect();
        entry(vec![
            ("world", Value::Str(self.def.name.clone())),
            ("tick", Value::Int(self.tick)),
            ("vars", Value::Map(self.vars.clone())),
            ("entities", Value::Map(self.entities.clone())),
            ("stored", Value::Map(self.stored.clone())),
            ("players", Value::Map(players)),
            ("rates", Value::Map(rates)),
            ("counters", Value::Map(counters)),
            ("spawned", Value::Map(self.spawned.clone())),
            ("books", Value::Map(self.books.clone())),
            ("parties", Value::Map(self.parties.clone())),
            ("trades", Value::Map(self.trades.clone())),
            (
                "rng",
                Value::List(vec![Value::Int(3), Value::List(state), Value::Null]),
            ),
        ])
    }

    /// world.py's digest: sha256 of the snapshot as json.dumps(sort_keys=True) writes it.
    pub fn digest(&self) -> String {
        let mut text = String::new();
        dumps(&self.snapshot(), true, &mut text);
        let hash = Sha256::digest(text.as_bytes());
        hash.iter().map(|b| format!("{b:02x}")).collect()
    }

    pub fn from_snapshot(def: Arc<WorldDef>, snap: &Value) -> Result<World, String> {
        let mut world = World::new(def, 0).map_err(|e| format!("{e:?}"))?;
        let s = map_of(snap)?;
        world.tick = int_of(key(s, "tick")?)?;
        world.vars = map_of(key(s, "vars")?)?.clone();
        world.entities = map_of(key(s, "entities")?)?.clone();
        world.stored = map_of(key(s, "stored")?)?.clone();
        world.players = map_of(key(s, "players")?)?
            .iter()
            .map(|(k, v)| (k.clone(), vm::py_str(v)))
            .collect();
        world.rates = map_of(key(s, "rates")?)?
            .iter()
            .map(|(k, v)| {
                Ok((
                    k.clone(),
                    list_of(v)?.iter().map(int_of).collect::<Result<_, _>>()?,
                ))
            })
            .collect::<Result<_, String>>()?;
        world.counters = map_of(key(s, "counters")?)?
            .iter()
            .map(|(k, v)| Ok((k.clone(), int_of(v)?)))
            .collect::<Result<_, String>>()?;
        let rng = list_of(key(s, "rng")?)?;
        let state: Vec<i64> = list_of(&rng[1])?
            .iter()
            .map(int_of)
            .collect::<Result<_, _>>()?;
        let words: Vec<u32> = state[..state.len() - 1].iter().map(|w| *w as u32).collect();
        world.rng = Rng::from_state(&words, state[state.len() - 1] as usize)
            .ok_or("a random's state is not one")?;
        for (k, slot) in [("spawned", 0), ("books", 1), ("parties", 2), ("trades", 3)] {
            if let Some(v) = s.get(k) {
                let m = map_of(v)?.clone();
                match slot {
                    0 => world.spawned = m,
                    1 => world.books = m,
                    2 => world.parties = m,
                    _ => world.trades = m,
                }
            }
        }
        let ids: Vec<String> = world.entities.keys().cloned().collect();
        for id in &ids {
            if world.field_of(id, "_expires").is_some() {
                world.expiring.insert(id.clone());
            }
            if world.field_of(id, "_path").is_some_and(vm::truthy) {
                world.travelers.insert(id.clone());
            }
        }
        world.reindex(ids.iter());
        Ok(world)
    }
}
