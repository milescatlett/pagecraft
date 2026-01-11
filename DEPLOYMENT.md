# Production Deployment Guide

This guide covers deploying updates to your PageCraft production environment.

## Quick Start

To deploy all updates (database migrations, image migration, etc.):

```bash
python deploy_production.py
```

This script is **idempotent** - it can be run multiple times safely. It will only make changes that haven't been applied yet.

## What the Deployment Script Does

The `deploy_production.py` script performs the following tasks:

### 1. Database Table Creation
- Creates `images` table for image metadata tracking
- Creates `image_folders` table for image organization
- Creates any other missing tables

### 2. Database Column Migrations
- Adds `page_styles` column to pages table (for page-level styling)
- Adds `is_homepage` column to pages table
- Adds menu/footer override columns to pages table
- Adds any other missing columns

### 3. Default Admin User
- Creates default admin user (username: `admin`, password: `admin`) if no users exist
- **⚠️ IMPORTANT**: Change this password immediately after first login!

### 4. Image Migration
- Scans `static/uploads/` folder for existing image files
- Creates database records for any images not already tracked
- Extracts metadata (dimensions, file size, MIME type)
- Preserves original file modification dates

### 5. Uploads Folder Verification
- Ensures `static/uploads/` folder exists
- Verifies folder is writable
- Creates folder if it doesn't exist

## Manual Deployment Steps

If you prefer to run migrations manually:

### Step 1: Backup Your Database
```bash
# Copy your database file
cp cms.db cms.db.backup
```

### Step 2: Backup Your Uploads Folder
```bash
# Copy your uploads folder
cp -r static/uploads static/uploads.backup
```

### Step 3: Pull Latest Code
```bash
git pull origin main
```

### Step 4: Update Dependencies
```bash
pip install -r requirements.txt
```

### Step 5: Run Deployment Script
```bash
python deploy_production.py
```

### Step 6: Restart Application
Restart your Flask application to pick up the changes.

## New Features in This Update

### 1. Caspio API v3 Migration
- Updated from Caspio REST API v2 to v3
- New base URL: `https://{account}.caspio.com/integrations/rest/v3`
- Updated endpoints: `/applications/` → `/bridgeApplications/`
- No action required - automatic

### 2. Image Management System
- **Image Gallery**: View all uploaded images in a dedicated gallery page
- **Usage Tracking**: See which pages/menus/footers use each image
- **Delete Protection**: Cannot delete images that are in use
- **Folders**: Organize images in hierarchical folders
- **Tags**: Tag images for easy searching and filtering
- **Crop Tool**: Create cropped copies of images with visual selection tool
- **Metadata**: Track upload date, user, file size, dimensions

### 3. View Live Button Fix
- Fixed "View Live" button for child pages
- Now correctly builds hierarchical URLs (e.g., `/site/1/parent/child`)

## Environment Variables

Ensure these environment variables are set in your `.env` file:

```env
# Required
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///cms.db

# Optional - Caspio Integration
CASPIO_ACCOUNT_ID=your-account-id
CASPIO_CLIENT_ID=your-client-id
CASPIO_CLIENT_SECRET=your-client-secret
```

## Post-Deployment Checklist

- [ ] Deployment script completed successfully
- [ ] No errors in script output
- [ ] Flask application restarted
- [ ] Can log in to CMS
- [ ] If admin user was created, password has been changed
- [ ] Images page loads correctly
- [ ] Existing pages still render correctly
- [ ] "View Live" button works for all pages
- [ ] File uploads still work

## Troubleshooting

### Issue: "No module named 'app'"
**Solution**: Make sure you're running the script from the project root directory.

### Issue: "Permission denied" on uploads folder
**Solution**: Check folder permissions:
```bash
chmod 755 static/uploads
```

### Issue: Images not showing in gallery
**Solution**: Run the deployment script again - it will migrate missing images.

### Issue: Database locked
**Solution**: Stop all running Flask processes and try again.

### Issue: Pillow installation fails
**Solution**: The script uses Pillow 12.1.0. If it fails to install:
```bash
pip install --upgrade pip
pip install Pillow
```

## Rollback Procedure

If you need to rollback:

1. **Restore database**:
   ```bash
   cp cms.db.backup cms.db
   ```

2. **Restore uploads**:
   ```bash
   rm -rf static/uploads
   cp -r static/uploads.backup static/uploads
   ```

3. **Checkout previous code**:
   ```bash
   git checkout <previous-commit-hash>
   ```

4. **Reinstall old dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Restart application**

## Getting Help

If you encounter issues during deployment:

1. Check the script output for specific error messages
2. Look at Flask application logs
3. Verify environment variables are set correctly
4. Ensure database file has correct permissions
5. Check that Python version is 3.x

## Production Recommendations

### Security
- Change default admin password immediately
- Use strong passwords for all users
- Keep `SECRET_KEY` secret and unique
- Use HTTPS in production
- Enable Flask-Talisman security headers (uncomment in `app/__init__.py`)

### Performance
- Use a production WSGI server (gunicorn, uWSGI)
- Configure rate limiting storage backend (Redis recommended)
- Set up proper logging
- Monitor disk space for uploads folder

### Backup
- Regular database backups (daily recommended)
- Backup uploads folder
- Version control your `.env` file separately (NOT in git)

### Monitoring
- Monitor application logs
- Track upload folder size
- Monitor database size
- Set up error notifications

## Sample Production Deployment with Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Sample Systemd Service File

Create `/etc/systemd/system/caspio-cms.service`:

```ini
[Unit]
Description=PageCraft CMS
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/PageCraft
Environment="PATH=/var/www/PageCraft/venv/bin"
ExecStart=/var/www/PageCraft/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 app:app

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable caspio-cms
sudo systemctl start caspio-cms
```

## Questions?

For issues or questions, refer to the project documentation or create an issue in the repository.
