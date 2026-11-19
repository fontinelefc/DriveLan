---
name: DriveLan LAN File Engine
colors:
  surface: '#101226'
  surface-dim: '#101226'
  surface-bright: '#36384e'
  surface-container-lowest: '#0a0c20'
  surface-container-low: '#181a2e'
  surface-container: '#1c1e33'
  surface-container-high: '#26283e'
  surface-container-highest: '#313349'
  on-surface: '#e0e0fd'
  on-surface-variant: '#c3c5d8'
  inverse-surface: '#e0e0fd'
  inverse-on-surface: '#2d2f44'
  outline: '#8d90a1'
  outline-variant: '#434655'
  surface-tint: '#b7c4ff'
  primary: '#b7c4ff'
  on-primary: '#002681'
  primary-container: '#6989ff'
  on-primary-container: '#002172'
  inverse-primary: '#134ee4'
  secondary: '#d0bcff'
  on-secondary: '#3c0091'
  secondary-container: '#571bc1'
  on-secondary-container: '#c4abff'
  tertiary: '#2fd9f4'
  on-tertiary: '#00363e'
  tertiary-container: '#009fb4'
  on-tertiary-container: '#002f36'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b7c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b5'
  secondary-fixed: '#e9ddff'
  secondary-fixed-dim: '#d0bcff'
  on-secondary-fixed: '#23005c'
  on-secondary-fixed-variant: '#5516be'
  tertiary-fixed: '#a2eeff'
  tertiary-fixed-dim: '#2fd9f4'
  on-tertiary-fixed: '#001f25'
  on-tertiary-fixed-variant: '#004e5a'
  background: '#101226'
  on-background: '#e0e0fd'
  surface-variant: '#313349'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  title-sm:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: -0.005em
  body-lg:
    fontFamily: Inter
    fontSize: 15px
    fontWeight: '400'
    lineHeight: 22px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: Inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
  code-sm:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  gutter: 1rem
  margin: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-lg: 1rem
  space-xl: 1.5rem
---

## Brand & Style

The design system establishes a high-performance, dark-mode native utility environment tailored for local-area file management across Windows and Linux desktop operating systems. The product operates fully offline without cloud dependencies, demanding an aesthetic that conveys absolute technical reliability, encrypted security, and low-latency throughput.

The visual style merges Modern Technical Utility with Subtle Glass and Tonal Depth:
- Precision interfaces using controlled contrast boundaries instead of noisy drop-shadows.
- Clear structural division between native desktop window frames, navigation bars, transfer queues, and local folder directories.
- Hardware-accelerated fluidity through subtle gradients and distinct active states, communicating local network speeds and uninterrupted peer-to-peer access.
- Visual clarity designed for sustained focus in long-session system management, peer discovery, and manual directory synchronization.

## Colors

The palette is engineered exclusively for an immersive, glare-free dark environment optimized for desktop screens.

### Core Architecture
- **Canvas Base (`#0E1024`):** Global window backdrop, application frame, and system gutter containers.
- **Surface Elevation (`#181B3A`):** Standard container tier for panels, cards, data grids, and sidebar partitions.
- **Surface Elevated / Hover (`#22264C`):** Interactive surfaces, item hover states, and expanded inspection panes.
- **Structural Stroke (`#2A2E5C`):** Ubiquitous 1px perimeter border across containers, dividers, and default input outlines.

### Brand & Interactive Accents
- **Primary Action (`#3D6BFF`):** Selection states, active peer nodes, focus halos, and text link triggers.
- **Secondary / Ownership (`#8B5CF6`):** Self-hosted directories, local device markers, and administrative highlights.
- **Brand Synergy:** Primary key actions and global active indicators leverage a 135° linear gradient running from `#3D6BFF` to `#8B5CF6`.
- **Tertiary Contrast (`#22D3EE`):** Remote peer folders, active network stream highlights, and keyboard navigation rings.

### Typography & Content Tokens
- **Text High-Contrast (`#F1F3FF`):** Primary headings, directory titles, active transfer counters, and user input text.
- **Text Subdued (`#A3A8D6`):** Secondary metadata, transfer protocols, file sizes, IP addresses, and dormant icons.

### Telemetry & Network Status
- **Online / Connected (`#22C55E`):** Verified active LAN peers and running sync tasks.
- **Offline / Stale (`#64748B`):** Disconnected targets, dormant nodes, and paused transfers.
- **Warning / Syncing (`#F59E0B`):** Concurrent edits, sync conflicts, and degraded network interfaces.
- **Error / Restricted (`#F43F5E`):** Access denial, PIN rejection, storage overflow, and firewall-blocked sockets.

## Typography

Inter serves as the singular foundational type family across headlines, body copy, and UI annotations, providing balanced numerical figures and high legibility at desktop viewing distances. JetBrains Mono is designated strictly for network identifiers, IP addresses, hash validations, and authentication PIN entry sequences.

Hierarchy Rules:
- Primary headlines utilize semi-bold and bold weights with subtle negative tracking to preserve structural density.
- Body sizes default to 14px for general directory listings and detail panels; 13px is applied to meta-dense file lists and status feeds.
- All uppercase metadata indicators (`label-sm`) require `letterSpacing: 0.04em` to guarantee instant readability against dark panel surfaces.

## Layout & Spacing

The layout is built for native desktop canvas constraints with a fixed-column workspace model:
- **Navigation Sidebar:** Fixed width (240px to 280px), collapsible to 64px on smaller desktop viewports.
- **Main Viewport Area:** Fluid grid adapting dynamically to native desktop resizing.
- **Inspector / Detail Drawer:** Optional right-hand docked container (320px fixed).
- **Desktop Window Minimum Bound:** 800px × 600px. Standard starting baseline: 1200px × 800px.

Layout containers rely on rigid 4px and 8px rhythmic increments. Padding inside cards, list items, and status indicators aligns with `space-sm` (8px) for compact layouts and `space-md` (12px) to `space-lg` (16px) for spacious panels. Gutters between grid elements maintain a consistent 16px (`1rem`) separation to uphold scannability across multi-folder tile views.

## Elevation & Depth

Visual hierarchy uses layered surface tonality coupled with crisp 1px borders instead of heavy drop shadows:

1. **Base Layer (`#0E1024`):** Canvas foundation; renders window margins, title bars, and background gutters.
2. **Structural Layer (`#181B3A`):** Core panels, file grid containers, and sidebars framed by a 1px solid `#2A2E5C` border.
3. **Elevated State / Overlay (`#22264C`):** Hovered directory cards, active table rows, and context dropdown menus.
4. **Modal / Critical Overlay:** Renders on `#181B3A` surrounded by a dual-edge treatment: a 1px border of `#2A2E5C` overlaid on an ambient shadow (`box-shadow: 0 16px 40px -8px rgba(5, 7, 18, 0.75)`).

Window blur and backdrop filtering (`backdrop-filter: blur(12px)`) are reserved strictly for floating title-bar segments and modal backdrops, keeping background processes crisp and resource consumption low.

## Shapes

The design system standardizes on calibrated rounded geometry between 10px and 12px for primary containers and modules, balancing modern desktop aesthetics with clean alignment.

- **Base Cards & Main Panels:** Bound with `rounded-lg` (12px / 0.75rem) with continuous 1px `#2A2E5C` strokes.
- **Buttons, Inputs, & Individual Elements:** Styled with `rounded` (10px to 8px) for crisp tactile interaction.
- **Status Badges & Avatar Nodes:** Pill-shaped (`rounded-full`) for instant classification.
- **Split Window Titlebars:** Upper corners match the native desktop window border radius (10px on supported Linux compositors and Windows 11 DWM).

## Components

### Desktop Window Titlebar
- Dedicated 38px drag-region at the window top with centered text styling (`label-md`, `#A3A8D6`).
- Integrated custom title controls: Minimize, Maximize/Restore, and Close.
- Windows/Linux styling: Buttons span 46px × 38px. Standard hover state is `#22264C`; close button hover triggers destructive red (`#F43F5E`) with white glyph rendering.

### Primary & Secondary Buttons
- **Primary Action:** Background set to `linear-gradient(135deg, #3D6BFF 0%, #8B5CF6 100%)`. Border radius 10px, label color `#F1F3FF`, font weight 600. Hover applies subtle brightness boost (1.08) and active state depresses scale (0.98).
- **Secondary Action:** Background `#181B3A`, border 1px solid `#2A2E5C`, text `#F1F3FF`. Hover transitions background to `#22264C` and border to `#3D6BFF`.
- **Tertiary / Ghost:** Borderless, background transparent, text `#A3A8D6`. Hover background `#22264C`, text `#F1F3FF`.

### Segmented PIN Authentication Inputs
- Independent, dedicated digit boxes (typically 4 or 6 slots) sized at 48px × 56px each.
- Default surface `#181B3A`, border 1px solid `#2A2E5C`, text centered using `JetBrains Mono` at 22px bold (`#F1F3FF`).
- Focus state activates a 1px border `#22D3EE` accompanied by a `0 0 0 3px rgba(34, 211, 238, 0.2)` glow ring.
- Error state shifts border to `#F43F5E` and triggers a horizontal shake animation.

### Directory & Share Cards
- Enclosed containers with background `#181B3A`, 1px border `#2A2E5C`, and radius 12px.
- Left-side indicator strip or icon accent denotes origin:
  * **Local Host Folders:** Icon color `#8B5CF6` with badge "Local Share".
  * **Remote LAN Folders:** Icon color `#22D3EE` with badge "Network Share".
- Meta text highlights path, allocated size, and active peer sync count in `#A3A8D6`.

### Alert Callouts & Error Banners
- Sits on `#181B3A` with a heavy left accent border (3px solid).
- **Warning Alert:** Left border `#F59E0B`, icon `#F59E0B`, body text `#F1F3FF`.
- **Lock / Error Alert:** Left border `#F43F5E`, icon `#F43F5E`, body text `#F1F3FF`.
- Includes explicit dismiss or action buttons formatted as ghost pills.

### Network Peer Status Chips
- Pill-shaped inline badges with 6px circular pulse dot.
- Online: Dot `#22C55E` with text `#F1F3FF`.
- Syncing / Busy: Dot `#F59E0B` with text `#F1F3FF`.
- Offline: Dot `#64748B` with text `#A3A8D6`.