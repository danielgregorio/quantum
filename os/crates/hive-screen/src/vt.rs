//! The virtual terminal the screen sits on: while the scene is drawn, the
//! kernel's text console must not draw over it. `KDSETMODE KD_GRAPHICS`
//! on the terminal that is ours (systemd gives it to the daemon as its
//! standard input, `TTYPath=`) stops the console; `KD_TEXT` gives it back
//! when the daemon leaves, however it leaves.

use std::os::fd::AsRawFd;

const KDSETMODE: libc::c_ulong = 0x4B3A;
const KD_TEXT: libc::c_int = 0;
const KD_GRAPHICS: libc::c_int = 1;

pub struct Console {
    fd: Option<i32>,
}

impl Console {
    /// No console to take: the lab, a test, a daemon with no display.
    pub fn none() -> Console {
        Console { fd: None }
    }

    /// Takes the terminal on standard input into graphics mode, when it is
    /// one. Anything else (a pipe, the lab, a test) is left alone.
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
        Console { fd: Some(fd) }
    }

    pub fn release(&mut self) {
        if let Some(fd) = self.fd.take() {
            // SAFETY: as above.
            unsafe {
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
