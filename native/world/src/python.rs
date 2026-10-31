//! The module for Python: `quantum_world.Engine`, as quantum/runtime/gameserver/native.py uses it.

use std::collections::{HashMap, HashSet};
use std::sync::atomic::{AtomicUsize, Ordering::Relaxed};
use std::sync::{Arc, Mutex};

use pyo3::create_exception;
use pyo3::exceptions::{PyException, PyKeyError, PyOverflowError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

use crate::frames::{EntityIn, EventIn, Frames, Spec, TickIn, Tile, ViewSpec};
use crate::net::{Event, Network};
use crate::rng::Rng as Twister;
use crate::value::{Map, Value};
use crate::vm::{
    self, Code, ErrorKind, Function, Functions, Host, Locals, Op, Raise, VmError, OPCODES,
};
use crate::world;

create_exception!(
    quantum_world,
    MachineError,
    PyException,
    "What the machine could not run: (kind, message, line), kind 'undefined', 'expression', 'rule' or \
'refused'."
);

/// A world's value from Python's (what world.py's plain() keeps; a tuple is a list).
fn to_value(obj: &Bound<'_, PyAny>) -> PyResult<Value> {
    if obj.is_none() {
        return Ok(Value::Null);
    }
    if let Ok(s) = obj.cast::<PyString>() {
        return Ok(match s.to_str() {
            Ok(text) => Value::Str(text.to_owned()),
            Err(_) => Value::Json(python_json(obj)?), // a lone surrogate: Python writes it
        });
    }
    if let Ok(d) = obj.cast::<PyDict>() {
        let mut map = Map::with_capacity_and_hasher(d.len(), Default::default());
        for (k, v) in d.iter() {
            let key: String = k
                .extract()
                .map_err(|_| PyTypeError::new_err("a record's keys are texts"))?;
            map.insert(key, to_value(&v)?);
        }
        return Ok(Value::Map(map));
    }
    if let Ok(b) = obj.cast::<PyBool>() {
        return Ok(Value::Bool(b.is_true()));
    }
    if let Ok(i) = obj.cast::<PyInt>() {
        return Ok(match i.extract::<i64>() {
            Ok(v) => Value::Int(v),
            Err(_) => Value::Big(i.str()?.to_str()?.to_owned()),
        });
    }
    if let Ok(f) = obj.cast::<PyFloat>() {
        return Ok(Value::Float(f.value()));
    }
    if let Ok(l) = obj.cast::<PyList>() {
        return l
            .iter()
            .map(|v| to_value(&v))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::List);
    }
    if let Ok(t) = obj.cast::<PyTuple>() {
        return t
            .iter()
            .map(|v| to_value(&v))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::List);
    }
    Err(PyTypeError::new_err(format!(
        "a {} is not a value a world keeps",
        obj.get_type().name()?
    )))
}

fn python_json(obj: &Bound<'_, PyAny>) -> PyResult<String> {
    obj.py()
        .import("json")?
        .call_method1("dumps", (obj,))?
        .extract()
}

/// A world's entity (a dict) as the engine reads it: its kind, its player, its fields but the world's own.
fn entity_in(id: String, d: &Bound<'_, PyDict>) -> PyResult<EntityIn> {
    let typ = match d.get_item("_type")? {
        Some(t) if !t.is_none() => t.extract()?,
        _ => String::new(),
    };
    let owner = match d.get_item("_player")? {
        Some(o) if !o.is_none() => Some(o.extract()?),
        _ => None,
    };
    let mut fields = Map::with_capacity_and_hasher(d.len(), Default::default());
    for (k, v) in d.iter() {
        let k = k
            .cast_into::<PyString>()
            .map_err(|_| PyTypeError::new_err("an entity's keys are texts"))?;
        let key = k.to_str()?;
        if key.starts_with('_') {
            continue;
        }
        fields.insert(key.to_owned(), to_value(&v)?);
    }
    Ok(EntityIn {
        id,
        typ,
        owner,
        fields,
    })
}

/// An entity as frames.rs reads it, from the engine's own world: its kind, its player, its fields but the world's.
fn entity_of_map(id: &str, m: &Map) -> EntityIn {
    let text = |k: &str| match m.get(k) {
        Some(Value::Str(s)) => Some(s.clone()),
        _ => None,
    };
    EntityIn {
        id: id.to_string(),
        typ: text("_type").unwrap_or_default(),
        owner: text("_player"),
        fields: m
            .iter()
            .filter(|(k, _)| !k.starts_with('_'))
            .map(|(k, v)| (k.clone(), v.clone()))
            .collect(),
    }
}

/// The members Python worked out of its views (by_python): {account: a list per view, None for the others}.
fn given_in(given: &Bound<'_, PyDict>) -> PyResult<HashMap<String, Vec<Option<HashSet<String>>>>> {
    let mut out = HashMap::new();
    for (account, views) in given.iter() {
        let mut each = Vec::new();
        for members in views.try_iter()? {
            let members = members?;
            each.push(if members.is_none() {
                None
            } else {
                Some(accounts_in(&members)?)
            });
        }
        out.insert(account.extract()?, each);
    }
    Ok(out)
}

fn tile_in(obj: &Bound<'_, PyAny>) -> PyResult<Option<Tile>> {
    if obj.is_none() {
        return Ok(None);
    }
    let (x, y): (i64, i64) = obj.extract()?;
    Ok(Some((x, y)))
}

fn accounts_in(obj: &Bound<'_, PyAny>) -> PyResult<HashSet<String>> {
    obj.try_iter()?.map(|a| a?.extract()).collect()
}

/// An event as Python hands it: (message, tile or None, to, everyone, accounts).
type EventTuple<'py> = (
    Bound<'py, PyAny>,
    Bound<'py, PyAny>,
    Option<String>,
    bool,
    Option<Vec<String>>,
);

/// (bytes sent in all, {conn: bytes sent}, {conn: the seq of its last command}).
type Counters = (u64, HashMap<u64, u64>, HashMap<u64, i64>);

/// The engine: what each player sees (frames.rs), and, when it listens, the network (net.rs). Frozen: the tick's
/// thread works out the frames while another waits on the network, so nothing is borrowed for long.
#[pyclass(module = "quantum_world", frozen)]
pub struct Engine {
    frames: Mutex<Frames>,
    net: Mutex<Option<Arc<Network>>>,
    /// The last tick's time: reading what changed out of Python (the bridge), the frames, the sending.
    timings: Mutex<(f64, f64, f64)>,
}

#[pymethods]
impl Engine {
    /// views: (name, radius or None, by_python) for each q:view, in order; private: each kind of entity's private
    /// fields; reach: how far an event is heard (None: by all); welcome_rest: a welcome's fields after its tick.
    #[new]
    fn new(
        views: Vec<(String, Option<i64>, bool)>,
        private: HashMap<String, Vec<String>>,
        reach: Option<i64>,
        welcome_rest: String,
    ) -> Self {
        let spec = Spec {
            views: views
                .into_iter()
                .map(|(name, radius, by_python)| ViewSpec {
                    name,
                    radius,
                    by_python,
                })
                .collect(),
            private: private
                .into_iter()
                .map(|(k, v)| (k, v.into_iter().collect()))
                .collect(),
            reach,
            welcome_rest,
        };
        Engine {
            frames: Mutex::new(Frames::new(spec)),
            net: Mutex::new(None),
            timings: Mutex::new((0.0, 0.0, 0.0)),
        }
    }

    /// The world's entities, all of them: at the start, or once it is back from its log.
    fn reset(&self, entities: &Bound<'_, PyAny>) -> PyResult<()> {
        let mut all = Vec::new();
        for entity in entities.try_iter()? {
            let entity = entity?;
            let d = entity.cast::<PyDict>()?;
            let id: String = d
                .get_item("id")?
                .ok_or_else(|| PyValueError::new_err("an entity has an id"))?
                .extract()?;
            all.push(entity_in(id, d)?);
        }
        self.frames.lock().unwrap().reset(all);
        Ok(())
    }

    /// A player to tell, from now on (told nothing yet); on a connection when it listens.
    #[pyo3(signature = (account, conn=None))]
    fn seat(&self, account: &str, conn: Option<u64>) {
        self.frames.lock().unwrap().seat(account);
        if let (Ok(net), Some(conn)) = (self.network(), conn) {
            net.bind(account, conn);
        }
    }

    fn unseat(&self, account: &str) {
        self.frames.lock().unwrap().unseat(account);
        if let Ok(net) = self.network() {
            net.unbind(account);
        }
    }

    fn seated(&self) -> Vec<String> {
        self.frames.lock().unwrap().seats.keys().cloned().collect()
    }

    /// Whether the seat was welcomed (it is told the ticks).
    fn joined(&self, account: &str) -> bool {
        self.frames
            .lock()
            .unwrap()
            .seats
            .get(account)
            .is_some_and(|s| s.joined)
    }

    /// One tick's frames, from what the tick changed. Returns each seat's messages (JSON texts), or, when it
    /// listens and `send` is true, writes them to the seats' connections and returns the bytes it sent.
    #[pyo3(signature = (tick, dirty, gone, players, joined, welcoming, acks, refused, events, given, every_tick=false, send=false))]
    #[allow(clippy::too_many_arguments)]
    fn tick<'py>(
        &self,
        py: Python<'py>,
        tick: i64,
        dirty: &Bound<'py, PyAny>,
        gone: &Bound<'py, PyAny>,
        players: HashMap<String, String>,
        joined: &Bound<'py, PyAny>,
        welcoming: &Bound<'py, PyAny>,
        acks: &Bound<'py, PyDict>,
        refused: &Bound<'py, PyDict>,
        events: &Bound<'py, PyAny>,
        given: &Bound<'py, PyDict>,
        every_tick: bool,
        send: bool,
    ) -> PyResult<Py<PyAny>> {
        let began = std::time::Instant::now();
        let mut t = TickIn {
            tick,
            players,
            every_tick,
            ..Default::default()
        };
        for item in dirty.try_iter()? {
            let item = item?;
            let (eid, entity): (String, Bound<'py, PyAny>) = item.extract()?;
            let entity = if entity.is_none() {
                None
            } else {
                Some(entity_in(eid.clone(), entity.cast::<PyDict>()?)?)
            };
            t.dirty.push((eid, entity));
        }
        t.gone = gone
            .try_iter()?
            .map(|g| g?.extract())
            .collect::<PyResult<_>>()?;
        t.joined = accounts_in(joined)?;
        t.welcoming = accounts_in(welcoming)?;
        for (k, v) in acks.iter() {
            t.acks.insert(k.extract()?, to_value(&v)?);
        }
        for (k, v) in refused.iter() {
            t.refused.insert(k.extract()?, to_value(&v)?);
        }
        for event in events.try_iter()? {
            let event = event?;
            let (message, tile, to, everyone, accounts): EventTuple<'py> = event.extract()?;
            t.events.push(EventIn {
                message: to_value(&message)?,
                tile: tile_in(&tile)?,
                to,
                everyone,
                accounts,
            });
        }
        t.given = given_in(given)?;
        self.finish(py, &t, send, began)
    }

    /// One tick's frames read from the engine's own world (native_world.py's NativeWorld, E3d): what it changed,
    /// its players, its events, and its tick's acks, refusals and joins, with no bridge out of Python. given: the
    /// members Python worked out of its views (by_python), as for tick.
    #[pyo3(signature = (world, welcoming, given, every_tick=false, send=false))]
    fn tick_world<'py>(
        &self,
        py: Python<'py>,
        world: PyRef<'py, PyWorld>,
        welcoming: &Bound<'py, PyAny>,
        given: &Bound<'py, PyDict>,
        every_tick: bool,
        send: bool,
    ) -> PyResult<Py<PyAny>> {
        let began = std::time::Instant::now();
        let w = &world.inner;
        let mut dirty: Vec<&String> = w.dirty.iter().collect();
        dirty.sort();
        let t = TickIn {
            tick: w.tick,
            dirty: dirty
                .into_iter()
                .map(|id| {
                    let entity = match w.entities.get(id) {
                        Some(Value::Map(m)) => Some(entity_of_map(id, m)),
                        _ => None,
                    };
                    (id.clone(), entity)
                })
                .collect(),
            gone: w.gone.iter().cloned().collect(),
            players: w
                .players
                .iter()
                .map(|(k, v)| (k.clone(), v.clone()))
                .collect(),
            joined: world.joined.clone(),
            welcoming: accounts_in(welcoming)?,
            acks: world.acks.clone(),
            refused: world.refused.clone(),
            events: w
                .events
                .iter()
                .map(|e| EventIn {
                    message: Value::Map(e.message.clone()),
                    tile: e.tile,
                    to: e.to.clone(),
                    everyone: e.everyone,
                    accounts: e.accounts.clone(),
                })
                .collect(),
            given: given_in(given)?,
            every_tick,
        };
        self.finish(py, &t, send, began)
    }

    /// The engine's own world's entities, all of them: at the start, or once it is back from its log.
    fn reset_world(&self, world: PyRef<'_, PyWorld>) {
        let all = world
            .inner
            .entities
            .iter()
            .filter_map(|(id, e)| match e {
                Value::Map(m) => Some(entity_of_map(id, m)),
                _ => None,
            })
            .collect();
        self.frames.lock().unwrap().reset(all);
    }

    /// The last tick's time, in seconds: (reading what changed out of Python, the frames, the sending).
    fn timings(&self) -> (f64, f64, f64) {
        *self.timings.lock().unwrap()
    }

    // -- the network ---------------------------------------------------------------------------------------------

    /// Listens on host:port (0: a free port, which it returns), on its own threads. step: a test world's (its
    /// harness says "step", "sync" and "peek" as fast as it runs). ping_every: a connection is pinged so often,
    /// and one that answers nothing for twice that is gone.
    #[pyo3(signature = (host, port, step=false, max_message=16384, messages_a_second=60, tick=0, ping_every=20.0))]
    #[allow(clippy::too_many_arguments)]
    fn listen(
        &self,
        py: Python<'_>,
        host: &str,
        port: u16,
        step: bool,
        max_message: usize,
        messages_a_second: usize,
        tick: i64,
        ping_every: f64,
    ) -> PyResult<u16> {
        let every = std::time::Duration::from_secs_f64(ping_every.max(0.05));
        let net = py
            .detach(|| {
                Network::listen(
                    host,
                    port,
                    step,
                    max_message,
                    messages_a_second,
                    tick,
                    every,
                )
            })
            .map_err(|e| pyo3::exceptions::PyOSError::new_err(e.to_string()))?;
        let port = net.port;
        *self.net.lock().unwrap() = Some(Arc::new(net));
        Ok(port)
    }

    /// What the players said since the last call, in the order it came (waits up to `timeout` seconds for the
    /// first): ("hello", conn, message), ("cmd", conn, seq, name, args), ("other", conn, message), ("closed", conn).
    fn wait<'py>(&self, py: Python<'py>, timeout: f64) -> PyResult<Vec<Bound<'py, PyAny>>> {
        let net = self.network()?;
        let events = py.detach(|| net.wait(std::time::Duration::from_secs_f64(timeout.max(0.0))));
        let json = py.import("json")?;
        let loads = json.getattr("loads")?;
        events
            .into_iter()
            .map(|event| -> PyResult<Bound<'py, PyAny>> {
                Ok(match event {
                    Event::Hello(conn, text) => ("hello", conn, loads.call1((text,))?)
                        .into_pyobject(py)?
                        .into_any(),
                    Event::Other(conn, text) => ("other", conn, loads.call1((text,))?)
                        .into_pyobject(py)?
                        .into_any(),
                    Event::Cmd(conn, seq, name, args) => (
                        "cmd",
                        conn,
                        loads.call1((seq,))?,
                        name,
                        loads.call1((args,))?,
                    )
                        .into_pyobject(py)?
                        .into_any(),
                    Event::Closed(conn) => ("closed", conn).into_pyobject(py)?.into_any(),
                })
            })
            .collect()
    }

    /// The connection is a player's (account) or a test world's control (None): its next messages are read.
    #[pyo3(signature = (conn, account=None))]
    fn accept(&self, conn: u64, account: Option<String>) -> PyResult<()> {
        self.network()?.accept(conn, account);
        Ok(())
    }

    /// A message to a connection, as it is (a JSON text).
    fn send(&self, conn: u64, text: String) -> PyResult<()> {
        self.network()?.send(conn, text);
        Ok(())
    }

    /// The connection told why ({"type": "error"}) and closed.
    fn close(&self, conn: u64, reason: &str) -> PyResult<()> {
        self.network()?.close(conn, reason);
        Ok(())
    }

    /// The world's tick, for the pongs.
    fn set_tick(&self, tick: i64) -> PyResult<()> {
        self.network()?.set_tick(tick);
        Ok(())
    }

    /// (bytes sent in all, {conn: bytes sent}, {conn: the seq of the last command}).
    fn counters(&self) -> PyResult<Counters> {
        Ok(self.network()?.counters())
    }

    fn shutdown(&self, py: Python<'_>) {
        let net = self.net.lock().unwrap().take();
        if let Some(net) = net {
            py.detach(|| net.shutdown());
        }
    }
}

impl Engine {
    fn network(&self) -> PyResult<Arc<Network>> {
        self.net
            .lock()
            .unwrap()
            .clone()
            .ok_or_else(|| PyValueError::new_err("the engine is not listening"))
    }
}

// -- the machine (vm.rs) and the world's random (rng.rs) ------------------------------------------------------------

/// The world's entities as a run of the machine holds them: by id, each the dict it was when the run first met it.
/// One that leaves the world while the run holds it (a rat a q:loop killed) is still that dict, as it is to Python.
#[derive(Clone)]
struct Entities<'py> {
    world: Bound<'py, PyDict>,
    held: Bound<'py, PyDict>,
}

impl<'py> Entities<'py> {
    fn new(world: &Bound<'py, PyDict>) -> Self {
        Entities {
            world: world.clone(),
            held: PyDict::new(world.py()),
        }
    }

    fn get(&self, id: &str) -> PyResult<Option<Bound<'py, PyAny>>> {
        if let Some(d) = self.held.get_item(id)? {
            return Ok(Some(d));
        }
        let live = self.world.get_item(id)?;
        if let Some(d) = &live {
            self.held.set_item(id, d)?;
        }
        Ok(live)
    }

    /// The id of an entity of the world (or one the run holds), the dict itself; None for any other record.
    fn identify(&self, d: &Bound<'py, PyDict>) -> PyResult<Option<String>> {
        let Some(id) = d.get_item("id")? else {
            return Ok(None);
        };
        let Ok(id) = id.cast::<PyString>() else {
            return Ok(None);
        };
        let id = id.to_str()?;
        let known = match self.held.get_item(id)? {
            Some(held) => held.is(d),
            None => self.world.get_item(id)?.is_some_and(|live| live.is(d)),
        };
        if !known {
            return Ok(None);
        }
        self.held.set_item(id, d)?;
        Ok(Some(id.to_owned()))
    }
}

/// A value of a world's, with its entities as the machine holds them: by id.
fn to_world_value(obj: &Bound<'_, PyAny>, entities: &Entities<'_>) -> PyResult<Value> {
    if let Ok(d) = obj.cast::<PyDict>() {
        if let Some(id) = entities.identify(d)? {
            return Ok(Value::Entity(id));
        }
        let mut map = Map::with_capacity_and_hasher(d.len(), Default::default());
        for (k, v) in d.iter() {
            let key: String = k
                .extract()
                .map_err(|_| PyTypeError::new_err("a record's keys are texts"))?;
            map.insert(key, to_world_value(&v, entities)?);
        }
        return Ok(Value::Map(map));
    }
    if let Ok(l) = obj.cast::<PyList>() {
        return l
            .iter()
            .map(|v| to_world_value(&v, entities))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::List);
    }
    if let Ok(t) = obj.cast::<PyTuple>() {
        return t
            .iter()
            .map(|v| to_world_value(&v, entities))
            .collect::<PyResult<Vec<_>>>()
            .map(Value::Tuple);
    }
    to_value(obj)
}

/// A value of the machine's, as Python holds it: an entity is the world's own dict.
fn from_value<'py>(
    py: Python<'py>,
    v: &Value,
    entities: &Entities<'py>,
) -> PyResult<Bound<'py, PyAny>> {
    Ok(match v {
        Value::Null => py.None().into_bound(py),
        Value::Bool(b) => PyBool::new(py, *b).to_owned().into_any(),
        Value::Int(i) => i.into_pyobject(py)?.into_any(),
        Value::Big(d) => py.get_type::<PyInt>().call1((d.as_str(),))?,
        Value::Float(f) => PyFloat::new(py, *f).into_any(),
        Value::Str(s) => PyString::new(py, s).into_any(),
        Value::Json(j) => py.import("json")?.call_method1("loads", (j.as_str(),))?,
        Value::List(x) => {
            let items = x
                .iter()
                .map(|v| from_value(py, v, entities))
                .collect::<PyResult<Vec<_>>>()?;
            PyList::new(py, items)?.into_any()
        }
        Value::Tuple(x) => {
            let items = x
                .iter()
                .map(|v| from_value(py, v, entities))
                .collect::<PyResult<Vec<_>>>()?;
            PyTuple::new(py, items)?.into_any()
        }
        Value::Map(m) => {
            let d = PyDict::new(py);
            for (k, v) in m {
                d.set_item(k, from_value(py, v, entities)?)?;
            }
            d.into_any()
        }
        Value::Entity(id) => match entities.get(id)? {
            Some(e) => e,
            None => py.None().into_bound(py),
        },
    })
}

/// The machine's host, in Python: an object with variable(name), call(name, args, kwargs), write_var(name, value,
/// line), assign_path(name, local, root, value, line), effect(name, args) and, if it has one, scope_names(local)
/// (quantum/runtime/gameserver/machine.py's WorldHost). An entity's fields are read here, from its dict.
struct PyHost<'py> {
    host: Bound<'py, PyAny>,
    entities: Entities<'py>,
    /// What the host raised that is not the world's own error: raised as it was when the run ends with it.
    pending: Option<PyErr>,
}

fn is_a(py: Python<'_>, e: &PyErr, module: &str, class: &str) -> bool {
    py.import(module)
        .and_then(|m| m.getattr(class))
        .map(|cls| e.is_instance(py, &cls))
        .unwrap_or(false)
}

impl<'py> PyHost<'py> {
    fn new(host: &Bound<'py, PyAny>, entities: &Entities<'py>) -> Self {
        PyHost {
            host: host.clone(),
            entities: entities.clone(),
            pending: None,
        }
    }

    /// The host's exception as the machine's error: the Core's (UndefinedError, ExpressionError) and the world's
    /// (RuleError with its line, Refused with its reason) by kind; anything else kept, to raise as it was.
    fn failed(&mut self, e: PyErr) -> VmError {
        let py = self.host.py();
        let message = e.value(py).to_string();
        if is_a(py, &e, "quantum.core.expressions", "UndefinedError") {
            return VmError::new(ErrorKind::Undefined, message);
        }
        if is_a(py, &e, "quantum.core.expressions", "ExpressionError") {
            return VmError::new(ErrorKind::Expression, message);
        }
        let errors = "quantum.runtime.gameserver.errors";
        if is_a(py, &e, errors, "RuleError") {
            let value = e.value(py);
            let line: Option<u32> = value
                .getattr("line")
                .and_then(|l| l.extract())
                .unwrap_or(None);
            return VmError {
                kind: ErrorKind::Rule,
                message: value
                    .getattr("message")
                    .and_then(|m| m.extract())
                    .unwrap_or(message),
                line: Some(line.unwrap_or(0)),
            };
        }
        if is_a(py, &e, errors, "Refused") {
            let reason = e
                .value(py)
                .getattr("reason")
                .and_then(|r| r.extract())
                .unwrap_or(message);
            return VmError::new(ErrorKind::Refused, reason);
        }
        self.pending = Some(e);
        VmError::new(ErrorKind::Host, message)
    }

    fn found(&mut self, answer: PyResult<Bound<'py, PyAny>>) -> Result<Option<Value>, VmError> {
        let answer = answer.map_err(|e| self.failed(e))?;
        let (found, value): (bool, Bound<'py, PyAny>) =
            answer.extract().map_err(|e| self.failed(e))?;
        if !found {
            return Ok(None);
        }
        to_world_value(&value, &self.entities)
            .map(Some)
            .map_err(|e| self.failed(e))
    }

    fn python(&mut self, v: &Value) -> Result<Bound<'py, PyAny>, VmError> {
        from_value(self.host.py(), v, &self.entities).map_err(|e| self.failed(e))
    }

    fn values(&mut self, values: &[Value]) -> Result<Bound<'py, PyList>, VmError> {
        let items = values
            .iter()
            .map(|v| self.python(v))
            .collect::<Result<Vec<_>, _>>()?;
        PyList::new(self.host.py(), items).map_err(|e| self.failed(e))
    }

    /// The machine's error as Python raises it, at the end of a run.
    fn raised(&mut self, e: VmError) -> PyErr {
        match e.kind {
            ErrorKind::Host => match self.pending.take() {
                Some(raised) => raised,
                None => MachineError::new_err(("host", e.message, e.line.unwrap_or(0))),
            },
            ErrorKind::Python(Raise::Type) => PyTypeError::new_err(e.message),
            ErrorKind::Python(Raise::Value) => PyValueError::new_err(e.message),
            ErrorKind::Python(Raise::Overflow) => PyOverflowError::new_err(e.message),
            kind => MachineError::new_err((
                match kind {
                    ErrorKind::Undefined => "undefined",
                    ErrorKind::Rule => "rule",
                    ErrorKind::Refused => "refused",
                    _ => "expression",
                },
                e.message,
                e.line.unwrap_or(0),
            )),
        }
    }
}

impl Host for PyHost<'_> {
    fn variable(&mut self, name: &str) -> Option<Value> {
        let answer = self.host.call_method1("variable", (name,));
        self.found(answer).ok().flatten()
    }

    fn field(&mut self, id: &str, key: &str) -> Result<Option<Value>, VmError> {
        let entity = self.entities.get(id).map_err(|e| self.failed(e))?;
        let Some(entity) = entity else {
            return Ok(None);
        };
        let value = entity.get_item(key);
        match value {
            Ok(v) => to_world_value(&v, &self.entities)
                .map(Some)
                .map_err(|e| self.failed(e)),
            Err(e) if e.is_instance_of::<PyKeyError>(self.host.py()) => Ok(None),
            Err(e) => Err(self.failed(e)),
        }
    }

    fn keys(&mut self, id: &str) -> Result<Vec<String>, VmError> {
        let entity = self.entities.get(id).map_err(|e| self.failed(e))?;
        let Some(entity) = entity else {
            return Ok(Vec::new());
        };
        let keys = entity
            .call_method0("keys")
            .and_then(|k| k.try_iter()?.map(|k| k?.extract()).collect());
        keys.map_err(|e| self.failed(e))
    }

    fn call(
        &mut self,
        name: &str,
        args: Vec<Value>,
        kwargs: Vec<(String, Value)>,
    ) -> Result<Value, VmError> {
        let py = self.host.py();
        let args = self.values(&args)?;
        let kw = PyDict::new(py);
        for (k, v) in &kwargs {
            let v = self.python(v)?;
            kw.set_item(k, v).map_err(|e| self.failed(e))?;
        }
        let result = self.host.call_method1("call", (name, args, kw));
        let result = result.map_err(|e| self.failed(e))?;
        to_world_value(&result, &self.entities).map_err(|e| self.failed(e))
    }

    fn write_var(&mut self, name: &str, value: &Value, line: u32) -> Result<bool, VmError> {
        let value = self.python(value)?;
        let wrote = self.host.call_method1("write_var", (name, value, line));
        let wrote = wrote.map_err(|e| self.failed(e))?;
        wrote.is_truthy().map_err(|e| self.failed(e))
    }

    fn assign_path(
        &mut self,
        name: &str,
        root: Option<Value>,
        value: Value,
        line: u32,
    ) -> Result<Option<Value>, VmError> {
        let py = self.host.py();
        let local = root.is_some();
        let root = match &root {
            Some(r) => self.python(r)?,
            None => py.None().into_bound(py),
        };
        let value = self.python(&value)?;
        let answer = self
            .host
            .call_method1("assign_path", (name, local, root, value, line));
        self.found(answer)
    }

    fn effect(&mut self, name: &str, args: Vec<Value>) -> Result<(), VmError> {
        let args = self.values(&args)?;
        let done = self.host.call_method1("effect", (name, args));
        done.map(|_| ()).map_err(|e| self.failed(e))
    }

    fn names_of(&mut self, v: &Value) -> Result<Vec<String>, VmError> {
        // the Core's own _names_of, over the value as Python has it (dir() is Python's to say)
        let value = self.python(v)?;
        let names = self
            .host
            .py()
            .import("quantum.core.expressions")
            .and_then(|m| m.getattr("_names_of"))
            .and_then(|f| f.call1((value,)))
            .and_then(|n| n.extract::<Vec<String>>());
        names.map_err(|e| self.failed(e))
    }

    fn scope_names(&mut self, locals: &Locals) -> Vec<String> {
        let default = || {
            locals
                .keys()
                .filter(|k| !k.starts_with('_'))
                .cloned()
                .collect()
        };
        if !self.host.hasattr("scope_names").unwrap_or(false) {
            return default();
        }
        let Ok(local) = self.python(&Value::Map(locals.clone())) else {
            return default();
        };
        self.host
            .call_method1("scope_names", (local,))
            .and_then(|n| n.extract())
            .unwrap_or_else(|_| default())
    }
}

/// A code from bytecode.py's Code (ops, consts, names), its jumps and references checked.
fn code_of(
    ops: Vec<(i64, u32, u32)>,
    consts: &Bound<'_, PyAny>,
    names: Vec<String>,
) -> PyResult<Code> {
    let mut instructions = Vec::with_capacity(ops.len());
    for (op, a, b) in ops {
        let op = Op::from_number(op)
            .ok_or_else(|| PyValueError::new_err(format!("there is no instruction {op}")))?;
        instructions.push((op, a, b));
    }
    let consts = consts
        .try_iter()?
        .map(|c| to_value(&c?))
        .collect::<PyResult<Vec<_>>>()?;
    let code = Code {
        ops: instructions,
        consts,
        names,
    };
    code.check().map_err(PyValueError::new_err)?;
    Ok(code)
}

/// A world's expressions and blocks as bytecode, loaded once and run many times (vm.rs), with its q:functions.
#[pyclass(module = "quantum_world", frozen)]
pub struct Machine {
    codes: Mutex<Vec<Arc<Code>>>,
    functions: Mutex<Arc<Functions>>,
    depth: AtomicUsize,
}

impl Machine {
    fn code(&self, code: usize) -> PyResult<Arc<Code>> {
        self.codes
            .lock()
            .unwrap()
            .get(code)
            .cloned()
            .ok_or_else(|| PyValueError::new_err("no such code"))
    }

    /// Runs a code with the block's variables (local), the world's host and its entities (by id, the live dicts).
    /// Nothing is locked while it runs: a block the world runs from inside an effect runs on this machine too.
    fn execute<'py>(
        &self,
        code: usize,
        local: &Bound<'py, PyAny>,
        host: &Bound<'py, PyAny>,
        entities: &Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let code = self.code(code)?;
        let functions = self.functions.lock().unwrap().clone();
        let entities = Entities::new(entities);
        let mut locals = Map::default();
        for item in local.call_method0("items")?.try_iter()? {
            let (k, v): (String, Bound<'py, PyAny>) = item?.extract()?;
            locals.insert(k, to_world_value(&v, &entities)?);
        }
        let mut world = PyHost::new(host, &entities);
        let machine = vm::Machine {
            functions: &functions,
            depth: &self.depth,
        };
        match machine.run(&code, &mut locals, &mut world) {
            Ok(v) => from_value(host.py(), &v, &entities),
            Err(e) => Err(world.raised(e)),
        }
    }
}

#[pymethods]
impl Machine {
    #[new]
    fn new() -> Self {
        Machine {
            codes: Mutex::new(Vec::new()),
            functions: Mutex::new(Arc::new(Functions::default())),
            depth: AtomicUsize::new(0),
        }
    }

    /// A code (bytecode.py's Code: ops, consts, names), an expression's or a block's; its number, to run it by.
    fn load(
        &self,
        ops: Vec<(i64, u32, u32)>,
        consts: &Bound<'_, PyAny>,
        names: Vec<String>,
    ) -> PyResult<usize> {
        let code = code_of(ops, consts, names)?;
        let mut codes = self.codes.lock().unwrap();
        codes.push(Arc::new(code));
        Ok(codes.len() - 1)
    }

    /// A q:function, its body a loaded code: CALL_USER and CALL_STATEMENT run it on the machine.
    fn define(&self, name: String, code: usize, params: Vec<String>, line: u32) -> PyResult<()> {
        let function = Function {
            name: name.clone(),
            code: self.code(code)?,
            params,
            line,
        };
        let mut functions = self.functions.lock().unwrap();
        Arc::make_mut(&mut functions).insert(name, Arc::new(function));
        Ok(())
    }

    /// An expression's value (MachineError (kind, message, line) when it cannot be had).
    fn run<'py>(
        &self,
        code: usize,
        local: &Bound<'py, PyAny>,
        host: &Bound<'py, PyAny>,
        entities: &Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyAny>> {
        self.execute(code, local, host, entities)
    }

    /// A block run: its q:return's value, or None. A q:require that did not hold is MachineError('refused',
    /// reason, 0); a rule that could not run, ('rule' | 'expression' | 'undefined', message, line).
    fn run_block<'py>(
        &self,
        code: usize,
        local: &Bound<'py, PyAny>,
        host: &Bound<'py, PyAny>,
        entities: &Bound<'py, PyDict>,
    ) -> PyResult<Bound<'py, PyAny>> {
        self.execute(code, local, host, entities)
    }

    /// How deep the world's q:function calls are now (rules.py's Interpreter.depth).
    fn depth(&self) -> usize {
        self.depth.load(Relaxed)
    }

    fn set_depth(&self, depth: usize) {
        self.depth.store(depth, Relaxed);
    }
}

impl Engine {
    /// A tick's frames worked out, off Python's lock, and written to the seats' connections when it listens and
    /// `send` is true (the bytes sent), else returned ({account: its messages}).
    fn finish(
        &self,
        py: Python<'_>,
        t: &TickIn,
        send: bool,
        began: std::time::Instant,
    ) -> PyResult<Py<PyAny>> {
        let tick = t.tick;
        let read = began.elapsed().as_secs_f64();
        let mut guard = self.frames.lock().unwrap();
        let frames: &mut Frames = &mut guard;
        let messages = py.detach(|| frames.tick(t));
        drop(guard);
        let made = began.elapsed().as_secs_f64();
        if send {
            if let Ok(net) = self.network() {
                let sent = py.detach(|| net.send_frames(messages, tick));
                *self.timings.lock().unwrap() =
                    (read, made - read, began.elapsed().as_secs_f64() - made);
                return Ok(sent.into_pyobject(py)?.into_any().unbind());
            }
        }
        *self.timings.lock().unwrap() = (read, made - read, 0.0);
        let out = PyDict::new(py);
        for (account, said) in messages {
            out.set_item(account, said)?;
        }
        Ok(out.into_any().unbind())
    }
}

// -- the world (world.rs, E3) ----------------------------------------------------------------------------------------

/// A value of the world's, as Python holds it (it holds no entity by reference: what the world keeps is plain).
fn plain_out<'py>(py: Python<'py>, v: &Value) -> PyResult<Bound<'py, PyAny>> {
    let none = PyDict::new(py);
    from_value(py, v, &Entities::new(&none))
}

/// What the world raises, as world.py raises it.
fn world_raised(py: Python<'_>, e: world::Raised) -> PyErr {
    let class = |name: &str| {
        py.import("quantum.runtime.gameserver.errors")
            .and_then(|m| m.getattr(name))
    };
    let made = match e {
        world::Raised::Rule(message, line) => {
            let line = if line > 0 { Some(line) } else { None };
            class("RuleError").and_then(|c| c.call1((message, line)))
        }
        world::Raised::Refused(reason) => class("Refused").and_then(|c| c.call1((reason,))),
        world::Raised::Python(e) => {
            return match e.kind {
                ErrorKind::Python(Raise::Type) => PyTypeError::new_err(e.message),
                ErrorKind::Python(Raise::Overflow) => PyOverflowError::new_err(e.message),
                _ => PyValueError::new_err(e.message),
            }
        }
    };
    match made {
        Ok(err) => PyErr::from_value(err),
        Err(e) => e,
    }
}

/// A code as bytecode.py's Code hands it: (ops, consts, names).
type CodeParts<'py> = (Vec<(i64, u32, u32)>, Bound<'py, PyAny>, Vec<String>);

fn world_def(
    definition: &Bound<'_, PyAny>,
    codes: &Bound<'_, PyAny>,
) -> PyResult<Arc<world::WorldDef>> {
    let mut loaded = Vec::new();
    for c in codes.try_iter()? {
        let c = c?;
        let (ops, consts, names): CodeParts<'_> = c.extract()?;
        loaded.push(Arc::new(code_of(ops, &consts, names)?));
    }
    let value = to_value(definition)?;
    world::WorldDef::from_value(&value, &loaded)
        .map(Arc::new)
        .map_err(PyValueError::new_err)
}

/// A world whose state and tick are the engine's (world.rs): quantum/runtime/gameserver/native_world.py's
/// NativeWorld keeps what frames.py reads of it in step.
#[pyclass(module = "quantum_world", name = "World")]
pub struct PyWorld {
    inner: world::World,
    /// The last tick's acks, refusals and joins, for the frames (Engine.tick_world).
    acks: HashMap<String, Value>,
    refused: HashMap<String, Value>,
    joined: HashSet<String>,
}

impl PyWorld {
    fn of(inner: world::World) -> Self {
        PyWorld {
            inner,
            acks: HashMap::new(),
            refused: HashMap::new(),
            joined: HashSet::new(),
        }
    }
}

#[pymethods]
impl PyWorld {
    /// definition and codes: native_world.py's export; seed: the world's random's.
    #[new]
    fn new(
        py: Python<'_>,
        definition: &Bound<'_, PyAny>,
        codes: &Bound<'_, PyAny>,
        seed: u64,
    ) -> PyResult<Self> {
        let def = world_def(definition, codes)?;
        let inner = world::World::new(def, seed).map_err(|e| world_raised(py, e))?;
        Ok(PyWorld::of(inner))
    }

    /// A world from its snapshot (world.py's from_snapshot).
    #[staticmethod]
    fn from_snapshot(
        definition: &Bound<'_, PyAny>,
        codes: &Bound<'_, PyAny>,
        snap: &Bound<'_, PyAny>,
    ) -> PyResult<Self> {
        let def = world_def(definition, codes)?;
        let inner =
            world::World::from_snapshot(def, &to_value(snap)?).map_err(PyValueError::new_err)?;
        Ok(PyWorld::of(inner))
    }

    /// One tick (world.py's step): {tick, entries, acks, refused, joined, left, full, asks}.
    fn step<'py>(
        &mut self,
        py: Python<'py>,
        inputs: &Bound<'py, PyAny>,
    ) -> PyResult<Bound<'py, PyAny>> {
        let inputs = inputs
            .try_iter()?
            .map(|i| to_value(&i?))
            .collect::<PyResult<Vec<_>>>()?;
        let out = self.inner.step(&inputs).map_err(|e| world_raised(py, e))?;
        self.acks = out
            .acks
            .iter()
            .map(|(k, v)| (k.clone(), Value::List(v.clone())))
            .collect();
        self.refused = out
            .refused
            .iter()
            .map(|(k, v)| (k.clone(), Value::List(v.clone())))
            .collect();
        self.joined = out.joined.keys().cloned().collect();
        let lists =
            |m: indexmap::IndexMap<String, Vec<Value>, rustc_hash::FxBuildHasher>| -> Value {
                Value::Map(m.into_iter().map(|(k, v)| (k, Value::List(v))).collect())
            };
        let d = PyDict::new(py);
        d.set_item("tick", out.tick)?;
        d.set_item("entries", plain_out(py, &Value::List(out.entries))?)?;
        d.set_item("acks", plain_out(py, &lists(out.acks))?)?;
        d.set_item("refused", plain_out(py, &lists(out.refused))?)?;
        let joined = PyDict::new(py);
        for (k, v) in out.joined {
            joined.set_item(k, v)?;
        }
        d.set_item("joined", joined)?;
        d.set_item("left", out.left)?;
        d.set_item("full", out.full)?;
        d.set_item(
            "asks",
            plain_out(py, &Value::List(self.inner.asks.clone()))?,
        )?;
        Ok(d.into_any())
    }

    fn snapshot<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyAny>> {
        plain_out(py, &self.inner.snapshot())
    }

    fn digest(&self) -> String {
        self.inner.digest()
    }

    /// These entities as they are now, in the world's order ({id: its dict}; None for one not in the world, last).
    fn pull<'py>(&self, py: Python<'py>, ids: Vec<String>) -> PyResult<Bound<'py, PyDict>> {
        let wanted: HashSet<String> = ids.into_iter().collect();
        let d = PyDict::new(py);
        for (id, e) in &self.inner.entities {
            if wanted.contains(id) {
                d.set_item(id, plain_out(py, e)?)?;
            }
        }
        for id in wanted {
            if !self.inner.entities.contains_key(&id) {
                d.set_item(&id, py.None())?;
            }
        }
        Ok(d)
    }

    /// The tick's changes, for the mirror: dirty, gone, players, vars, vars_changed, events, and the errors made since
    /// errors_seen of them were (with how many have been made).
    fn changes<'py>(&self, py: Python<'py>, errors_seen: usize) -> PyResult<Bound<'py, PyTuple>> {
        let w = &self.inner;
        let players = PyDict::new(py);
        for (k, v) in &w.players {
            players.set_item(k, v)?;
        }
        let events = PyList::empty(py);
        for e in &w.events {
            events.append((
                plain_out(py, &Value::Map(e.message.clone()))?,
                e.tile,
                e.to.clone(),
                e.everyone,
                e.accounts.clone(),
            ))?;
        }
        let new = w
            .errors_made
            .saturating_sub(errors_seen)
            .min(w.errors.len());
        let errors = plain_out(
            py,
            &Value::List(
                w.errors[w.errors.len() - new..]
                    .iter()
                    .cloned()
                    .map(Value::Map)
                    .collect(),
            ),
        )?;
        let mut dirty: Vec<&String> = w.dirty.iter().collect();
        dirty.sort();
        let mut gone: Vec<&String> = w.gone.iter().collect();
        gone.sort();
        PyTuple::new(
            py,
            [
                dirty.into_pyobject(py)?.into_any(),
                gone.into_pyobject(py)?.into_any(),
                players.into_any(),
                plain_out(py, &Value::Map(w.vars.clone()))?,
                PyBool::new(py, w.vars_changed).to_owned().into_any(),
                events.into_any(),
                errors,
                w.errors_made.into_pyobject(py)?.into_any(),
            ],
        )
    }

    #[getter]
    fn tick(&self) -> i64 {
        self.inner.tick
    }

    /// A test's hand: fields of an entity set as given (world.py's dicts, written by hand).
    fn hand_write(&mut self, id: &str, fields: &Bound<'_, PyAny>) -> PyResult<()> {
        let Value::Map(fields) = to_value(fields)? else {
            return Err(PyValueError::new_err("fields is a dict"));
        };
        self.inner
            .hand_write(id, &fields)
            .map_err(PyValueError::new_err)
    }

    /// world.py's give, from outside a rule (a test's hand), booked at source.
    #[allow(clippy::too_many_arguments)]
    fn hand_give(
        &mut self,
        py: Python<'_>,
        id: &str,
        item: &Bound<'_, PyAny>,
        count: &Bound<'_, PyAny>,
        amount: &Bound<'_, PyAny>,
        currency: &Bound<'_, PyAny>,
        source: &str,
    ) -> PyResult<()> {
        self.inner
            .hand_give(
                id,
                &to_value(item)?,
                &to_value(count)?,
                &to_value(amount)?,
                &to_value(currency)?,
                source,
            )
            .map_err(|e| world_raised(py, e))
    }

    /// What the world keeps beside its entities, for the mirror: (books, parties, trades), and its stored heroes
    /// when asked for them (they change only as players come and go).
    fn kept<'py>(&self, py: Python<'py>, stored: bool) -> PyResult<Bound<'py, PyTuple>> {
        let w = &self.inner;
        let stored = if stored {
            plain_out(py, &Value::Map(w.stored.clone()))?
        } else {
            py.None().into_bound(py)
        };
        PyTuple::new(
            py,
            [
                plain_out(py, &Value::Map(w.books.clone()))?,
                plain_out(py, &Value::Map(w.parties.clone()))?,
                plain_out(py, &Value::Map(w.trades.clone()))?,
                stored,
            ],
        )
    }
}

/// Python's random.Random, as the engine draws it (rng.rs): for a test to hold the two together.
#[pyclass(module = "quantum_world", name = "Rng")]
pub struct PyRng {
    inner: Twister,
}

#[pymethods]
impl PyRng {
    #[new]
    fn new(seed: u64) -> Self {
        PyRng {
            inner: Twister::seeded(seed),
        }
    }

    /// From Python's getstate()[1]: 624 words and the index.
    #[staticmethod]
    fn from_state(state: Vec<u32>) -> PyResult<Self> {
        let (index, words) = state
            .split_last()
            .ok_or_else(|| PyValueError::new_err("an empty state"))?;
        Twister::from_state(words, *index as usize)
            .map(|inner| PyRng { inner })
            .ok_or_else(|| PyValueError::new_err("a state is 624 words and an index"))
    }

    /// As Python's getstate()[1].
    fn state(&self) -> Vec<u32> {
        let (mut words, index) = self.inner.state();
        words.push(index as u32);
        words
    }

    fn random(&mut self) -> f64 {
        self.inner.random()
    }

    fn randint(&mut self, a: i64, b: i64) -> PyResult<i64> {
        self.inner
            .randint(a, b)
            .ok_or_else(|| PyValueError::new_err(format!("empty range in randint({a}, {b})")))
    }

    fn randrange(&mut self, n: i64) -> PyResult<i64> {
        self.inner
            .randrange(n)
            .ok_or_else(|| PyValueError::new_err(format!("empty range in randrange({n})")))
    }
}

#[pymodule]
fn quantum_world(m: &Bound<'_, PyModule>) -> PyResult<()> {
    vm::SORTS_AS_313.store(m.py().version_info() >= (3, 13), Relaxed);
    m.add_class::<Engine>()?;
    m.add_class::<Machine>()?;
    m.add_class::<PyRng>()?;
    m.add_class::<PyWorld>()?;
    m.add("MachineError", m.py().get_type::<MachineError>())?;
    m.add("OPCODES", OPCODES.to_vec())?;
    Ok(())
}
