//! What each player is told of a tick (frames.py, the reference): their welcome, their acks and refusals, what
//! changed in each of their views, their events. The engine keeps its own copy of what players can see (each entity
//! as the others see it, and as its own player does), its own index of cells, and what each seat was told; after
//! a tick it is handed what changed, and it works out every seat's frames in parallel, a seat per task.
//!
//! It holds to frames.py on every point a player can see, and the conformance harness (conform.py) holds it to it:
//! the same members, the same fields that changed, the same order, the same JSON.

use std::collections::{HashMap, HashSet};

use rayon::prelude::*;

use crate::value::{changed, write_json, write_map, write_str, Map, Value};

pub const CELL: i64 = 16;

pub type Tile = (i64, i64);

/// A q:view as the engine reads it.
#[derive(Clone, Debug)]
pub struct ViewSpec {
    pub name: String,
    /// n of a `near(it, me, n)`: read from the index.
    pub radius: Option<i64>,
    /// Its where= is more than the near() (or there is no near()): Python works out its members (until E2's
    /// bytecode), the engine what changed in them.
    pub by_python: bool,
}

#[derive(Clone, Debug, Default)]
pub struct Spec {
    pub views: Vec<ViewSpec>,
    /// Each kind of entity's private fields: its own player sees them, no one else.
    pub private: HashMap<String, HashSet<String>>,
    /// How far an event at a tile is heard (the views' widest); None: by everyone.
    pub reach: Option<i64>,
    /// A welcome's fields after its tick, as JSON: `"rate":10,"world":...,"views":[...]`.
    pub welcome_rest: String,
}

/// An entity as the world has it after the tick: its kind, its player, and its fields but the world's own (_...).
#[derive(Clone, Debug)]
pub struct EntityIn {
    pub id: String,
    pub typ: String,
    pub owner: Option<String>,
    pub fields: Map,
}

#[derive(Clone, Debug)]
pub struct EventIn {
    pub message: Value,
    pub tile: Option<Tile>,
    pub to: Option<String>,
    pub everyone: bool,
    pub accounts: Option<Vec<String>>,
}

/// What a tick hands the engine.
#[derive(Debug, Default)]
pub struct TickIn {
    pub tick: i64,
    /// The entities changed this tick (world.dirty): as they are now, or None when they are no longer.
    pub dirty: Vec<(String, Option<EntityIn>)>,
    pub gone: Vec<String>,
    /// The world's players: account, its entity's id.
    pub players: HashMap<String, String>,
    pub joined: HashSet<String>,
    pub welcoming: HashSet<String>,
    pub acks: HashMap<String, Value>,
    pub refused: HashMap<String, Value>,
    pub events: Vec<EventIn>,
    /// The members Python worked out of its views (by_python), by account, a list per view (None for the others).
    pub given: HashMap<String, Vec<Option<HashSet<String>>>>,
    pub every_tick: bool,
}

#[derive(Clone, Debug)]
struct Known {
    owner: Option<String>,
    tile: Option<Tile>,
    public: Map,      // as the others see it
    own: Option<Map>, // as its own player does
    // and as JSON, written once for all who see it come in
    public_json: String,
    own_json: Option<String>,
}

/// What a player has been told: whether they were welcomed, and what they have of each view.
#[derive(Clone, Debug, Default)]
pub struct Seat {
    pub joined: bool,
    views: Vec<Option<HashSet<String>>>,
}

pub struct Frames {
    pub spec: Spec,
    entities: HashMap<String, Known>,
    cells: HashMap<Tile, HashSet<String>>,
    cell_of: HashMap<String, Tile>,
    /// The seats, by account: the players this engine tells.
    pub seats: HashMap<String, Seat>,
}

/// frames.py's tile_of of an entity: its `at` when that is a record of numbers x and y (truncated, as int() does).
fn tile_of(fields: &Map) -> Option<Tile> {
    let at = fields.get("at")?;
    Some((at.get("x")?.as_whole()?, at.get("y")?.as_whole()?))
}

fn cell_of_tile(tile: Tile) -> Tile {
    (tile.0.div_euclid(CELL), tile.1.div_euclid(CELL))
}

fn chebyshev(a: Tile, b: Tile) -> i64 {
    (a.0 - b.0).abs().max((a.1 - b.1).abs())
}

/// The cells that a square of n tiles around the tile touches (world.py's cells_near).
fn cells_near(tile: Tile, n: i64) -> impl Iterator<Item = Tile> {
    let (x0, x1) = ((tile.0 - n).div_euclid(CELL), (tile.0 + n).div_euclid(CELL));
    let (y0, y1) = ((tile.1 - n).div_euclid(CELL), (tile.1 + n).div_euclid(CELL));
    (x0..=x1).flat_map(move |cx| (y0..=y1).map(move |cy| (cx, cy)))
}

/// A seat's messages of a tick, as JSON texts, in order.
pub type Said = Vec<String>;

struct TickView<'a> {
    tick: &'a TickIn,
    dirty: HashSet<&'a str>,
    gone: HashSet<&'a str>,
    dirty_cells: HashMap<Tile, Vec<&'a str>>,
    theirs: HashMap<&'a str, String>, // the update of an entity to the others, as JSON
    mine: HashMap<&'a str, String>,   // and to its own player
    events: HashMap<&'a str, Vec<usize>>,
}

impl Frames {
    pub fn new(spec: Spec) -> Self {
        Frames {
            spec,
            entities: HashMap::new(),
            cells: HashMap::new(),
            cell_of: HashMap::new(),
            seats: HashMap::new(),
        }
    }

    fn known(&self, entity: &EntityIn) -> Known {
        let own = entity.owner.as_ref().map(|_| entity.fields.clone());
        let public = match (&entity.owner, self.spec.private.get(&entity.typ)) {
            (Some(_), Some(private)) if !private.is_empty() => entity
                .fields
                .iter()
                .filter(|(k, _)| !private.contains(*k))
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
            _ => entity.fields.clone(),
        };
        let public_json = map_json(&public);
        let own_json = own.as_ref().map(map_json);
        Known {
            owner: entity.owner.clone(),
            tile: tile_of(&entity.fields),
            public,
            own,
            public_json,
            own_json,
        }
    }

    fn place(&mut self, eid: &str, tile: Option<Tile>) {
        let cell = tile.map(cell_of_tile);
        let old = self.cell_of.get(eid).copied();
        if old == cell {
            return;
        }
        if let Some(old) = old {
            if let Some(members) = self.cells.get_mut(&old) {
                members.remove(eid);
                if members.is_empty() {
                    self.cells.remove(&old);
                }
            }
            self.cell_of.remove(eid);
        }
        if let Some(cell) = cell {
            self.cells.entry(cell).or_default().insert(eid.to_string());
            self.cell_of.insert(eid.to_string(), cell);
        }
    }

    /// The world as it is, whole: at the start, or from a snapshot.
    pub fn reset(&mut self, entities: Vec<EntityIn>) {
        self.entities.clear();
        self.cells.clear();
        self.cell_of.clear();
        for entity in entities {
            let known = self.known(&entity);
            let tile = known.tile;
            self.entities.insert(entity.id.clone(), known);
            self.place(&entity.id, tile);
        }
    }

    pub fn seat(&mut self, account: &str) {
        self.seats.insert(account.to_string(), Seat::default());
    }

    pub fn unseat(&mut self, account: &str) {
        self.seats.remove(account);
    }

    /// The tick's messages of each seat (only those with something to say).
    pub fn tick(&mut self, tick: &TickIn) -> Vec<(String, Said)> {
        // what changed of each entity, once for every seat; the store and the index follow
        let mut theirs = HashMap::new();
        let mut mine = HashMap::new();
        let mut dirty = HashSet::new();
        for (eid, entity) in &tick.dirty {
            dirty.insert(eid.as_str());
            match entity {
                Some(entity) => {
                    let now = self.known(entity);
                    if let Some(before) = self.entities.get(eid) {
                        let diff = changed(&before.public, &now.public);
                        if !diff.is_empty() {
                            theirs.insert(eid.as_str(), update_json(eid, &diff));
                        }
                        if let (Some(b), Some(n)) = (&before.own, &now.own) {
                            let diff = changed(b, n);
                            if !diff.is_empty() {
                                mine.insert(eid.as_str(), update_json(eid, &diff));
                            }
                        }
                    }
                    let tile = now.tile;
                    self.entities.insert(eid.clone(), now);
                    self.place(eid, tile);
                }
                None => {
                    self.entities.remove(eid);
                    self.place(eid, None);
                }
            }
        }
        let mut gone = HashSet::new();
        for eid in &tick.gone {
            gone.insert(eid.as_str());
            self.entities.remove(eid);
            self.place(eid, None);
        }
        let mut dirty_cells: HashMap<Tile, Vec<&str>> = HashMap::new();
        for eid in &dirty {
            if let Some(cell) = self.cell_of.get(*eid) {
                dirty_cells.entry(*cell).or_default().push(eid);
            }
        }
        let events = self.events(tick);
        let at = TickView {
            tick,
            dirty,
            gone,
            dirty_cells,
            theirs,
            mine,
            events,
        };
        let mut seats = std::mem::take(&mut self.seats);
        let this = &*self;
        let messages: Vec<(String, Said)> = seats
            .par_iter_mut()
            .filter_map(|(account, seat)| {
                let said = this.said(&at, account, seat);
                (!said.is_empty()).then(|| (account.clone(), said))
            })
            .collect();
        self.seats = seats;
        messages
    }

    /// frames.py's _events: theirs (to=), everyone's, and those where they see (at=); by account, the events'
    /// indexes in order.
    fn events<'a>(&self, tick: &'a TickIn) -> HashMap<&'a str, Vec<usize>> {
        let mut out: HashMap<&'a str, Vec<usize>> = HashMap::new();
        if tick.events.is_empty() {
            return out;
        }
        let accounts: Vec<&'a str> = tick
            .players
            .keys()
            .filter(|a| self.seats.get(a.as_str()).is_some_and(|s| s.joined))
            .map(|a| a.as_str())
            .collect();
        let seated = |a: &str| self.seats.contains_key(a);
        for (n, event) in tick.events.iter().enumerate() {
            let to: Vec<&'a str> = if let Some(list) = &event.accounts {
                list.iter()
                    .filter(|a| seated(a))
                    .map(|a| a.as_str())
                    .collect()
            } else if let Some(account) = &event.to {
                if seated(account) {
                    vec![account.as_str()]
                } else {
                    vec![]
                }
            } else if event.everyone || (event.tile.is_some() && self.spec.reach.is_none()) {
                accounts.clone()
            } else if let (Some(tile), Some(reach)) = (event.tile, self.spec.reach) {
                let mut to = vec![];
                for cell in cells_near(tile, reach) {
                    for eid in self.cells.get(&cell).into_iter().flatten() {
                        let known = &self.entities[eid];
                        if let Some(owner) = &known.owner {
                            if let Some((account, hero)) = tick.players.get_key_value(owner) {
                                if hero == eid
                                    && seated(owner)
                                    && known.tile.is_some_and(|t| chebyshev(t, tile) <= reach)
                                {
                                    to.push(account.as_str());
                                }
                            }
                        }
                    }
                }
                to
            } else {
                vec![]
            };
            for account in to {
                out.entry(account).or_default().push(n);
            }
        }
        out
    }

    fn said(&self, at: &TickView, account: &str, seat: &mut Seat) -> Said {
        let tick = at.tick;
        let mut said = Said::new();
        let hero = tick.players.get(account);
        if tick.joined.contains(account) || (tick.welcoming.contains(account) && hero.is_some()) {
            seat.joined = true;
            seat.views = vec![None; self.spec.views.len()];
            let mut text = String::from("{\"type\":\"welcome\",\"you\":");
            match hero {
                Some(eid) => write_str(eid, &mut text),
                None => text.push_str("null"),
            }
            text.push_str(&format!(",\"tick\":{},", tick.tick));
            text.push_str(&self.spec.welcome_rest);
            text.push('}');
            said.push(text);
        }
        let (Some(me_id), true) = (hero, seat.joined) else {
            return said;
        };
        if seat.views.len() != self.spec.views.len() {
            seat.views = vec![None; self.spec.views.len()];
        }
        let mut frame = format!("{{\"type\":\"tick\",\"tick\":{}", tick.tick);
        let mut more = false;
        if let Some(acks) = tick.acks.get(account).filter(|a| non_empty(a)) {
            frame.push_str(",\"ack\":");
            write_json(acks, &mut frame);
            more = true;
        }
        if let Some(refused) = tick.refused.get(account).filter(|r| non_empty(r)) {
            frame.push_str(",\"refused\":");
            write_json(refused, &mut frame);
            more = true;
        }
        if let Some(me) = self.entities.get(me_id) {
            let views = self.views(at, account, me_id, me, seat);
            if !views.is_empty() {
                frame.push_str(",\"views\":");
                frame.push_str(&views);
                more = true;
            }
        }
        if let Some(events) = at.events.get(account) {
            frame.push_str(",\"events\":[");
            for (n, index) in events.iter().enumerate() {
                if n > 0 {
                    frame.push(',');
                }
                write_json(&tick.events[*index].message, &mut frame);
            }
            frame.push(']');
            more = true;
        }
        if more || tick.every_tick {
            frame.push('}');
            said.push(frame);
        }
        said
    }

    /// The members of a view that the engine works out (frames.py's view_members, for a view of the index or of
    /// every entity).
    fn members(
        &self,
        at: &TickView,
        view: &ViewSpec,
        me_id: &str,
        me: &Known,
        had: Option<&HashSet<String>>,
    ) -> HashSet<String> {
        let sees = |eid: &str| -> bool {
            match view.radius {
                None => true,
                Some(r) => match (self.entities.get(eid).and_then(|e| e.tile), me.tile) {
                    (Some(a), Some(b)) => chebyshev(a, b) <= r,
                    _ => false,
                },
            }
        };
        let had = match had {
            Some(had) if !at.dirty.contains(me_id) => had,
            _ => {
                return match (view.radius, me.tile) {
                    (None, _) => self.entities.keys().cloned().collect(),
                    (Some(r), Some(tile)) => cells_near(tile, r)
                        .flat_map(|cell| self.cells.get(&cell).into_iter().flatten())
                        .filter(|eid| sees(eid))
                        .cloned()
                        .collect(),
                    (Some(_), None) => HashSet::new(),
                };
            }
        };
        let mut members: HashSet<String> = had
            .iter()
            .filter(|eid| !at.gone.contains(eid.as_str()))
            .cloned()
            .collect();
        let mut candidates: Vec<&str> = Vec::new();
        match view.radius {
            Some(r) => {
                candidates.extend(
                    had.iter()
                        .map(|e| e.as_str())
                        .filter(|e| at.dirty.contains(e)),
                );
                if let Some(tile) = me.tile {
                    for cell in cells_near(tile, r) {
                        if let Some(ids) = at.dirty_cells.get(&cell) {
                            candidates.extend(ids.iter().copied());
                        }
                    }
                }
            }
            None => candidates.extend(at.dirty.iter().copied()),
        }
        for eid in candidates {
            if self.entities.contains_key(eid) && sees(eid) {
                members.insert(eid.to_string());
            } else {
                members.remove(eid);
            }
        }
        members
    }

    /// What of each view changed for the seat, as JSON (empty: nothing): those that came in, the fields that
    /// changed, those that left.
    fn views(
        &self,
        at: &TickView,
        account: &str,
        me_id: &str,
        me: &Known,
        seat: &mut Seat,
    ) -> String {
        let mut out = String::new();
        let given = at.tick.given.get(account);
        for (v, view) in self.spec.views.iter().enumerate() {
            let had = seat.views[v].take();
            let members = if view.by_python {
                given
                    .and_then(|g| g.get(v))
                    .and_then(|m| m.clone())
                    .unwrap_or_default()
            } else {
                self.members(at, view, me_id, me, had.as_ref())
            };
            let empty = HashSet::new();
            let had_set = had.as_ref().unwrap_or(&empty);
            let mut enter: Vec<&String> =
                members.iter().filter(|e| !had_set.contains(*e)).collect();
            let mut update: Vec<&String> = members
                .iter()
                .filter(|e| had_set.contains(*e) && at.dirty.contains(e.as_str()))
                .collect();
            let mut leave: Vec<&String> =
                had_set.iter().filter(|e| !members.contains(*e)).collect();
            let mut frame = String::new();
            if !enter.is_empty() {
                enter.sort();
                frame.push_str("\"enter\":[");
                for (n, eid) in enter.iter().enumerate() {
                    if n > 0 {
                        frame.push(',');
                    }
                    let known = &self.entities[*eid];
                    frame.push_str(match (&known.owner, &known.own_json) {
                        (Some(owner), Some(own)) if owner == account => own,
                        _ => &known.public_json,
                    });
                }
                frame.push(']');
            }
            update.sort();
            let updates: Vec<&String> = update
                .iter()
                .filter_map(|eid| {
                    if eid.as_str() == me_id {
                        at.mine.get(eid.as_str())
                    } else {
                        at.theirs.get(eid.as_str())
                    }
                })
                .collect();
            if !updates.is_empty() {
                if !frame.is_empty() {
                    frame.push(',');
                }
                frame.push_str("\"update\":[");
                for (n, text) in updates.iter().enumerate() {
                    if n > 0 {
                        frame.push(',');
                    }
                    frame.push_str(text);
                }
                frame.push(']');
            }
            if !leave.is_empty() {
                leave.sort();
                if !frame.is_empty() {
                    frame.push(',');
                }
                frame.push_str("\"leave\":[");
                for (n, eid) in leave.iter().enumerate() {
                    if n > 0 {
                        frame.push(',');
                    }
                    write_str(eid, &mut frame);
                }
                frame.push(']');
            }
            if !frame.is_empty() {
                out.push(if out.is_empty() { '{' } else { ',' });
                write_str(&view.name, &mut out);
                out.push_str(":{");
                out.push_str(&frame);
                out.push('}');
            }
            seat.views[v] = Some(members);
        }
        if !out.is_empty() {
            out.push('}');
        }
        out
    }
}

fn map_json(map: &Map) -> String {
    let mut text = String::new();
    write_map(map, &mut text);
    text
}

fn non_empty(value: &Value) -> bool {
    match value {
        Value::List(items) => !items.is_empty(),
        Value::Null => false,
        _ => true,
    }
}

/// `{"id": eid, **changed}`
fn update_json(eid: &str, diff: &[(&String, &Value)]) -> String {
    let mut text = String::from("{\"id\":");
    write_str(eid, &mut text);
    for (k, v) in diff {
        text.push(',');
        write_str(k, &mut text);
        text.push(':');
        write_json(v, &mut text);
    }
    text.push('}');
    text
}

#[cfg(test)]
mod tests {
    use super::*;

    fn hero(id: &str, account: &str, x: i64, y: i64, purse: i64) -> EntityIn {
        let mut fields = Map::new();
        fields.insert("id".into(), Value::Str(id.into()));
        fields.insert("kind".into(), Value::Str("Hero".into()));
        let mut at = Map::new();
        at.insert("x".into(), Value::Int(x));
        at.insert("y".into(), Value::Int(y));
        fields.insert("at".into(), Value::Map(at));
        fields.insert("purse".into(), Value::Int(purse));
        EntityIn {
            id: id.into(),
            typ: "hero".into(),
            owner: Some(account.into()),
            fields,
        }
    }

    fn engine() -> Frames {
        let spec = Spec {
            views: vec![ViewSpec {
                name: "around".into(),
                radius: Some(5),
                by_python: false,
            }],
            private: [(
                "hero".to_string(),
                ["purse".to_string()].into_iter().collect(),
            )]
            .into_iter()
            .collect(),
            reach: Some(5),
            welcome_rest: "\"rate\":10".into(),
        };
        Frames::new(spec)
    }

    #[test]
    fn a_player_comes_in_sees_who_is_near_and_what_changes() {
        let mut f = engine();
        f.seat("ana");
        f.seat("bo");
        let mut tick = TickIn {
            tick: 1,
            ..Default::default()
        };
        tick.dirty = vec![
            ("hero:ana".into(), Some(hero("hero:ana", "ana", 2, 2, 5))),
            ("hero:bo".into(), Some(hero("hero:bo", "bo", 4, 2, 7))),
        ];
        tick.players = [
            ("ana".to_string(), "hero:ana".to_string()),
            ("bo".to_string(), "hero:bo".to_string()),
        ]
        .into_iter()
        .collect();
        tick.joined = ["ana".to_string(), "bo".to_string()].into_iter().collect();
        let said: HashMap<_, _> = f.tick(&tick).into_iter().collect();
        assert_eq!(
            said["ana"][0],
            "{\"type\":\"welcome\",\"you\":\"hero:ana\",\"tick\":1,\"rate\":10}"
        );
        assert_eq!(
            said["ana"][1],
            concat!(
                "{\"type\":\"tick\",\"tick\":1,\"views\":{\"around\":{\"enter\":[",
                "{\"id\":\"hero:ana\",\"kind\":\"Hero\",\"at\":{\"x\":2,\"y\":2},\"purse\":5},",
                "{\"id\":\"hero:bo\",\"kind\":\"Hero\",\"at\":{\"x\":4,\"y\":2}}]}}}"
            )
        );
        // bo walks away, out of ana's sight; ana's purse changes: only she is told
        let mut tick = TickIn {
            tick: 2,
            players: tick.players.clone(),
            ..Default::default()
        };
        tick.dirty = vec![
            ("hero:ana".into(), Some(hero("hero:ana", "ana", 2, 2, 6))),
            ("hero:bo".into(), Some(hero("hero:bo", "bo", 20, 2, 7))),
        ];
        let said: HashMap<_, _> = f.tick(&tick).into_iter().collect();
        assert_eq!(
            said["ana"][0],
            "{\"type\":\"tick\",\"tick\":2,\"views\":{\"around\":{\"update\":[{\"id\":\"hero:ana\",\"purse\":6}],\"leave\":[\"hero:bo\"]}}}"
        );
        assert_eq!(
            said["bo"][0],
            "{\"type\":\"tick\",\"tick\":2,\"views\":{\"around\":{\"update\":[{\"id\":\"hero:bo\",\"at\":{\"x\":20,\"y\":2}}],\"leave\":[\"hero:ana\"]}}}"
        );
    }
}
