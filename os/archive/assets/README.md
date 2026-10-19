# DruidOS Assets

This directory contains visual assets for DruidOS.

## Structure

```
assets/
├── fonts/          # Font files
│   └── README.md   # Font licensing info
├── icons/          # Icon sets
│   └── README.md   # Icon specifications
└── themes/         # Theme definitions
    └── README.md   # Theme format documentation
```

## Fonts

The default fonts for DruidOS are:

- **UI Font**: Inter (Google Fonts, OFL)
- **Terminal Font**: JetBrains Mono (JetBrains, OFL)

Download and place font files in `fonts/` directory.

## Icons

DruidOS uses custom icons for the Hive Stack components.
Icon specifications:
- Format: SVG (scalable)
- Sizes: 16px, 24px, 48px, 96px
- Style: Monochrome with accent color support

## Themes

The default theme follows the DruidOS design system:

### Colors
```
--bg-base: #0D0D0D
--bg-surface: #1A1A1A
--bg-elevated: #262626
--border: #333333

--text-primary: #FFFFFF
--text-secondary: #A0A0A0
--text-muted: #666666

--accent: #7B5CFF
--accent-light: #9D85FF
--accent-dark: #5A3DD6

--success: #4ADE80
--warning: #FBBF24
--error: #F87171
--info: #60A5FA
```
