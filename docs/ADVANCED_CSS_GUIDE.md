# Advanced CSS Properties Guide

FM Skin Builder now supports advanced CSS properties beyond just colors! You can now customize fonts, dimensions, borders, opacity, and more using standard CSS syntax.

## 🎨 What's New

In addition to colors, you can now modify:
- **Font Properties**: font-size, font-weight, font-family, text-align
- **Dimension Properties**: width, height, padding, margin
- **Border Properties**: border-width, border-radius, border-color
- **Visual Effects**: opacity, visibility, display, overflow
- **Position/Layout**: position, left, top, flex properties

## 📝 Syntax

### CSS Variables

Define variables in your `.uss` or `.css` files:

```css
/* Font properties */
--button-font-size: 16px;
--button-font-weight: 700;
--title-font: url('resource://fonts/RobotoBold');
--body-text-align: center;

/* Dimension properties */
--button-width: 200px;
--button-height: 40px;
--button-padding: 10px 20px;
--content-margin: 15px;

/* Border properties */
--button-border-radius: 8px;
--button-border-width: 2px;
--button-border-color: #FF0000;

/* Visual effects */
--button-opacity: 0.9;
--menu-visibility: visible;
--panel-display: flex;
```

### Selector Overrides

Apply properties to specific UI elements:

```css
.button {
  font-size: 16px;
  font-weight: bold;
  width: 200px;
  height: 40px;
  padding: 10px;
  border-radius: 8px;
  opacity: 0.9;
  color: #FFFFFF;
}

.title-text {
  font-size: 24px;
  -unity-font: url('resource://fonts/RobotoBold');
  -unity-text-align: center;
  color: #FFD700;
}

.panel {
  width: 400px;
  height: 300px;
  padding: 20px;
  background-color: #1A1A1A;
  border-radius: 12px;
  visibility: visible;
}
```

## 🔤 Font Properties

### Font Size
```css
--heading-font-size: 24px;
--body-font-size: 14px;
--caption-font-size: 0.8em;

.heading { font-size: 24px; }
```

Units supported: `px`, `em`, `rem`, `pt`, `%`

### Font Weight
```css
--title-font-weight: 700;
--body-font-weight: 400;

.title { font-weight: bold; }  /* Keywords: normal, bold */
.title { font-weight: 700; }    /* Numeric: 100-900 */
```

### Font Family (Resource Reference)
```css
--custom-font: url('resource://fonts/RobotoBold');
--title-font: url('resource://fonts/Montserrat-ExtraBold');

.title {
  -unity-font: url('resource://fonts/RobotoBold');
  -unity-font-definition: url('resource://fonts/RobotoSDF');
}
```

**Note**: Unity expects fonts in `resource://` format. Place font assets in your Unity project's Resources folder.

### Text Alignment
```css
--title-align: center;

.title {
  -unity-text-align: center;  /* left, right, center, justify */
  -unity-text-align: upper-center;  /* Unity-specific alignments */
}
```

### Font Style
```css
.italic { -unity-font-style: italic; }
.bold { -unity-font-style: bold; }
.bold-italic { -unity-font-style: bold-and-italic; }
```

## 📐 Dimension Properties

### Width and Height
```css
--button-width: 200px;
--button-height: 40px;
--panel-width: 50%;

.button {
  width: 200px;
  height: 40px;
  min-width: 100px;
  max-width: 400px;
}

.panel {
  width: 50%;
  height: auto;
}
```

Keywords: `auto`, numeric values with units

### Padding
```css
/* All sides */
--button-padding: 10px;

/* Vertical | Horizontal */
--button-padding: 10px 20px;

/* Top | Right | Bottom | Left */
--button-padding: 10px 20px 10px 20px;

.button {
  padding: 10px;                    /* All sides */
  padding: 10px 20px;               /* V | H */
  padding: 10px 20px 15px 20px;    /* T | R | B | L */

  /* Individual sides */
  padding-top: 10px;
  padding-right: 20px;
  padding-bottom: 10px;
  padding-left: 20px;
}
```

### Margin
```css
.panel {
  margin: 15px;                /* All sides */
  margin: 10px 20px;          /* V | H */
  margin: 10px 20px 15px 20px; /* T | R | B | L */
  margin: auto;                /* Center horizontally */

  /* Individual sides */
  margin-top: 10px;
  margin-right: 20px;
  margin-bottom: 15px;
  margin-left: 20px;
}
```

## 🎯 Border Properties

### Border Width
```css
.button {
  border-width: 2px;                     /* All sides */
  border-width: 1px 2px;                /* V | H */
  border-width: 1px 2px 1px 2px;        /* T | R | B | L */

  /* Individual sides */
  border-top-width: 1px;
  border-right-width: 2px;
  border-bottom-width: 1px;
  border-left-width: 2px;
}
```

### Border Radius
```css
.button {
  border-radius: 8px;                    /* All corners */
  border-radius: 8px 12px;              /* TL+BR | TR+BL */
  border-radius: 8px 12px 8px 12px;     /* TL | TR | BR | BL */

  /* Individual corners */
  border-top-left-radius: 8px;
  border-top-right-radius: 12px;
  border-bottom-right-radius: 8px;
  border-bottom-left-radius: 12px;
}
```

### Border Color
```css
.button {
  border-color: #FF0000;                 /* All sides */
  border-color: #FF0000 #00FF00;        /* V | H */

  /* Individual sides */
  border-top-color: #FF0000;
  border-right-color: #00FF00;
  border-bottom-color: #0000FF;
  border-left-color: #FFFF00;
}
```

## ✨ Visual Effects

### Opacity
```css
.button {
  opacity: 0.9;    /* 0.0 (transparent) to 1.0 (opaque) */
  opacity: 0.5;
  opacity: 1;
}
```

### Visibility
```css
.menu {
  visibility: visible;  /* visible, hidden */
}
```

### Display
```css
.panel {
  display: flex;    /* flex, none, inline, block */
}
```

### Overflow
```css
.scrollable {
  overflow: scroll;  /* visible, hidden, scroll, clip */
}
```

### Background Scale Mode
```css
.image {
  -unity-background-scale-mode: scale-to-fit;
  /* Options: stretch-to-fill, scale-and-crop, scale-to-fit */
}
```

## 📍 Position and Layout

### Position
```css
.floating-button {
  position: absolute;  /* relative, absolute, static */
  left: 20px;
  top: 20px;
}
```

### Flex Layout
```css
.container {
  flex-direction: row;      /* row, column, row-reverse, column-reverse */
  flex-wrap: wrap;          /* nowrap, wrap, wrap-reverse */
  justify-content: center;  /* flex-start, flex-end, center, space-between */
  align-items: center;      /* flex-start, flex-end, center, stretch */
}

.item {
  flex-grow: 1;
  flex-shrink: 0;
  flex-basis: auto;
}
```

## 💡 Usage Examples

### Button Customization
```css
/* Define variables */
--primary-button-width: 200px;
--primary-button-height: 48px;
--primary-button-font-size: 16px;
--primary-button-border-radius: 8px;
--primary-button-bg: #0066FF;
--primary-button-text: #FFFFFF;

/* Apply to selector */
.primary-button {
  width: 200px;
  height: 48px;
  font-size: 16px;
  border-radius: 8px;
  background-color: #0066FF;
  color: #FFFFFF;
  opacity: 1;
}

.primary-button:hover {
  opacity: 0.8;
}
```

### Card/Panel Design
```css
.info-card {
  width: 400px;
  min-height: 200px;
  padding: 24px;
  margin: 16px;
  border-radius: 12px;
  border-width: 1px;
  border-color: #333333;
  background-color: #1A1A1A;
}

.info-card__title {
  font-size: 20px;
  font-weight: bold;
  -unity-text-align: center;
  color: #FFFFFF;
  margin-bottom: 12px;
}

.info-card__body {
  font-size: 14px;
  -unity-text-align: left;
  color: #CCCCCC;
  padding: 8px;
}
```

### Custom Font Loading
```css
/* Use custom fonts from Unity Resources */
.title-text {
  -unity-font: url('resource://fonts/Montserrat-ExtraBold');
  font-size: 32px;
  -unity-text-align: center;
  color: #FFD700;
}

.body-text {
  -unity-font: url('resource://fonts/Roboto-Regular');
  font-size: 14px;
  -unity-text-align: left;
  color: #FFFFFF;
}
```

## 🔧 Technical Details

### Unity StyleSheet Value Types

FM Skin Builder now supports all Unity StyleSheet value types:

- **Type 1/8**: Keywords and enums (visibility, display, font-style, etc.)
- **Type 2**: Floats with units (dimensions, font-size, opacity)
- **Type 4**: Colors (hex, rgb, rgba) - existing support
- **Type 7**: Resource references (fonts, images via url())

### Property Type Registry

50+ USS properties are registered and mapped to their Unity types:

```python
# Examples from property_handlers.py
"font-size": Type 2 (float)
"opacity": Type 2 (float)
"visibility": Type 1/8 (keyword)
"-unity-font": Type 7 (resource)
"border-radius": Type 2 (float)
```

### Value Parsing

Values are automatically parsed based on syntax:

```css
12px         → Float value (12.0, unit: "px")
bold         → Keyword value ("bold")
url('...')   → Resource value (path)
#FF0000      → Color value (rgb: 255, 0, 0)
```

## 📋 Supported Properties Reference

### Font Properties
- `font-size` (float)
- `font-weight` (float or keyword: normal, bold)
- `-unity-font` (resource)
- `-unity-font-definition` (resource)
- `-unity-font-style` (keyword: normal, italic, bold, bold-and-italic)
- `-unity-text-align` (keyword)
- `-unity-text-outline-width` (float)
- `-unity-text-outline-color` (color)
- `color` (color)
- `white-space` (keyword)

### Dimension Properties
- `width`, `height` (float or keyword: auto)
- `min-width`, `min-height` (float or keyword)
- `max-width`, `max-height` (float or keyword)

### Padding & Margin
- `padding`, `padding-top/right/bottom/left` (float)
- `margin`, `margin-top/right/bottom/left` (float or keyword: auto)

### Border Properties
- `border-width`, `border-top/right/bottom/left-width` (float)
- `border-radius`, `border-top-left/right-radius`, `border-bottom-left/right-radius` (float)
- `border-color`, `border-top/right/bottom/left-color` (color)

### Background Properties
- `background-color` (color)
- `background-image` (resource)
- `-unity-background-image-tint-color` (color)
- `-unity-background-scale-mode` (keyword)

### Visual Effects
- `opacity` (float 0-1)
- `visibility` (keyword: visible, hidden)
- `display` (keyword: flex, none, inline, block)
- `overflow` (keyword: visible, hidden, scroll, clip)

### Position & Layout
- `position` (keyword: relative, absolute, static)
- `left`, `top`, `right`, `bottom` (float or keyword: auto)
- `flex-direction` (keyword)
- `flex-wrap` (keyword)
- `flex-grow`, `flex-shrink` (float)
- `flex-basis` (float or keyword: auto)
- `align-items`, `align-self` (keyword)
- `justify-content` (keyword)

## ⚙️ How It Works

1. **CSS Collection**: Parser reads all CSS variables and selector overrides
2. **Value Detection**: Each value is automatically classified (color, float, keyword, resource)
3. **Type Matching**: Property name is matched to expected Unity type via registry
4. **Value Patching**: Appropriate handler updates Unity arrays:
   - Colors → `colors` array (Type 4)
   - Floats → `floats` array (Type 2)
   - Keywords → `strings` array (Type 1/8)
   - Resources → `strings` array (Type 7)
5. **Bundle Writing**: Modified stylesheet is saved to output bundle

## 🚀 Migration from Colors-Only

Existing color-only skins are 100% backwards compatible. Simply add new properties to your CSS files:

```css
/* Before (colors only) */
--button-bg: #0066FF;
--button-text: #FFFFFF;

/* After (with advanced properties) */
--button-bg: #0066FF;
--button-text: #FFFFFF;
--button-font-size: 16px;        /* NEW */
--button-border-radius: 8px;     /* NEW */
--button-opacity: 0.9;           /* NEW */
```

## 🐛 Troubleshooting

### Property Not Applying

1. **Check property name spelling**: Unity USS uses specific property names (e.g., `-unity-font`, not `font-family`)
2. **Verify value format**: Ensure units are included for floats (`12px` not `12`)
3. **Check logs**: Look for `[PATCHED - float/keyword/resource]` messages
4. **Property support**: Verify property is in supported list above

### Font Not Loading

1. **Use correct resource path**: Fonts must be in `resource://fonts/FontName` format
2. **Font in Resources folder**: Ensure font is in Unity's `Resources/fonts/` directory
3. **Font name matches**: Check Unity asset name matches the path

### Invalid Value Error

1. **Unknown unit**: Only standard CSS units are supported (`px`, `em`, `%`, etc.)
2. **Invalid keyword**: Check keyword spelling and availability for that property
3. **Malformed url()**: Ensure proper syntax: `url('path')` or `url("path")`

## 📚 Learn More

- [Unity USS Property Reference](https://docs.unity3d.com/Manual/UIE-USS-Properties-Reference.html)
- [Unity UI Toolkit](https://docs.unity3d.com/Manual/UIElements.html)
- FM Skin Builder Implementation Plan: `docs/FONT_IMPLEMENTATION_PLAN.md`
