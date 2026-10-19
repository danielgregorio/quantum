//! Who is bound to a port, from /proc/net.
//!
//! /proc/net/{tcp,tcp6,udp,udp6} list every socket with its owner's uid and
//! inode, readable by anyone. The owning *process* is not: mapping an inode
//! back to a pid means reading /proc/<pid>/fd, which the kernel only allows
//! to a reader that could ptrace that process — never the case for
//! `_hive-sense` and another user's service. So a holder is identified by
//! the user that owns the socket.

use std::path::Path;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Protocol {
    Tcp,
    Udp,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Socket {
    pub protocol: Protocol,
    pub port: u16,
    pub uid: u32,
    pub inode: u64,
}

/// TCP state column value for LISTEN.
const TCP_LISTEN: &str = "0A";

/// Parse one line of /proc/net/{tcp,tcp6,udp,udp6}:
///
/// ```text
///   sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
///    0: 00000000:1F91 00000000:0000 0A 00000000:00000000 00:00000000 00000000 65534        0 10755 ...
/// ```
///
/// TCP sockets count only while listening; UDP has no listen state, so any
/// bound UDP socket counts.
pub fn parse_line(line: &str, protocol: Protocol) -> Option<Socket> {
    let fields: Vec<&str> = line.split_whitespace().collect();
    if fields.len() < 10 || !fields[0].ends_with(':') {
        return None; // header or malformed
    }
    if protocol == Protocol::Tcp && fields[3] != TCP_LISTEN {
        return None;
    }
    let port = u16::from_str_radix(fields[1].rsplit(':').next()?, 16).ok()?;
    if port == 0 {
        return None;
    }
    Some(Socket {
        protocol,
        port,
        uid: fields[7].parse().ok()?,
        inode: fields[9].parse().ok()?,
    })
}

/// Sockets holding `port` right now: TCP listeners if there are any (the
/// usual conflict), otherwise bound UDP sockets.
pub fn holders_of(port: u16) -> Vec<Socket> {
    holders_in(Path::new("/proc/net"), port)
}

fn holders_in(proc_net: &Path, port: u16) -> Vec<Socket> {
    let read = |file: &str, protocol: Protocol| -> Vec<Socket> {
        std::fs::read_to_string(proc_net.join(file))
            .map(|content| {
                content
                    .lines()
                    .filter_map(|line| parse_line(line, protocol))
                    .filter(|socket| socket.port == port)
                    .collect()
            })
            .unwrap_or_default()
    };

    let tcp: Vec<Socket> = [read("tcp", Protocol::Tcp), read("tcp6", Protocol::Tcp)].concat();
    if !tcp.is_empty() {
        return tcp;
    }
    [read("udp", Protocol::Udp), read("udp6", Protocol::Udp)].concat()
}

#[cfg(test)]
mod tests {
    use super::*;

    // Captured from a DruidOS guest: user nobody (65534) listening on 8081
    // over IPv4 and IPv6, plus sshd's listener and an established session.
    const TCP: &str = "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000:1F91 00000000:0000 0A 00000000:00000000 00:00000000 00000000 65534        0 10755 1 ffff8d3904f2c0c0 100 0 0 10 0
   1: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 7201 1 ffff8d3904f2b000 100 0 0 10 0
   2: 0F02000A:0016 0202000A:D1C4 01 00000000:00000000 02:00053D2E 00000000     0        0 9981 2 ffff8d3904f2d180 20 4 30 10 -1
";
    const TCP6: &str = "  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000000000000000000000000000:1F91 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000 65534        0 10756 1 ffff8d3905424600 100 0 0 10 0
";
    const UDP: &str = "   sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref pointer drops
  0: 00000000:0044 00000000:0000 07 00000000:00000000 00:00000000 00000000   101        0 6120 2 ffff8d3902a1e000 0
";

    fn proc_net() -> tempfile::TempDir {
        let dir = tempfile::tempdir().unwrap();
        std::fs::write(dir.path().join("tcp"), TCP).unwrap();
        std::fs::write(dir.path().join("tcp6"), TCP6).unwrap();
        std::fs::write(dir.path().join("udp"), UDP).unwrap();
        dir
    }

    #[test]
    fn a_dual_stack_listener_is_two_sockets_of_one_user() {
        let dir = proc_net();

        let holders = holders_in(dir.path(), 8081);

        assert_eq!(holders.len(), 2);
        assert!(holders
            .iter()
            .all(|s| s.uid == 65534 && s.protocol == Protocol::Tcp));
        assert_eq!(
            holders.iter().map(|s| s.inode).collect::<Vec<_>>(),
            vec![10755, 10756]
        );
    }

    #[test]
    fn established_connections_are_not_holders() {
        let dir = proc_net();

        let holders = holders_in(dir.path(), 22);

        assert_eq!(holders.len(), 1, "only sshd's listener, not the session");
        assert_eq!(holders[0].inode, 7201);
    }

    #[test]
    fn udp_sockets_count_when_nothing_listens_on_tcp() {
        let dir = proc_net();

        let holders = holders_in(dir.path(), 68);

        assert_eq!(holders.len(), 1);
        assert_eq!((holders[0].protocol, holders[0].uid), (Protocol::Udp, 101));
    }

    #[test]
    fn a_free_port_has_no_holders() {
        let dir = proc_net();
        assert!(holders_in(dir.path(), 9999).is_empty());
    }

    #[test]
    fn header_lines_are_not_sockets() {
        assert!(parse_line(TCP.lines().next().unwrap(), Protocol::Tcp).is_none());
    }
}
