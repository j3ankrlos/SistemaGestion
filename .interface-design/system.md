# Sistema Porcino — System Design

## Direction & Feel
Cálido, terroso, artesanal — como un cuaderno de campo al atardecer. Profundo, con un toque de arcilla cocida y texturas naturales. Inspirado en granja, campo y registro manual.

## Core Tokens
```css
--bg-primary:   #12100e   /* Fondo general */
--bg-secondary: #1a1714   /* Sidebar, cards */
--bg-tertiary:  #2a231d   /* Hover, inputs */
--accent:       #d4874a   /* Naranja arcilla */
--accent-hover: #c07a3e
--text-primary: #e8ddd0   /* Texto principal */
--text-secondary:#a69583  /* Texto secundario */
--danger:       #d4554a   /* Rojo arcilla */
--success:      #6bab5a   /* Verde oliva */
--border:       #3a3028   /* Bordes */
```

## Depth Strategy
Borders + subtle shadows. No shadows on dark mode — lean on borders.
Elevation: 1px border on all surfaces. Cards get 1px border + soft multi-layer shadow on light mode only.

## Spacing
Base unit: 4px. Component padding: 12-16px, section gaps: 20-24px.

## Typography
- Typeface: Inter (400, 500, 600, 700)
- Scale ratio: ~1.25
- Body: 14-16px, weight/color hierarchy (600 primary, 500 secondary, 400 muted)
- Labels: 0.75rem uppercase tracked

## Border Radius
- Inputs/buttons: 10px
- Cards: 10px
- Auth card: 20px
- Emblema: 22px

## Auth (Login & Setup)
- Background: radial-gradient tierra nocturna
- Card: fondo `#1f1813`, glow decorativo detrás del emblema
- Emblema (cerdo): 72px, gradient arcilla `#d4874a → #e8a05a`, box-shadow glow
- Inputs: fondo oscuro `#16100c`, iconos internos, glow naranja al focus
- Botón primary: gradient arcilla, texto oscuro `#1a1410`

## Patterns
- **User avatar**: gradient arcilla 38px circle, box-shadow glow
- **Status badges**: pill con dot, active=verde oliva, inactive=rojo arcilla
- **Submenu**: accordion slide, chevron rotate, max-height transition
- **Pagination**: bordered pills, active=filled accent
- **Modals**: backdrop blur, slide-in animation, section headers uppercase
