//! Wayland layer-shell overlay window.

use anyhow::{Context, Result};
use hive_common::messages::Suggestion;

use crate::render::Renderer;

#[cfg(feature = "wayland")]
use std::os::unix::io::AsFd;
#[cfg(feature = "wayland")]
use wayland_client::{
    globals::{registry_queue_init, GlobalListContents},
    protocol::{wl_compositor, wl_shm, wl_surface},
    Connection, Dispatch, QueueHandle,
};
#[cfg(feature = "wayland")]
use wayland_protocols_wlr::layer_shell::v1::client::{
    zwlr_layer_shell_v1, zwlr_layer_surface_v1,
};

/// Overlay window using layer-shell protocol
pub struct OverlayWindow {
    #[cfg(feature = "wayland")]
    connection: Connection,
    renderer: Renderer,
    width: u32,
    height: u32,
    visible: bool,
}

impl OverlayWindow {
    /// Create a new overlay window
    #[cfg(feature = "wayland")]
    pub fn new() -> Result<Self> {
        // Try to connect to Wayland
        let connection = Connection::connect_to_env()
            .context("Failed to connect to Wayland display")?;

        let renderer = Renderer::new(400, 300);

        Ok(Self {
            connection,
            renderer,
            width: 400,
            height: 300,
            visible: false,
        })
    }

    /// Create a new overlay window (headless mode when Wayland not available)
    #[cfg(not(feature = "wayland"))]
    pub fn new() -> Result<Self> {
        let renderer = Renderer::new(400, 300);

        Ok(Self {
            renderer,
            width: 400,
            height: 300,
            visible: false,
        })
    }

    /// Update the overlay with new suggestions
    pub fn update(&mut self, suggestions: &[&Suggestion]) -> Result<()> {
        if suggestions.is_empty() {
            self.hide()?;
            return Ok(());
        }

        // Render suggestions
        self.renderer.render_suggestions(suggestions)?;

        // Show if not visible
        if !self.visible {
            self.show()?;
        }

        Ok(())
    }

    /// Show the overlay
    pub fn show(&mut self) -> Result<()> {
        self.visible = true;
        Ok(())
    }

    /// Hide the overlay
    pub fn hide(&mut self) -> Result<()> {
        self.visible = false;
        Ok(())
    }

    /// Check if overlay is visible
    pub fn is_visible(&self) -> bool {
        self.visible
    }
}

// Wayland event handling state (only when feature enabled)
#[cfg(feature = "wayland")]
struct WaylandState {
    compositor: Option<wl_compositor::WlCompositor>,
    shm: Option<wl_shm::WlShm>,
    layer_shell: Option<zwlr_layer_shell_v1::ZwlrLayerShellV1>,
    surface: Option<wl_surface::WlSurface>,
    layer_surface: Option<zwlr_layer_surface_v1::ZwlrLayerSurfaceV1>,
    configured: bool,
}

#[cfg(feature = "wayland")]
impl WaylandState {
    fn new() -> Self {
        Self {
            compositor: None,
            shm: None,
            layer_shell: None,
            surface: None,
            layer_surface: None,
            configured: false,
        }
    }
}

#[cfg(feature = "wayland")]
impl Dispatch<wl_compositor::WlCompositor, ()> for WaylandState {
    fn event(
        _state: &mut Self,
        _proxy: &wl_compositor::WlCompositor,
        _event: wl_compositor::Event,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        // Compositor doesn't send events
    }
}

#[cfg(feature = "wayland")]
impl Dispatch<wl_shm::WlShm, ()> for WaylandState {
    fn event(
        _state: &mut Self,
        _proxy: &wl_shm::WlShm,
        _event: wl_shm::Event,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        // Handle shm format events if needed
    }
}

#[cfg(feature = "wayland")]
impl Dispatch<wl_surface::WlSurface, ()> for WaylandState {
    fn event(
        _state: &mut Self,
        _proxy: &wl_surface::WlSurface,
        _event: wl_surface::Event,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        // Handle surface events
    }
}

#[cfg(feature = "wayland")]
impl Dispatch<zwlr_layer_shell_v1::ZwlrLayerShellV1, ()> for WaylandState {
    fn event(
        _state: &mut Self,
        _proxy: &zwlr_layer_shell_v1::ZwlrLayerShellV1,
        _event: zwlr_layer_shell_v1::Event,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        // Layer shell doesn't send events
    }
}

#[cfg(feature = "wayland")]
impl Dispatch<zwlr_layer_surface_v1::ZwlrLayerSurfaceV1, ()> for WaylandState {
    fn event(
        state: &mut Self,
        _proxy: &zwlr_layer_surface_v1::ZwlrLayerSurfaceV1,
        event: zwlr_layer_surface_v1::Event,
        _data: &(),
        _conn: &Connection,
        _qh: &QueueHandle<Self>,
    ) {
        match event {
            zwlr_layer_surface_v1::Event::Configure { serial, .. } => {
                // Acknowledge configure
                if let Some(ref layer_surface) = state.layer_surface {
                    layer_surface.ack_configure(serial);
                }
                state.configured = true;
            }
            zwlr_layer_surface_v1::Event::Closed => {
                state.configured = false;
            }
            _ => {}
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_overlay_creation() {
        // Test headless mode (without Wayland feature)
        let overlay = OverlayWindow::new();
        // May succeed in headless mode, fail if trying real Wayland
        if let Ok(overlay) = overlay {
            assert!(!overlay.is_visible());
        }
    }
}
