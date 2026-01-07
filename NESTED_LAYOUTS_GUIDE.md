# Nested Layouts Guide

## Overview

The page builder now supports **infinitely nested rows and columns**, allowing you to create complex, flexible layouts with unlimited depth. You can nest rows inside columns, columns inside rows, and build any layout structure you need!

## Layout Widgets

### Row Widget
- **Purpose**: Creates a horizontal container for columns
- **Visual**: Green dashed border in the builder
- **Bootstrap**: Renders as Bootstrap `<div class="row">`
- **Can contain**: Columns, content widgets, or even other rows!
- **Quick action**: Click "+ Column" button to add a new column

### Column Widget
- **Purpose**: Creates a vertical section within a row
- **Visual**: Blue dashed border in the builder
- **Bootstrap**: Renders as Bootstrap `<div class="col-{width}">`
- **Width**: Configurable from 1-12 (Bootstrap grid units)
- **Can contain**: Any widgets, including rows for nested layouts!

## How to Build Nested Layouts

### Basic Two-Column Layout

1. Drag a **Row** widget onto the canvas
2. Click the "+ Column" button on the row (adds a column automatically)
3. Click "+ Column" again to add a second column
4. Drag content widgets (heading, text, image, etc.) into each column

```
Row
├── Column (6/12)
│   └── Heading: "Left Content"
└── Column (6/12)
    └── Text: "Right Content"
```

### Nested Layouts

#### Example 1: Three Columns with Nested Content

1. Create a Row
2. Add 3 columns (edit each to set width: 4, 4, 4)
3. Inside the middle column, drag another **Row**
4. Add 2 columns inside that nested row
5. Add content to the nested columns

```
Row
├── Column (4/12)
│   └── Card
├── Column (4/12)
│   └── Row (nested)
│       ├── Column (6/12)
│       │   └── Image
│       └── Column (6/12)
│           └── Text
└── Column (4/12)
    └── Card
```

#### Example 2: Sidebar Layout with Nested Sections

```
Row
├── Column (3/12) - Sidebar
│   ├── Heading
│   ├── Text
│   └── Button
└── Column (9/12) - Main Content
    ├── Row
    │   ├── Column (6/12)
    │   │   └── Card
    │   └── Column (6/12)
    │       └── Card
    └── Row
        └── Column (12/12)
            └── Rich Text
```

#### Example 3: Complex Dashboard Layout

```
Row (Header)
└── Column (12/12)
    └── Heading: "Dashboard"

Row (Content)
├── Column (4/12) - Left Sidebar
│   ├── Card: "Stats"
│   └── Card: "Links"
├── Column (8/12) - Main Area
│   ├── Row
│   │   ├── Column (6/12)
│   │   │   └── Card: "Chart 1"
│   │   └── Column (6/12)
│   │       └── Card: "Chart 2"
│   └── Row
│       └── Column (12/12)
│           ├── Heading
│           └── Text

Row (Footer)
└── Column (12/12)
    └── Text: "Copyright"
```

## Working with Nested Layouts

### Adding Widgets to Containers

1. **Direct Drag**: Drag any widget from the sidebar directly into a row or column
2. **Drop Zones**: Empty rows/columns show a drop zone - drag widgets here
3. **Visual Feedback**: Containers highlight when you drag over them

### Editing Containers

**Row Options:**
- Click the pencil icon to edit row settings
- Click "+ Column" to quickly add a new column
- Columns are automatically set to width 6

**Column Options:**
- Click the pencil icon to edit column width (1-12)
- Width represents Bootstrap grid units
- Example: 3 columns of width 4 = full row (4+4+4=12)

### Column Width Tips

Bootstrap uses a 12-column grid system:
- **col-12**: Full width
- **col-6**: Half width (50%)
- **col-4**: One third (33%)
- **col-3**: One quarter (25%)
- **col-8**: Two thirds (66%)
- **col-9**: Three quarters (75%)

Common layouts:
- **Sidebar + Content**: 3/12 + 9/12 or 4/12 + 8/12
- **Two Columns**: 6/12 + 6/12
- **Three Columns**: 4/12 + 4/12 + 4/12
- **Four Columns**: 3/12 + 3/12 + 3/12 + 3/12

### Visual Indicators

- **Green containers**: Rows (can contain columns)
- **Blue containers**: Columns (can contain any widgets)
- **White containers**: Content widgets (headings, text, images, etc.)
- **Hover effects**: Colored borders show what you're hovering over
- **Drag highlight**: Containers light up when you can drop into them

## Best Practices

### 1. Plan Your Structure
Sketch out your layout before building:
- What's the main content area?
- Do you need sidebars?
- How many columns per section?

### 2. Start with Rows
Always start with a Row at the top level, then add columns inside

### 3. Use Appropriate Nesting
- Don't nest too deeply (3-4 levels max for readability)
- Keep it simple when possible
- More nesting = more complexity

### 4. Column Widths Should Add Up to 12
Within each row, column widths should total 12:
- ✅ 6 + 6 = 12
- ✅ 4 + 4 + 4 = 12
- ✅ 3 + 9 = 12
- ❌ 6 + 8 = 14 (will wrap to next line)

### 5. Mobile Responsiveness
Bootstrap columns automatically stack on mobile, so:
- Rows become vertical on small screens
- Columns stack on top of each other
- Test your layout in different sizes!

## Common Layout Patterns

### Hero Section with Call-to-Actions
```
Row
└── Column (12/12)
    ├── Heading (H1)
    ├── Text
    └── Row
        ├── Column (6/12)
        │   └── Button: "Get Started"
        └── Column (6/12)
            └── Button: "Learn More"
```

### Feature Grid (3 Features)
```
Row
├── Column (4/12)
│   ├── Image
│   ├── Heading (H3)
│   └── Text
├── Column (4/12)
│   ├── Image
│   ├── Heading (H3)
│   └── Text
└── Column (4/12)
    ├── Image
    ├── Heading (H3)
    └── Text
```

### Content with Sidebar
```
Row
├── Column (8/12) - Main Content
│   ├── Heading
│   ├── Text
│   ├── Image
│   └── Text
└── Column (4/12) - Sidebar
    ├── Card: "Related"
    ├── Card: "Popular"
    └── Button: "Subscribe"
```

### Image Gallery (2x2)
```
Row
├── Column (6/12)
│   └── Image
└── Column (6/12)
    └── Image

Row
├── Column (6/12)
│   └── Image
└── Column (6/12)
    └── Image
```

## Tips & Tricks

1. **Quick Column Addition**: Use the "+ Column" button on rows instead of dragging columns from the sidebar

2. **Nested Rows for Spacing**: Add a row inside a column to create sub-sections with better control

3. **Full-Width Sections**: Use a single column with width 12 for full-width content

4. **Asymmetric Layouts**: Try 4/8, 3/9, or 7/5 splits for unique designs

5. **Testing**: Always preview your page to see how the layout looks with real Bootstrap rendering

6. **Reordering**: You can drag entire rows and columns to reorder them (including all nested content!)

## Troubleshooting

**Problem**: Columns aren't side-by-side
- **Solution**: Make sure they're inside the same Row and widths total ≤ 12

**Problem**: Can't drag widget into column
- **Solution**: Make sure you're dragging over the column's drop zone, not the column header

**Problem**: Layout looks wrong in preview
- **Solution**: Check that column widths add up to 12 within each row

**Problem**: Too much nesting
- **Solution**: Simplify - often 2 levels (Row > Column > Content) is enough

## Advanced Example: Complete Landing Page

```
[Row] Full-width header
└── [Column 12]
    ├── Heading: "Welcome"
    └── Text: "Subtitle"

[Row] Three features
├── [Column 4]
│   ├── Image
│   ├── Heading
│   └── Text
├── [Column 4]
│   ├── Image
│   ├── Heading
│   └── Text
└── [Column 4]
    ├── Image
    ├── Heading
    └── Text

[Row] Content with sidebar
├── [Column 8]
│   ├── Heading
│   ├── Text
│   └── [Row] Nested images
│       ├── [Column 6]
│       │   └── Image
│       └── [Column 6]
│           └── Image
└── [Column 4]
    ├── Card: "Sign up"
    └── Card: "Resources"

[Row] Call to action
└── [Column 12]
    ├── Heading
    └── Button
```

## Summary

The nested layout system gives you **complete flexibility** to create any layout you can imagine:

✅ Unlimited nesting depth
✅ Drag and drop interface
✅ Visual feedback while building
✅ Bootstrap-powered responsive design
✅ Full control over column widths
✅ Mix content and layout widgets freely

Start simple, then experiment with nesting to create more complex designs!
