//! Program executions, straight from the kernel's audit log.
//!
//! Polling /proc for new processes misses anything that starts and exits
//! between two scans — and one-shot commands like `rm -rf` typically live
//! for a millisecond or two. The kernel audit subsystem instead records every
//! `execve` together with its argv, captured in the kernel at exec time, so
//! nothing is too quick to see.
//!
//! DruidOS installs an audit rule (config/audit/60-druidos-hive-exec.rules)
//! tagging every exec from a login session with the key `hive-exec`, and
//! this nerve subscribes to the audit multicast netlink group. That needs
//! only CAP_AUDIT_READ, a capability that can read the audit stream and do
//! nothing else.
//!
//! One exec arrives as several records sharing a serial number — SYSCALL
//! (who, rule key, success), EXECVE (argv), CWD, PATH..., PROCTITLE — closed
//! by an EOE record. [`ExecAssembler`] stitches them back together.

use std::collections::{BTreeMap, HashMap, VecDeque};
use std::io;
use std::os::fd::{AsRawFd, FromRawFd, OwnedFd};
use std::path::PathBuf;

pub const AUDIT_SYSCALL: u16 = 1300;
pub const AUDIT_CWD: u16 = 1307;
pub const AUDIT_EXECVE: u16 = 1309;
pub const AUDIT_EOE: u16 = 1320;

/// The audit rule key DruidOS tags exec records with.
pub const HIVE_EXEC_KEY: &str = "hive-exec";

/// Unfinished events kept while waiting for their EOE record. Events whose
/// EOE never arrives (dropped under load) are evicted oldest first.
const MAX_PENDING: usize = 1024;

/// A completed program execution.
#[derive(Debug, Clone, PartialEq)]
pub struct ExecEvent {
    pub pid: u32,
    pub ppid: Option<u32>,
    pub uid: u32,
    pub comm: String,
    /// The executable that ran, as the kernel saw it (not argv[0]).
    pub exe: Option<String>,
    pub argv: Vec<String>,
    pub cwd: Option<PathBuf>,
}

/// Split `audit(1789051192.502:155): key=value ...` into its serial number
/// and fields. Values never contain whitespace: the kernel hex-encodes any
/// untrusted string that would.
pub fn parse_record(payload: &str) -> Option<(u64, Vec<(&str, &str)>)> {
    let rest = payload.strip_prefix("audit(")?;
    let (stamp, rest) = rest.split_once("):")?;
    let serial = stamp.rsplit_once(':')?.1.parse().ok()?;
    let fields = rest
        .split_whitespace()
        .filter_map(|token| token.split_once('='))
        .collect();
    Some((serial, fields))
}

/// Decode an untrusted string value (argv, comm, cwd): quoted as-is, or
/// hex-encoded when it contains spaces, quotes or control characters.
pub fn decode_string(value: &str) -> String {
    if let Some(inner) = value.strip_prefix('"').and_then(|v| v.strip_suffix('"')) {
        return inner.to_string();
    }
    match hex_decode(value) {
        Some(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        None => value.to_string(),
    }
}

fn hex_decode(value: &str) -> Option<Vec<u8>> {
    if value.is_empty() || value.len() % 2 != 0 || !value.bytes().all(|b| b.is_ascii_hexdigit()) {
        return None;
    }
    (0..value.len())
        .step_by(2)
        .map(|i| u8::from_str_radix(&value[i..i + 2], 16).ok())
        .collect()
}

fn field<'a>(fields: &[(&str, &'a str)], name: &str) -> Option<&'a str> {
    fields
        .iter()
        .find(|(key, _)| *key == name)
        .map(|(_, value)| *value)
}

#[derive(Debug)]
struct Syscall {
    pid: u32,
    ppid: Option<u32>,
    uid: u32,
    comm: String,
    exe: Option<String>,
    succeeded: bool,
    key: String,
}

impl Syscall {
    fn from_fields(fields: &[(&str, &str)]) -> Option<Self> {
        Some(Self {
            pid: field(fields, "pid")?.parse().ok()?,
            ppid: field(fields, "ppid").and_then(|v| v.parse().ok()),
            uid: field(fields, "uid")?.parse().ok()?,
            comm: field(fields, "comm").map(decode_string).unwrap_or_default(),
            exe: field(fields, "exe").map(decode_string),
            succeeded: field(fields, "success") == Some("yes"),
            key: field(fields, "key").map(decode_string).unwrap_or_default(),
        })
    }
}

#[derive(Debug, Default)]
struct PartialExec {
    syscall: Option<Syscall>,
    argc: Option<usize>,
    args: BTreeMap<usize, String>,
    /// Arguments too long for one record arrive as `aN[0]`, `aN[1]`, ...
    chunks: BTreeMap<(usize, usize), String>,
    cwd: Option<PathBuf>,
}

impl PartialExec {
    fn add_execve(&mut self, fields: &[(&str, &str)]) {
        for (key, value) in fields {
            if *key == "argc" {
                self.argc = value.parse().ok();
            } else if let Some(index) = key.strip_prefix('a') {
                if let Some((arg, chunk)) = index.strip_suffix(']').and_then(|i| i.split_once('['))
                {
                    if let (Ok(arg), Ok(chunk)) = (arg.parse(), chunk.parse()) {
                        self.chunks.insert((arg, chunk), decode_string(value));
                    }
                } else if let Ok(arg) = index.parse() {
                    self.args.insert(arg, decode_string(value));
                }
            }
        }
    }

    fn finish(self) -> Option<ExecEvent> {
        let syscall = self.syscall?;
        if !syscall.succeeded || syscall.key != HIVE_EXEC_KEY {
            return None;
        }
        let argc = self.argc.unwrap_or(self.args.len());
        let argv: Vec<String> = (0..argc)
            .map(|i| match self.args.get(&i) {
                Some(arg) => arg.clone(),
                None => self
                    .chunks
                    .range((i, 0)..(i + 1, 0))
                    .map(|(_, chunk)| chunk.as_str())
                    .collect(),
            })
            .collect();
        if argv.is_empty() {
            return None;
        }
        Some(ExecEvent {
            pid: syscall.pid,
            ppid: syscall.ppid,
            uid: syscall.uid,
            comm: syscall.comm,
            exe: syscall.exe,
            argv,
            cwd: self.cwd,
        })
    }
}

/// Reassembles audit records into [`ExecEvent`]s.
#[derive(Default)]
pub struct ExecAssembler {
    pending: HashMap<u64, PartialExec>,
    order: VecDeque<u64>,
}

impl ExecAssembler {
    pub fn new() -> Self {
        Self::default()
    }

    /// Feed one record; returns the execution once its last record (EOE)
    /// is in, if it was a successful exec tagged `hive-exec`.
    pub fn push(&mut self, kind: u16, payload: &str) -> Option<ExecEvent> {
        let (serial, fields) = parse_record(payload)?;
        match kind {
            AUDIT_EOE => self.pending.remove(&serial).and_then(PartialExec::finish),
            AUDIT_SYSCALL => {
                self.entry(serial).syscall = Syscall::from_fields(&fields);
                None
            }
            AUDIT_EXECVE => {
                self.entry(serial).add_execve(&fields);
                None
            }
            AUDIT_CWD => {
                self.entry(serial).cwd = field(&fields, "cwd").map(|v| decode_string(v).into());
                None
            }
            _ => None,
        }
    }

    fn entry(&mut self, serial: u64) -> &mut PartialExec {
        if !self.pending.contains_key(&serial) {
            self.order.push_back(serial);
            if self.order.len() > MAX_PENDING {
                if let Some(oldest) = self.order.pop_front() {
                    self.pending.remove(&oldest);
                }
            }
        }
        self.pending.entry(serial).or_default()
    }
}

/// A read-only subscription to the kernel audit log (needs CAP_AUDIT_READ).
pub struct AuditSocket {
    fd: OwnedFd,
}

impl AuditSocket {
    pub fn subscribe() -> io::Result<Self> {
        const NETLINK_AUDIT: libc::c_int = 9;
        const AUDIT_NLGRP_READLOG: u32 = 1;

        // SAFETY: plain socket(2)/bind(2) calls; the fd is owned immediately
        // and the address is a fully initialized sockaddr_nl.
        unsafe {
            let raw = libc::socket(
                libc::AF_NETLINK,
                libc::SOCK_RAW | libc::SOCK_CLOEXEC,
                NETLINK_AUDIT,
            );
            if raw < 0 {
                return Err(io::Error::last_os_error());
            }
            let fd = OwnedFd::from_raw_fd(raw);

            let mut addr: libc::sockaddr_nl = std::mem::zeroed();
            addr.nl_family = libc::AF_NETLINK as libc::sa_family_t;
            addr.nl_groups = AUDIT_NLGRP_READLOG;
            let bound = libc::bind(
                fd.as_raw_fd(),
                &addr as *const libc::sockaddr_nl as *const libc::sockaddr,
                std::mem::size_of::<libc::sockaddr_nl>() as libc::socklen_t,
            );
            if bound < 0 {
                return Err(io::Error::last_os_error());
            }
            Ok(Self { fd })
        }
    }

    /// Block for the next datagram and hand each record in it to `f`.
    /// ENOBUFS means the kernel dropped records because we fell behind.
    pub fn recv(&self, buf: &mut [u8], mut f: impl FnMut(u16, &str)) -> io::Result<()> {
        // SAFETY: recv(2) into a buffer we own, bounded by its length.
        let n = unsafe {
            libc::recv(
                self.fd.as_raw_fd(),
                buf.as_mut_ptr() as *mut libc::c_void,
                buf.len(),
                0,
            )
        };
        if n < 0 {
            return Err(io::Error::last_os_error());
        }
        for (kind, payload) in netlink_messages(&buf[..n as usize]) {
            f(kind, &payload);
        }
        Ok(())
    }
}

/// Split a netlink datagram into (message type, text payload) pairs.
pub fn netlink_messages(data: &[u8]) -> Vec<(u16, String)> {
    const HEADER: usize = 16;
    let mut messages = Vec::new();
    let mut offset = 0;
    while offset + HEADER <= data.len() {
        let len = u32::from_ne_bytes(data[offset..offset + 4].try_into().unwrap()) as usize;
        let kind = u16::from_ne_bytes(data[offset + 4..offset + 6].try_into().unwrap());
        // Tolerate a length that overshoots the datagram: take what's there.
        let end = if len < HEADER {
            data.len()
        } else {
            (offset + len).min(data.len())
        };
        let payload = &data[offset + HEADER..end];
        let text = String::from_utf8_lossy(payload);
        messages.push((kind, text.trim_end_matches('\0').to_string()));
        offset = (end + 3) & !3;
    }
    messages
}

#[cfg(test)]
mod tests {
    use super::*;

    // Records captured from a DruidOS guest: `rm -rf "/tmp/druidos probe"`
    // run from an SSH session (note the hex-encoded argument with a space).
    const RM_SYSCALL: &str = r#"audit(1789051192.502:155): arch=c000003e syscall=59 success=yes exit=0 a0=5bc321f3d4c0 a1=5bc321f41940 a2=5bc321f3a800 a3=5bc321f41940 items=2 ppid=1082 pid=1388 auid=1000 uid=0 gid=0 euid=0 suid=0 fsuid=0 egid=0 sgid=0 fsgid=0 tty=(none) ses=3 comm="rm" exe="/usr/bin/rm" subj=unconfined key="hive-exec""#;
    const RM_EXECVE: &str = r#"audit(1789051192.502:155): argc=3 a0="rm" a1="-rf" a2=2F746D702F64727569646F732070726F6265"#;
    const RM_CWD: &str = r#"audit(1789051192.502:155): cwd="/home/druid""#;
    const RM_PATH: &str = r#"audit(1789051192.502:155): item=0 name="/usr/bin/rm" inode=785828 dev=fd:02 mode=0100755 ouid=0 ogid=0 rdev=00:00 nametype=NORMAL cap_fp=0 cap_fi=0 cap_fe=0 cap_fver=0 cap_frootid=0"#;
    const RM_PROCTITLE: &str =
        "audit(1789051192.502:155): proctitle=726D002D7266002F746D702F64727569646F732070726F6265";
    const RM_EOE: &str = "audit(1789051192.502:155): ";

    fn rm_event() -> ExecEvent {
        ExecEvent {
            pid: 1388,
            ppid: Some(1082),
            uid: 0,
            comm: "rm".into(),
            exe: Some("/usr/bin/rm".into()),
            argv: vec!["rm".into(), "-rf".into(), "/tmp/druidos probe".into()],
            cwd: Some("/home/druid".into()),
        }
    }

    #[test]
    fn reassembles_a_real_exec_from_its_records() {
        let mut assembler = ExecAssembler::new();

        for (kind, payload) in [
            (AUDIT_SYSCALL, RM_SYSCALL),
            (AUDIT_EXECVE, RM_EXECVE),
            (AUDIT_CWD, RM_CWD),
            (1302, RM_PATH),
            (1327, RM_PROCTITLE),
        ] {
            assert_eq!(assembler.push(kind, payload), None, "finished before EOE");
        }

        let event = assembler.push(AUDIT_EOE, RM_EOE).unwrap();
        assert_eq!(event, rm_event());
        assert_eq!(event.argv.join(" "), "rm -rf /tmp/druidos probe");
    }

    #[test]
    fn interleaved_executions_are_kept_apart() {
        let mut assembler = ExecAssembler::new();
        let other = |record: &str| {
            record
                .replace(":155)", ":156)")
                .replace("pid=1388", "pid=1389")
        };

        assembler.push(AUDIT_SYSCALL, RM_SYSCALL);
        assembler.push(AUDIT_SYSCALL, &other(RM_SYSCALL));
        assembler.push(
            AUDIT_EXECVE,
            &other(r#"audit(1789051192.502:155): argc=2 a0="ls" a1="/""#),
        );
        assembler.push(AUDIT_EXECVE, RM_EXECVE);

        assert_eq!(assembler.push(AUDIT_EOE, RM_EOE).unwrap().argv[0], "rm");
        let second = assembler.push(AUDIT_EOE, &other(RM_EOE)).unwrap();
        assert_eq!((second.pid, second.argv.join(" ").as_str()), (1389, "ls /"));
    }

    #[test]
    fn only_successful_execs_tagged_by_the_hive_rule_count() {
        for syscall in [
            RM_SYSCALL.replace("success=yes", "success=no"),
            RM_SYSCALL.replace(r#"key="hive-exec""#, r#"key="someone-elses-rule""#),
            RM_SYSCALL.replace(r#"key="hive-exec""#, "key=(null)"),
        ] {
            let mut assembler = ExecAssembler::new();
            assembler.push(AUDIT_SYSCALL, &syscall);
            assembler.push(AUDIT_EXECVE, RM_EXECVE);
            assert_eq!(assembler.push(AUDIT_EOE, RM_EOE), None, "{syscall}");
        }
    }

    #[test]
    fn long_arguments_split_into_chunks_are_joined() {
        let mut assembler = ExecAssembler::new();
        assembler.push(AUDIT_SYSCALL, RM_SYSCALL);
        // "rm -rf /tmp/xy" with the last argument split in two hex chunks.
        assembler.push(
            AUDIT_EXECVE,
            r#"audit(1789051192.502:155): argc=3 a0="rm" a1="-rf" a2_len=7 a2[0]=2F746D70 a2[1]=2F7879"#,
        );

        let event = assembler.push(AUDIT_EOE, RM_EOE).unwrap();
        assert_eq!(event.argv.join(" "), "rm -rf /tmp/xy");
    }

    #[test]
    fn records_without_a_syscall_or_eoe_leave_nothing_behind() {
        let mut assembler = ExecAssembler::new();
        assert_eq!(assembler.push(AUDIT_EOE, RM_EOE), None);
        assert_eq!(
            assembler.push(1400, "audit(1.0:9): apparmor=\"DENIED\""),
            None
        );
        assert_eq!(assembler.push(AUDIT_EXECVE, "not an audit record"), None);
    }

    #[test]
    fn pending_events_are_bounded() {
        let mut assembler = ExecAssembler::new();
        for serial in 0..(MAX_PENDING as u64 + 50) {
            assembler.push(
                AUDIT_SYSCALL,
                &RM_SYSCALL.replace(":155)", &format!(":{serial})")),
            );
        }
        assert_eq!(assembler.pending.len(), MAX_PENDING);
    }

    #[test]
    fn decodes_quoted_and_hex_strings() {
        assert_eq!(decode_string(r#""/home/druid""#), "/home/druid");
        assert_eq!(decode_string("2F746D702F61206220"), "/tmp/a b ");
        assert_eq!(decode_string("(null)"), "(null)");
    }

    #[test]
    fn splits_netlink_datagrams_into_records() {
        let mut datagram = Vec::new();
        for (kind, text) in [(AUDIT_EXECVE, RM_EXECVE), (AUDIT_EOE, RM_EOE)] {
            let len = 16 + text.len();
            datagram.extend_from_slice(&(len as u32).to_ne_bytes());
            datagram.extend_from_slice(&kind.to_ne_bytes());
            datagram.extend_from_slice(&[0u8; 10]);
            datagram.extend_from_slice(text.as_bytes());
            while datagram.len() % 4 != 0 {
                datagram.push(0);
            }
        }

        assert_eq!(
            netlink_messages(&datagram),
            vec![
                (AUDIT_EXECVE, RM_EXECVE.to_string()),
                (AUDIT_EOE, RM_EOE.to_string())
            ]
        );
    }
}
