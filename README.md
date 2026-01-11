# PageCraft - Website Builder CMS

A modern, feature-rich content management system built with Flask that allows you to craft and manage beautiful websites with an intuitive drag-and-drop interface.

## Features

- **Multi-Site Management**: Create and manage multiple websites from a single CMS
- **Drag & Drop Page Builder**: Build pages visually with a wide variety of widgets
- **Flexible Menus**: Create menus that can be positioned on top, left, or right
- **Footer Builder**: Design custom footers with drag and drop
- **Bootstrap Integration**: All widgets use Bootstrap 5 components
- **Rich Widget Library**:
  - Headings (H1-H6)
  - Rich Text
  - Custom HTML
  - Separators
  - Buttons (all Bootstrap styles)
  - Cards
  - Alerts
  - Columns (Flex Layout)
  - Images
  - Videos
  - And more!
- **Page Management**: Create unlimited pages with custom slugs
- **Live Preview**: Preview your pages before publishing
- **Modern UI**: Sleek, professional interface

## Installation

The virtual environment and Flask dependencies have already been installed. The project structure is ready to use.

## Running the Application

To start the Flask development server:

```bash
# On Windows
venv\Scripts\python app.py

# On macOS/Linux
venv/bin/python app.py
```

The application will be available at `http://127.0.0.1:5000/`

## Project Structure

```
PageCraft/
├── app.py                  # Main Flask application
├── database.py             # Database configuration
├── models.py               # Database models
├── templates/
│   ├── base.html          # Base template
│   ├── cms/               # CMS interface templates
│   │   ├── dashboard.html
│   │   ├── site_detail.html
│   │   ├── page_builder.html
│   │   ├── menu_builder.html
│   │   └── footer_builder.html
│   ├── preview/           # Preview templates
│   │   └── page.html
│   └── public/            # Public site templates
│       └── page.html
├── static/
│   ├── css/
│   │   └── style.css      # Custom CSS
│   └── js/                # JavaScript files
└── venv/                  # Virtual environment

```

## Usage Guide

### 1. Creating a Site

1. Visit `http://127.0.0.1:5000/`
2. Click "Create New Site"
3. Enter a name and optional domain
4. Click "Create Site"

### 2. Creating Pages

1. Go to your site's detail page
2. Click "New Page"
3. Enter a title and slug (URL-friendly name)
4. Click "Create Page"
5. Use the drag-and-drop builder to add widgets
6. Click "Save" to save your changes
7. Click "Preview" to see your page

### 3. Building Menus

1. From your site detail page, click "New Menu"
2. Enter a name and choose position (top, left, or right)
3. Click "Create Menu"
4. Add menu items by clicking "Add Item"
5. Link items to pages or custom URLs
6. Drag to reorder items
7. Mark as "Active" to show on your site
8. Click "Save Menu"

### 4. Creating Footers

1. From your site detail page, click "New Footer"
2. Enter a name
3. Drag widgets into the footer area
4. Customize each widget by clicking the edit icon
5. Mark as "Active" to show on your site
6. Click "Save Footer"

### 5. Available Widgets

**Page Widgets:**
- **Heading**: Add titles (H1-H6)
- **Rich Text**: Formatted text content
- **Custom HTML**: Add any HTML code
- **Separator**: Horizontal divider line
- **Button**: Bootstrap buttons with various styles
- **Card**: Bootstrap card component
- **Alert**: Information boxes
- **Columns**: Multi-column flex layout
- **Image**: Add images
- **Video**: Embed videos

**Footer Widgets:**
- **Text**: Simple text content
- **Links**: List of links
- **Social**: Social media icons
- **Copyright**: Copyright notice

## Widget Customization

All widgets can be edited by clicking the pencil icon when hovering over them. Each widget has specific options:

- **Headings**: Change text and level (H1-H6)
- **Buttons**: Customize text, URL, and style
- **Cards**: Add title, content, and optional image
- **Alerts**: Choose style (info, success, warning, danger)
- **Images**: Set URL and alt text
- **Videos**: Add embed URL

## Bootstrap Components

The CMS is fully integrated with Bootstrap 5, giving you access to:
- Buttons (primary, secondary, success, danger, warning, info)
- Cards with images
- Alerts
- Grid system (columns)
- Responsive utilities
- Typography
- And all other Bootstrap components via custom HTML widget

## Database

The application uses SQLite for simplicity. The database file `cms.db` will be created automatically on first run.

### Models:
- **Site**: Represents a website
- **Page**: Individual pages within a site
- **Menu**: Navigation menus
- **MenuItem**: Items within a menu
- **Footer**: Footer sections
- **Widget**: Widgets on pages

## Preview vs Public URLs

- **Preview URL**: `http://127.0.0.1:5000/preview/{page_id}` - Shows a preview banner
- **Public URL**: `http://127.0.0.1:5000/site/{site_id}/{slug}` - Live page view

## Tips

1. **Slug Format**: Use lowercase letters, numbers, and hyphens (e.g., `about-us`, `contact`)
2. **Active Menus/Footers**: Only one menu and footer per site should be marked as "Active"
3. **Widget Order**: Drag widgets to reorder them on the page
4. **Bootstrap Classes**: Use the Custom HTML widget to add any Bootstrap component
5. **Responsive**: All pages are responsive by default thanks to Bootstrap

## Security Notes

- Change the `SECRET_KEY` in [app.py](app.py:8) before deploying to production
- Use a production-grade database (PostgreSQL, MySQL) instead of SQLite for production
- Add authentication/authorization for the CMS interface
- Validate and sanitize custom HTML input to prevent XSS attacks

## Future Enhancements

Potential features to add:
- User authentication and roles
- Media library for images/files
- SEO settings per page
- Page templates
- Custom CSS editor
- Form builder
- Blog functionality
- Multi-language support
- Export/import functionality

## License

This project is provided as-is for your use.

## Support

For issues or questions, please refer to the Flask documentation:
- Flask: https://flask.palletsprojects.com/
- Bootstrap: https://getbootstrap.com/
- SQLAlchemy: https://www.sqlalchemy.org/
