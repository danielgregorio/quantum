//! The module for Python: `quantum_world.Engine`, as quantum/runtime/gameserver/native.py uses it.

use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};

use pyo3::exceptions::{PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyFloat, PyInt, PyList, PyString, PyTuple};

use crate::frames::{EntityIn, EventIn, Frames, Spec, TickIn, Tile, ViewSpec};
use crate::net::{Event, Network};
use crate::value::{Map, Value};

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
        let mut map = Map::with_capacity(d.len());
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
    let mut fields = Map::with_capacity(d.len());
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
            t.given.insert(account.extract()?, each);
        }
        let read = began.elapsed().as_secs_f64();
        let mut guard = self.frames.lock().unwrap();
        let frames: &mut Frames = &mut guard;
        let messages = py.detach(|| frames.tick(&t));
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

    /// The last tick's time, in seconds: (reading what changed out of Python, the frames, the sending).
    fn timings(&self) -> (f64, f64, f64) {
        *self.timings.lock().unwrap()
    }

    // -- the network ---------------------------------------------------------------------------------------------

    /// Listens on host:port (0: a free port, which it returns), on its own threads. step: a test world's (its
    /// harness says "step", "sync" and "peek" as fast as it runs).
    #[pyo3(signature = (host, port, step=false, max_message=16384, messages_a_second=60, tick=0))]
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
    ) -> PyResult<u16> {
        let net = py
            .detach(|| Network::listen(host, port, step, max_message, messages_a_second, tick))
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

#[pymodule]
fn quantum_world(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<Engine>()?;
    Ok(())
}
