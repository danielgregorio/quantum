//! Framebuffer test - validates bark and spore
//!
//! Run in DruidOS:
//!   fb-test
//!
//! Should display a colored rectangle and text on screen.

use bark::Framebuffer;
use spore::{Canvas, Color, TextRenderer};

fn main() {
    println!("=== DruidOS Framebuffer Test ===");

    // Try to open framebuffer
    let fb_result = Framebuffer::open_default();

    match fb_result {
        Ok(mut fb) => {
            println!("Framebuffer opened: {}x{} @ {}bpp", fb.width, fb.height, fb.bpp);

            // Create canvas at framebuffer resolution
            let mut canvas = Canvas::new(fb.width, fb.height);

            // Clear to dark background
            canvas.clear(Color::rgb(20, 20, 40));

            // Draw a red rectangle
            canvas.fill_rect(50, 50, 200, 100, Color::RED);

            // Draw a green rectangle
            canvas.fill_rect(100, 100, 200, 100, Color::GREEN);

            // Draw a blue rectangle with transparency
            canvas.fill_rect(150, 150, 200, 100, Color::rgba(0, 100, 255, 180));

            // Draw text
            let text = TextRenderer::default_font();
            text.draw(&mut canvas, 50, 300, "DruidOS v0.4", Color::WHITE);
            text.draw(&mut canvas, 50, 320, "bark + spore working!", Color::CYAN);
            text.draw(&mut canvas, 50, 340, "Press Ctrl+C to exit", Color::YELLOW);

            // Draw a circle
            canvas.fill_circle(600, 200, 80, Color::MAGENTA);

            // Copy to framebuffer and display
            fb.copy_buffer(canvas.pixels());
            fb.flush();

            println!("Graphics drawn! Check the screen.");
            println!("Press Ctrl+C to exit...");

            // Keep running so user can see the result
            loop {
                std::thread::sleep(std::time::Duration::from_secs(1));
            }
        }
        Err(e) => {
            eprintln!("Failed to open framebuffer: {}", e);
            eprintln!("Make sure /dev/fb0 exists and you have permissions.");
            std::process::exit(1);
        }
    }
}
