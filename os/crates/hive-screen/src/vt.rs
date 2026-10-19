//! The virtual terminal the screen sits on. While the scene is drawn, the
//! kernel's text console must not draw over it: `KDSETMODE KD_GRAPHICS`
//! on the terminal that is ours (systemd gives it to the daemon as its
//! standard input, `TTYPath=`) stops the console, and `KD_TEXT` gives it
//! back when the daemon leaves, however it leaves.
//!
//! The terminal is shared with the others: Ctrl+Alt+F2 asks for the
//! console, and the kernel asks us (`VT_PROCESS` mode: a signal to let go,
//! a signal when it is ours again). The daemon lets the display go and
//! answers `VT_RELDISP`; the text console draws there meanwhile, and keys
//! are not ours. Ctrl+Alt+F1 brings it back, whole.

use std::os::fd::AsRawFd;
use std::sync::atomic::{AtomicBool, Ordering};

const KDSETMODE: libc::c_ulong = 0x4B3A;
const KD_TEXT: libc::c_int = 0;
const KD_GRAPHICS: libc::c_int = 1;
const VT_SETMODE: libc::c_ulong = 0x5602;
const VT_RELDISP: libc::c_ulong = 0x5605;
const VT_AUTO: u8 = 0;
const VT_PROCESS: u8 = 1;
const VT_ACKACQ: libc::c_ulong = 2;

/// `struct vt_mode` of <linux/vt.h>.
#[repr(C)]
struct VtMode {
    mode: u8,
    waitv: u8,
    relsig: i16,
    acqsig: i16,
    frsig: i16,
}

/// The kernel asked for the terminal (someone pressed Ctrl+Alt+Fn).
static RELEASE: AtomicBool = AtomicBool::new(false);
/// The terminal is ours again (Ctrl+Alt+F1).
static ACQUIRE: AtomicBool = AtomicBool::new(false);

extern "C" fn on_release(_: libc::c_int) {
    RELEASE.store(true, Ordering::Relaxed);
}

extern "C" fn on_acquire(_: libc::c_int) {
    ACQUIRE.store(true, Ordering::Relaxed);
}

pub struct Console {
    fd: Option<i32>,
}

impl Console {
    /// No console to take: the lab, a test, a daemon with no display.
    pub fn none() -> Console {
        Console { fd: None }
    }

    /// Takes the terminal on standard input into graphics mode, when it is
    /// one, and asks the kernel to tell us before switching it. Anything
    /// else (a pipe, the lab, a test) is left alone.
    pub fn take() -> Console {
        let stdin = std::io::stdin();
        let fd = stdin.as_raw_fd();
        // SAFETY: isatty and ioctl on a descriptor we own; KDSETMODE takes an int.
        let is_tty = unsafe { libc::isatty(fd) } == 1;
        if !is_tty {
            return Console { fd: None };
        }
        let r = unsafe { libc::ioctl(fd, KDSETMODE, KD_GRAPHICS as libc::c_ulong) };
        if r < 0 {
            tracing::warn!(
                "cannot put the console into graphics mode: {} (the text console may draw over the scene)",
                std::io::Error::last_os_error()
            );
            return Console { fd: None };
        }
        tracing::info!("the console is in graphics mode");
        // SAFETY: handlers that only store a flag; VT_SETMODE takes a vt_mode.
        unsafe {
            libc::signal(libc::SIGUSR1, on_release as *const () as libc::sighandler_t);
            libc::signal(libc::SIGUSR2, on_acquire as *const () as libc::sighandler_t);
            let mode = VtMode {
                mode: VT_PROCESS,
                waitv: 0,
                relsig: libc::SIGUSR1 as i16,
                acqsig: libc::SIGUSR2 as i16,
                frsig: 0,
            };
            if libc::ioctl(fd, VT_SETMODE, &mode as *const VtMode) < 0 {
                tracing::warn!(
                    "cannot be told of a terminal switch: {} (Ctrl+Alt+Fn would leave the scene behind)",
                    std::io::Error::last_os_error()
                );
            } else {
                tracing::info!("the terminal switches with us: Ctrl+Alt+F2 leaves the scene, Ctrl+Alt+F1 returns");
            }
        }
        Console { fd: Some(fd) }
    }

    /// Whether the kernel asked for the terminal since the last look.
    pub fn release_asked(&self) -> bool {
        self.fd.is_some() && RELEASE.swap(false, Ordering::Relaxed)
    }

    /// Whether the terminal came back to us since the last look.
    pub fn acquire_asked(&self) -> bool {
        self.fd.is_some() && ACQUIRE.swap(false, Ordering::Relaxed)
    }

    /// Lets the switch happen, once the display is let go.
    pub fn allow_release(&self) {
        if let Some(fd) = self.fd {
            // SAFETY: VT_RELDISP takes an int.
            unsafe {
                libc::ioctl(fd, VT_RELDISP, 1 as libc::c_ulong);
            }
        }
    }

    /// Tells the kernel the terminal is taken again.
    pub fn acknowledge_acquire(&self) {
        if let Some(fd) = self.fd {
            // SAFETY: as above.
            unsafe {
                libc::ioctl(fd, VT_RELDISP, VT_ACKACQ);
            }
        }
    }

    pub fn release(&mut self) {
        if let Some(fd) = self.fd.take() {
            let auto = VtMode {
                mode: VT_AUTO,
                waitv: 0,
                relsig: 0,
                acqsig: 0,
                frsig: 0,
            };
            // SAFETY: as above.
            unsafe {
                libc::ioctl(fd, VT_SETMODE, &auto as *const VtMode);
                libc::ioctl(fd, KDSETMODE, KD_TEXT as libc::c_ulong);
            }
        }
    }
}

impl Drop for Console {
    fn drop(&mut self) {
        self.release();
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn vt_mode_is_the_kernel_s_struct() {
        assert_eq!(std::mem::size_of::<VtMode>(), 8);
        assert_eq!(VT_SETMODE, 0x5602);
        assert_eq!(VT_RELDISP, 0x5605);
    }
}
