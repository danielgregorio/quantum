//! Wayland layer-shell dock window.

use anyhow::Result;

use crate::apps::AppInfo;
use crate::render::DockRenderer;

#[cfg(feature = "wayland")]
use anyhow::Context;
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

/// Dock position on screen
#[derive(Debug, Clone, Copy, PartialEq)]
pub enum DockPosition {
    Bottom,
    Top,
    Left,
    Right,
}

impl Default for DockPosition {
    fn default() -> Self {
        Self::Bottom
    }
}

/// Dock window using layer-shell protocol
pub struct DockWindow {
    #[cfg(feature = "wayland")]
    connection: Connection,
    renderer: DockRenderer,
    position: DockPosition,
    width: u32,
    height: u32,
    icon_size: u32,
    visible: bool,
}

impl DockWindow {
    /// Create a new dock window (Wayland mode)
    #[cfg(feature = "wayland")]
    pub fn new(position: DockPosition, icon_size: u32) -> Result<Self> {
        let connection = Connection::connect_to_env()
            .context("Failed to connect to Wayland display")?;

        // Calculate dimensions based on position
        let (width, height) = match position {
            DockPosition::Bottom | DockPosition::Top => {
                (800, icon_size + 24) // Horizontal dock
            }
            DockPosition::Left | DockPosition::Right => {
                (icon_size + 24, 600) // Vertical dock
            }
        };

        let renderer = DockRenderer::new(width, height, icon_size);

        Ok(Self {
            connection,
            renderer,
            position,
            width,
            height,
            icon_size,
            visible: false,
        })
    }

    /// Create a new dock window (headless mode when Wayland not available)
    #[cfg(not(feature = "wayland"))]
    pub fn new(position: DockPosition, icon_size: u32) -> Result<Self> {
        // Calculate dimensions based on position
        let (width, height) = match position {
            DockPosition::Bottom | DockPosition::Top => {
                (800, icon_size + 24)
            }
            DockPosition::Left | DockPosition::Right => {
                (icon_size + 24, 600)
            }
        };

        let renderer = DockRenderer::new(width, height, icon_size);

        Ok(Self {
            renderer,
            position,
            width,
            height,
            icon_size,
            visible: false,
        })
    }

    /// Update the dock with application list
    pub fn update(&mut self, pinned_apps: &[&AppInfo], running_apps: &[&AppInfo]) -> Result<()> {
        // Render the dock
        self.renderer.render_dock(pinned_apps, running_apps)?;

        // Show if not visible
        if !self.visible {
            self.show()?;
        }

        Ok(())
    }

    /// Show the dock
    pub fn show(&mut self) -> Result<()> {
        self.visible = true;
        Ok(())
    }

    /// Hide the dock
    pub fn hide(&mut self) -> Result<()> {
        self.visible = false;
        Ok(())
    }

    /// Check if dock is visible
    pub fn is_visible(&self) -> bool {
        self.visible
    }

    /// Get dock position
    pub fn position(&self) -> DockPosition {
        self.position
    }

    /// Set dock position
    pub fn set_position(&mut self, position: DockPosition) {
        self.position = position;
        // Would need to recreate the surface in real implementation
    }

    /// Get icon size
    pub fn icon_size(&self) -> u32 {
        self.icon_size
    }

    /// Get dock dimensions
    pub fn dimensions(&self) -> (u32, u32) {
        (self.width, self.height)
    }

    /// Handle click at position
    pub fn handle_click(&self, x: i32, y: i32, pinned_count: usize) -> Option<usize> {
        // Calculate which icon was clicked based on position
        let padding = 12;
        let spacing = 8;

        let (icon_pos, icon_total) = match self.position {
            DockPosition::Bottom | DockPosition::Top => {
                // Horizontal dock
                let start_x = padding;
                let icon_total = self.icon_size + spacing;
                let relative_x = x - start_x as i32;
                if relative_x < 0 {
                    return None;
                }
                (relative_x as u32, icon_total)
            }
            DockPosition::Left | DockPosition::Right => {
                // Vertical dock
                let start_y = padding;
                let icon_total = self.icon_size + spacing;
                let relative_y = y - start_y as i32;
                if relative_y < 0 {
                    return None;
                }
                (relative_y as u32, icon_total)
            }
        };

        let index = (icon_pos / icon_total) as usize;
        if index < pinned_count {
            Some(index)
        } else {
            None
        }
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
    fn test_dock_creation() {
        let dock = DockWindow::new(DockPosition::Bottom, 48);
        // May succeed in headless mode
        if let Ok(dock) = dock {
            assert!(!dock.is_visible());
            assert_eq!(dock.position(), DockPosition::Bottom);
            assert_eq!(dock.icon_size(), 48);
        }
    }

    #[test]
    fn test_dock_positions() {
        assert_eq!(DockPosition::default(), DockPosition::Bottom);
    }

    #[test]
    fn test_click_handling() {
        let dock = DockWindow::new(DockPosition::Bottom, 48).unwrap();

        // Click on first icon (padding=12, icon=48, spacing=8)
        let result = dock.handle_click(30, 30, 3);
        assert_eq!(result, Some(0));

        // Click on second icon
        let result = dock.handle_click(80, 30, 3);
        assert_eq!(result, Some(1));

        // Click outside
        let result = dock.handle_click(5, 30, 3);
        assert!(result.is_none());
    }
}
