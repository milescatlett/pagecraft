# PageCraft - Flask Website Builder CMS

## Overview

A drag-and-drop website builder built with Flask and Bootstrap. Create multiple sites, each with their own pages, menus, and footers. Uses a visual page builder with a widget-based system.

## Architecture

### Backend (Flask)

- **Framework**: Flask with SQLAlchemy ORM
- **Database**: SQLite (`cms.db`)
- **Templates**: Jinja2
- **File Structure**:

  ```
  app.py              # Main Flask application with all routesLink Text

  models.py           # SQLAlchemy database models
  database.py         # Database initialization
  templates/
    ├── cms/          # CMS builder interfaces
    ├── preview/      # Preview templates
    └── public/       # Published page templates
  static/
    └── uploads/      # User-uploaded images
  ```

### Frontend

- **UI Framework**: Bootstrap 5.3.2
- **Icons**: Bootstrap Icons
- **Drag & Drop**: Native HTML5 drag and drop API
- **Styling**: All widgets support custom CSS properties

## Database Models

### Site

- `id`, `name`, `domain`
- Relationships: pages, menus, footers

### Page

- `id`, `site_id`, `title`, `slug`, `published`
- `content`: JSON string of widget array
- `page_styles`: JSON string of page-level CSS properties

### Menu

- `id`, `site_id`, `name`, `position` (top/left/right)
- `is_active`: Boolean for site-wide activation
- `content`: JSON string of widgets (menus can have widgets!)
- `menu_styles`: JSON string of menu CSS properties

### MenuItem

- `id`, `menu_id`, `label`, `link_type` (page/custom)
- `page_id`, `custom_url`, `order`

### Footer

- `id`, `site_id`, `name`, `is_active`
- `content`: JSON string of widgets
- `footer_styles`: JSON string of footer CSS properties

### Widget

- Legacy model - widgets are now stored as JSON in Page.content

## Widget System

### Widget Structure

All widgets are JavaScript objects stored as JSON with this base structure:

```javascript
{
  id: "timestamp-random",  // Format: "1234567890-12345"
  type: "widget_type",
  styles: {
    color: "#000000",
    backgroundColor: "#ffffff",
    borderTop: "1px solid #000",
    borderRadius: "5px",
    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
    padding: "10px",
    margin: "5px",
    // ... other CSS properties
  }
}
```

### Available Widgets

#### Layout Widgets

- **Row**: Container with Bootstrap grid columns
  - `numColumns`: Number of columns (1-12)
  - `children`: Array of column widgets
- **Column**: Grid column (used inside rows)
  - `width`: Bootstrap column width (1-12)
  - `children`: Array of child widgets

#### Content Widgets

- **Heading**: `h1` to `h6` tags
  - `content`, `level`
- **Rich Text**: Formatted text content
  - `content`
- **HTML**: Custom HTML code
  - `content`
- **Separator**: Horizontal line (`<hr>`)

#### Component Widgets

- **Button**: Bootstrap button with link
  - `text`, `url`, `style` (primary/secondary/success/danger/warning/info)
- **Link**: Hyperlink with optional dropdown
  - `text`, `url`, `target` (\_self/\_blank)
  - `dropdownItems`: Array of `{text, url}` for dropdown menu
- **Card**: Bootstrap card
  - `title`, `content`, `image`
- **Alert**: Bootstrap alert box
  - `content`, `style`
- **Image**: Image element
  - `src`, `alt`
- **Video**: Embedded video (iframe)
  - `url`
- **Accordion**: Collapsible panels
  - `items`: Array of `{title, content, expanded}`
- **Badge**: Bootstrap badge
  - `text`, `style`
- **Breadcrumb**: Navigation breadcrumbs
  - `items`: Array of `{text, url, active}`
- **Collapse**: Toggle-able content
  - `title`, `content`, `expanded`
- **Tabs**: Tab navigation
  - `tabs`: Array of `{title, content, active}`
- **Toast**: Notification toast
  - `title`, `content`, `style`

## Key Features

### Page Builder (`/page/<id>/edit`)

- Drag widgets from sidebar to canvas
- Nested layouts: rows → columns → widgets
- Edit widgets via modal
- Live preview in builder canvas
- Auto-save on widget changes
- Page-level styling (background, padding, etc.)

### Menu Builder (`/menu/<id>/edit`)

- Create menu items (links to pages or custom URLs)
- Add widgets to menu content area
- Configure menu position (top/left/right)
- Style menus with custom CSS
- Set active menu for site-wide display

### Footer Builder (`/footer/<id>/edit`)

- Add widgets to footer
- Style footer with custom CSS
- Set active footer for site-wide display

### Preview & Publishing

- **Preview** (`/preview/<page_id>`): See page with active menu/footer
- **Public** (`/site/<site_id>/<slug>`): Only shows published pages
- Both render widgets from JSON using Jinja2 macros

## Styling System

### Widget Styles

Every widget can have custom styles applied via the "Edit Styles" section in the widget modal:

- Colors (text, background)
- Borders (all sides, radius)
- Box shadow
- Padding & margin
- Background images
- Custom CSS

### Row & Column Styling

**Important**: Rows and columns use wrapper divs for styling to avoid Bootstrap grid conflicts:

```html
<!-- Row -->
<div class="mb-4">
  <div style="/* custom styles here */">
    <div class="row">
      <!-- columns here -->
    </div>
  </div>
</div>

<!-- Column -->
<div class="col-6">
  <div style="/* custom styles here */">
    <!-- widget content here -->
  </div>
</div>
```

This prevents Bootstrap's flexbox and gutter system from conflicting with custom padding/margins/borders.

### Page Styles

Pages have their own styling system accessed via "Page Styling" button:

- Background color
- Text color
- Padding
- Margin
- Custom CSS

Styles auto-save and are stored in `page.page_styles` as JSON.

## Important Technical Details

### Widget ID Generation

Widget IDs use format: `timestamp-random` (e.g., `1765218369732-45678`)

- **Old format** (broken): `timestamp.decimal` - causes issues with CSS selectors
- IDs must not contain periods (`.`) as they break `data-bs-target` selectors in Bootstrap

### JSON Encoding

- **Backend**: Use `json.dumps()` when saving to database
- **Template → JS**: Use `|safe` filter to pass JSON objects
- **Backend → Template**: Parse JSON in route, pass as dict, use `|tojson` in template
- Watch for double-encoding issues!

### Bootstrap Integration

- Bootstrap 5.3.2 CSS and JS loaded via CDN
- All interactive components (accordions, dropdowns, tabs, etc.) require Bootstrap JS
- Dropdowns need `data-bs-toggle="dropdown"` attribute

### File Uploads

- Route: `/upload` (POST)
- Allowed: png, jpg, jpeg, gif, webp, svg
- Max size: 16MB
- Returns: `{success: true, url: "/static/uploads/filename.ext"}`
- Storage: `static/uploads/` directory

## Recent Fixes & Improvements

1. **Accordion Fix**: Changed widget ID generation from decimal to dash format to fix Bootstrap data-target selectors
2. **Page Styles**: Fixed JSON parsing for page_styles, added proper initialization and auto-save
3. **Row/Column Styling**: Restructured HTML to use wrapper divs, preventing Bootstrap grid conflicts
4. **Link Widget**: Added new widget type with dropdown support for navigation menus
5. **Preview Rendering**: Added page_styles support to both preview and public page templates

## Routes Reference

### CMS Routes

- `/` - Dashboard (list sites)
- `/site/<id>` - Site detail (pages, menus, footers)
- `/page/<id>/edit` - Page builder
- `/page/<id>/save` - Save page (POST)
- `/page/<id>/preview` - Preview page
- `/menu/<id>/edit` - Menu builder
- `/menu/<id>/save` - Save menu (POST)
- `/footer/<id>/edit` - Footer builder
- `/footer/<id>/save` - Save footer (POST)

### Public Routes

- `/site/<site_id>/<slug>` - Published page (only if `published=True`)

### Utility Routes

- `/upload` - File upload (POST)

## Development Notes

- **Debug Mode**: `app.run(debug=True)` in `app.py`
- **Database**: Created automatically on first run via `db.create_all()`
- **Virtual Environment**: Located in `venv/` directory
- **Python Version**: Works with Python 3.x
- **Dependencies**: See `requirements.txt`

## Tips for Claude/Developers

1. **Widget Changes**: When modifying widgets, update all three locations:

   - `createWidget()` in page_builder.html (default values)
   - Render logic in page_builder.html (canvas preview)
   - Template rendering in preview/page.html and public/page.html

2. **Styling Issues**: If styles aren't applying, check:

   - Is `build_style_attr()` macro being called on the element?
   - For rows/columns, are you using the wrapper div structure?
   - Is the JSON being properly parsed from database to template?

3. **Bootstrap Components**: Must include both CSS and JS CDN links for interactive components to work

4. **Database Migrations**: No Alembic setup - schema changes require manual migration scripts

5. **Widget IDs**: Always use string IDs with dashes, never periods or decimals
