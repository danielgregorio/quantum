//! The network (server.py's protocol, on tokio): the WebSockets, each message read and checked (its size, its
//! rate, a command's seq and name), the pongs, and each player's frames written, on a pool of threads, so the
//! tick's thread never waits on a socket. A slow player never holds the tick: what is not sent yet waits in its
//! connection's queue, and a connection that falls too far behind is closed.
//!
//! What is the world's to decide stays Python's (native.py): a hello (who it is, a ticket), "step", "sync",
//! "peek" and anything else; the engine hands them over in the order they came, with the commands, and waits for
//! a hello's answer before it reads that connection's next message, as server.py does.

use std::collections::{HashMap, VecDeque};
use std::net::SocketAddr;
use std::sync::atomic::{AtomicI64, AtomicU64, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use futures_util::{SinkExt, StreamExt};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::{mpsc, oneshot, watch};
use tokio_tungstenite::tungstenite::protocol::WebSocketConfig;
use tokio_tungstenite::tungstenite::Message;

use crate::value::{from_serde, write_json, write_str};

/// A connection's frames waiting to be sent past this, and it is let go.
const MAX_QUEUED: usize = 16 * 1024 * 1024;
const UNLIMITED: [&str; 3] = ["step", "sync", "peek"];

/// What a connection said, for Python, in the order it came.
#[derive(Debug)]
pub enum Event {
    /// a hello: who it is is Python's to say (accept or close)
    Hello(u64, String),
    /// a command: its seq (an integer), its name, its args, as JSON
    Cmd(u64, String, String, String),
    /// step, sync, peek, or anything else
    Other(u64, String),
    Closed(u64),
}

enum Out {
    Text(String),
    Ping,
    Close,
}

/// As websockets' server does: a ping every twenty seconds, and a connection that answers nothing for twenty more
/// is gone (its player leaves the world).
pub const PING_EVERY: Duration = Duration::from_secs(20);

#[derive(Clone, PartialEq)]
enum Role {
    New,
    Player,
    Control,
    Closed,
}

struct Conn {
    out: mpsc::UnboundedSender<Out>,
    role: Role,
    answer: Option<oneshot::Sender<bool>>,
    closing: watch::Sender<bool>,
    queued: Arc<AtomicUsize>,
    sent: u64,
    last_seq: i64,
}

struct Shared {
    conns: Mutex<HashMap<u64, Conn>>,
    seats: Mutex<HashMap<String, u64>>,
    tick: AtomicI64,
    bytes_out: AtomicU64,
    next: AtomicU64,
    events: crossbeam_channel::Sender<Event>,
    step: bool,
    max_message: usize,
    rate: usize,
    ping_every: Duration,
}

pub struct Network {
    pub port: u16,
    runtime: Mutex<Option<tokio::runtime::Runtime>>,
    shared: Arc<Shared>,
    events: crossbeam_channel::Receiver<Event>,
}

impl Shared {
    /// A message to the connection (counted), unless it is closed; one too far behind is closed.
    fn push(&self, conns: &mut HashMap<u64, Conn>, id: u64, text: String) -> u64 {
        let Some(conn) = conns.get_mut(&id) else {
            return 0;
        };
        if conn.role == Role::Closed {
            return 0;
        }
        let n = text.len();
        if conn.queued.load(Ordering::Relaxed) + n > MAX_QUEUED {
            Self::close_conn(
                conn,
                "The connection is too slow: what the world says could not be sent.",
            );
            return 0;
        }
        conn.queued.fetch_add(n, Ordering::Relaxed);
        conn.sent += n as u64;
        self.bytes_out.fetch_add(n as u64, Ordering::Relaxed);
        let _ = conn.out.send(Out::Text(text));
        n as u64
    }

    fn close_conn(conn: &mut Conn, reason: &str) {
        if conn.role == Role::Closed {
            return;
        }
        let mut text = String::from("{\"type\":\"error\",\"reason\":");
        write_str(reason, &mut text);
        text.push('}');
        conn.sent += text.len() as u64;
        let _ = conn.out.send(Out::Text(text));
        let _ = conn.out.send(Out::Close);
        conn.role = Role::Closed;
        if let Some(answer) = conn.answer.take() {
            let _ = answer.send(false);
        }
        let _ = conn.closing.send(true);
    }

    fn close(&self, id: u64, reason: &str) {
        let mut conns = self.conns.lock().unwrap();
        if let Some(conn) = conns.get_mut(&id) {
            let len = conn.sent;
            Self::close_conn(conn, reason);
            self.bytes_out.fetch_add(conn.sent - len, Ordering::Relaxed);
        }
    }
}

impl Network {
    pub fn listen(
        host: &str,
        port: u16,
        step: bool,
        max_message: usize,
        rate: usize,
        tick: i64,
        ping_every: Duration,
    ) -> std::io::Result<Network> {
        let runtime = tokio::runtime::Builder::new_multi_thread()
            .thread_name("world-net")
            .enable_all()
            .build()?;
        let (tx, rx) = crossbeam_channel::unbounded();
        let shared = Arc::new(Shared {
            conns: Mutex::new(HashMap::new()),
            seats: Mutex::new(HashMap::new()),
            tick: AtomicI64::new(tick),
            bytes_out: AtomicU64::new(0),
            next: AtomicU64::new(1),
            events: tx,
            step,
            max_message,
            rate,
            ping_every,
        });
        let listener = runtime.block_on(TcpListener::bind((host, port)))?;
        let port = listener.local_addr()?.port();
        let accepting = shared.clone();
        runtime.spawn(async move {
            loop {
                match listener.accept().await {
                    Ok((stream, peer)) => {
                        let _ = stream.set_nodelay(true);
                        tokio::spawn(serve(accepting.clone(), stream, peer));
                    }
                    Err(_) => tokio::time::sleep(Duration::from_millis(50)).await, // too many open files: a breath
                }
            }
        });
        Ok(Network {
            port,
            runtime: Mutex::new(Some(runtime)),
            shared,
            events: rx,
        })
    }

    /// What came since the last call, waiting up to `timeout` for the first.
    pub fn wait(&self, timeout: Duration) -> Vec<Event> {
        let mut out = Vec::new();
        if let Ok(first) = self.events.recv_timeout(timeout) {
            out.push(first);
            while let Ok(next) = self.events.try_recv() {
                out.push(next);
                if out.len() >= 4096 {
                    break;
                }
            }
        }
        out
    }

    pub fn accept(&self, id: u64, account: Option<String>) {
        let mut conns = self.shared.conns.lock().unwrap();
        if let Some(conn) = conns.get_mut(&id) {
            if conn.role == Role::Closed {
                return;
            }
            conn.role = if account.is_some() {
                Role::Player
            } else {
                Role::Control
            };
            if let Some(answer) = conn.answer.take() {
                let _ = answer.send(true);
            }
        }
    }

    pub fn send(&self, id: u64, text: String) {
        let mut conns = self.shared.conns.lock().unwrap();
        self.shared.push(&mut conns, id, text);
    }

    pub fn close(&self, id: u64, reason: &str) {
        self.shared.close(id, reason);
    }

    pub fn bind(&self, account: &str, id: u64) {
        self.shared
            .seats
            .lock()
            .unwrap()
            .insert(account.to_string(), id);
    }

    pub fn unbind(&self, account: &str) {
        self.shared.seats.lock().unwrap().remove(account);
    }

    pub fn set_tick(&self, tick: i64) {
        self.shared.tick.store(tick, Ordering::Relaxed);
    }

    /// Each seat's messages to its connection; the bytes sent.
    pub fn send_frames(&self, messages: Vec<(String, Vec<String>)>, tick: i64) -> u64 {
        self.shared.tick.store(tick, Ordering::Relaxed);
        let seats = self.shared.seats.lock().unwrap();
        let mut conns = self.shared.conns.lock().unwrap();
        let mut sent = 0;
        for (account, said) in messages {
            if let Some(id) = seats.get(&account) {
                for text in said {
                    sent += self.shared.push(&mut conns, *id, text);
                }
            }
        }
        sent
    }

    pub fn counters(&self) -> (u64, HashMap<u64, u64>, HashMap<u64, i64>) {
        let conns = self.shared.conns.lock().unwrap();
        (
            self.shared.bytes_out.load(Ordering::Relaxed),
            conns.iter().map(|(id, c)| (*id, c.sent)).collect(),
            conns.iter().map(|(id, c)| (*id, c.last_seq)).collect(),
        )
    }

    pub fn shutdown(&self) {
        {
            let mut conns = self.shared.conns.lock().unwrap();
            for conn in conns.values_mut() {
                let _ = conn.out.send(Out::Close);
                let _ = conn.closing.send(true);
            }
        }
        let runtime = self.runtime.lock().unwrap().take();
        if let Some(runtime) = runtime {
            runtime.shutdown_timeout(Duration::from_secs(2));
        }
    }
}

impl Drop for Network {
    fn drop(&mut self) {
        if let Some(runtime) = self.runtime.get_mut().unwrap().take() {
            runtime.shutdown_background();
        }
    }
}

/// A seq is an integer (a bool is one, to Python).
fn integer(value: &serde_json::Value) -> Option<i64> {
    match value {
        serde_json::Value::Number(n) => n.as_i64().or_else(|| n.as_u64().map(|u| u as i64)),
        serde_json::Value::Bool(b) => Some(*b as i64),
        _ => None,
    }
}

async fn serve(shared: Arc<Shared>, stream: TcpStream, _peer: SocketAddr) {
    let config = WebSocketConfig::default()
        .max_message_size(Some(shared.max_message))
        .max_frame_size(Some(shared.max_message));
    let Ok(ws) = tokio_tungstenite::accept_async_with_config(stream, Some(config)).await else {
        return;
    };
    let (mut sink, mut source) = ws.split();
    let (tx, mut rx) = mpsc::unbounded_channel::<Out>();
    let (closing_tx, mut closing) = watch::channel(false);
    let queued = Arc::new(AtomicUsize::new(0));
    let id = shared.next.fetch_add(1, Ordering::Relaxed);
    shared.conns.lock().unwrap().insert(
        id,
        Conn {
            out: tx,
            role: Role::New,
            answer: None,
            closing: closing_tx,
            queued: queued.clone(),
            sent: 0,
            last_seq: 0,
        },
    );
    let writer = tokio::spawn(async move {
        while let Some(out) = rx.recv().await {
            match out {
                Out::Text(text) => {
                    let n = text.len();
                    let failed = sink.send(Message::text(text)).await.is_err();
                    queued.fetch_sub(n, Ordering::Relaxed);
                    if failed {
                        break;
                    }
                }
                Out::Ping => {
                    if sink.send(Message::Ping(Vec::new().into())).await.is_err() {
                        break;
                    }
                }
                Out::Close => {
                    let _ = sink.close().await;
                    break;
                }
            }
        }
    });
    let mut window: VecDeque<Instant> = VecDeque::new();
    let say = |text: String| {
        let mut conns = shared.conns.lock().unwrap();
        shared.push(&mut conns, id, text);
    };
    let close = |reason: &str| shared.close(id, reason);
    let every = shared.ping_every;
    let mut pings = tokio::time::interval_at(tokio::time::Instant::now() + every, every);
    let mut heard = Instant::now();
    loop {
        let message = tokio::select! {
            m = source.next() => m,
            _ = closing.changed() => break,
            _ = pings.tick() => {
                if heard.elapsed() > 2 * every {
                    break; // no answer to the last ping: the other side is gone
                }
                if let Some(conn) = shared.conns.lock().unwrap().get(&id) {
                    let _ = conn.out.send(Out::Ping);
                }
                continue;
            }
        };
        heard = Instant::now();
        let text = match message {
            Some(Ok(Message::Text(t))) => t.to_string(),
            Some(Ok(Message::Binary(b))) => match String::from_utf8(b.to_vec()) {
                Ok(t) => t,
                Err(_) => {
                    close("A message is a JSON object with a type.");
                    break;
                }
            },
            Some(Ok(Message::Close(_))) | None | Some(Err(_)) => break,
            Some(Ok(_)) => continue, // pings and pongs: tungstenite answers them
        };
        let role = match shared.conns.lock().unwrap().get(&id) {
            Some(c) => c.role.clone(),
            None => break,
        };
        if role == Role::Closed {
            break;
        }
        let parsed: Option<serde_json::Map<String, serde_json::Value>> =
            match serde_json::from_str(&text) {
                Ok(serde_json::Value::Object(map)) => Some(map),
                _ => None,
            };
        let Some(message) = parsed.filter(|m| m.get("type").is_some_and(|t| !t.is_null())) else {
            close("A message is a JSON object with a type.");
            break;
        };
        let kind = message.get("type").and_then(|t| t.as_str()).unwrap_or("");
        if role != Role::New && !(shared.step && UNLIMITED.contains(&kind)) {
            let now = Instant::now();
            while window
                .front()
                .is_some_and(|t| now.duration_since(*t) >= Duration::from_secs(1))
            {
                window.pop_front();
            }
            window.push_back(now);
            if window.len() > shared.rate {
                close(&format!("More than {} messages a second.", shared.rate));
                break;
            }
        }
        match (&role, kind) {
            (Role::New, "hello") => {
                let (answer_tx, answer_rx) = oneshot::channel();
                if let Some(conn) = shared.conns.lock().unwrap().get_mut(&id) {
                    conn.answer = Some(answer_tx);
                }
                let _ = shared.events.send(Event::Hello(id, text));
                let accepted = tokio::select! {
                    a = answer_rx => a.unwrap_or(false),
                    _ = closing.changed() => false,
                };
                if !accepted {
                    break;
                }
            }
            (Role::New, _) => {
                close("Say hello first.");
                break;
            }
            (Role::Control, "cmd") => {
                close("A control connection has no entity: it sends no commands.");
                break;
            }
            (Role::Player, "cmd") => {
                let seq = message.get("seq").and_then(integer);
                let name = message.get("name").and_then(|n| n.as_str());
                let (Some(seq), Some(name)) = (seq, name) else {
                    close("A command has an integer seq and a name.");
                    break;
                };
                let args = match message.get("args") {
                    Some(args) => args.to_string(),
                    None => "{}".to_string(),
                };
                if let Some(conn) = shared.conns.lock().unwrap().get_mut(&id) {
                    conn.last_seq = seq;
                }
                let seq = message
                    .get("seq")
                    .map(|s| s.to_string())
                    .unwrap_or_default();
                let _ = shared
                    .events
                    .send(Event::Cmd(id, seq, name.to_string(), args));
            }
            (_, "ping") => {
                let mut pong = String::from("{\"type\":\"pong\",\"t\":");
                match message.get("t") {
                    Some(t) => write_json(&from_serde(t), &mut pong),
                    None => pong.push_str("null"),
                }
                pong.push_str(&format!(
                    ",\"tick\":{}}}",
                    shared.tick.load(Ordering::Relaxed)
                ));
                say(pong);
            }
            _ => {
                let _ = shared.events.send(Event::Other(id, text));
            }
        }
    }
    {
        let mut conns = shared.conns.lock().unwrap();
        if let Some(conn) = conns.get_mut(&id) {
            if conn.role != Role::Closed {
                let _ = conn.out.send(Out::Close);
                conn.role = Role::Closed;
            }
        }
    }
    let _ = shared.events.send(Event::Closed(id));
    // the closing handshake, as websockets does it: what the other side still sends is read and let go, till its
    // close (two seconds at most), so the last word (an error, its reason) is not lost to a reset
    let _ = tokio::time::timeout(Duration::from_secs(2), async {
        while let Some(Ok(message)) = source.next().await {
            if message.is_close() {
                break;
            }
        }
    })
    .await;
    let _ = writer.await;
    shared.conns.lock().unwrap().remove(&id);
}
