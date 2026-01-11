"""Security utilities for HTML/CSS sanitization and URL validation"""
import re
from urllib.parse import urlparse
import bleach


# Allowed HTML tags for user content (strict sanitization)
ALLOWED_TAGS = [
    'p', 'br', 'b', 'i', 'u', 'strong', 'em', 'ul', 'ol', 'li', 'a',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'blockquote', 'code', 'pre',
    'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
]

# Allowed HTML attributes
ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target'],
    'img': ['src', 'alt', 'title'],
    '*': ['class']
}

# Safe CSS properties (whitelist)
SAFE_CSS_PROPERTIES = {
    'color', 'backgroundColor', 'textAlign', 'textDecoration',
    'fontWeight', 'fontStyle', 'fontSize', 'fontFamily',
    'padding', 'margin', 'border', 'borderTop', 'borderRight',
    'borderBottom', 'borderLeft', 'borderRadius', 'borderColor',
    'width', 'height', 'maxWidth', 'maxHeight', 'minWidth', 'minHeight',
    'display', 'alignItems', 'justifyContent', 'flexDirection',
    'backgroundImage', 'backgroundSize', 'backgroundPosition', 'backgroundRepeat',
    'boxShadow', 'opacity', 'lineHeight', 'letterSpacing', 'textTransform',
    'custom'  # Allow custom CSS but will validate it
}


def sanitize_html_content(html_content):
    """
    Sanitize HTML content to prevent XSS attacks.
    Strips dangerous tags, JavaScript, and event handlers.

    Args:
        html_content (str): Raw HTML content from user

    Returns:
        str: Sanitized HTML safe for rendering
    """
    if not html_content:
        return ''

    # Use bleach to sanitize HTML
    cleaned = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        strip=True  # Strip disallowed tags instead of escaping
    )

    # Additional safety: remove any javascript: URLs that might have slipped through
    cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)

    return cleaned


def sanitize_css_properties(styles):
    """
    Validate and sanitize CSS property dictionary.
    Removes dangerous CSS values like javascript: URLs.

    Args:
        styles (dict): Dictionary of CSS properties and values

    Returns:
        dict: Sanitized CSS properties
    """
    if not isinstance(styles, dict):
        return {}

    sanitized = {}

    for key, value in styles.items():
        # Only allow whitelisted CSS properties
        if key not in SAFE_CSS_PROPERTIES:
            continue

        if not isinstance(value, str):
            continue

        # Remove dangerous patterns
        value_lower = value.lower()

        # Block javascript: URLs
        if 'javascript:' in value_lower:
            continue

        # Block CSS expressions (IE-specific vulnerability)
        if 'expression' in value_lower:
            continue

        # Block data: URLs in background images (can contain JS in SVG)
        if key in ['backgroundImage', 'background'] and 'data:' in value_lower:
            # Allow data:image but not data:image/svg
            if 'data:image/svg' in value_lower:
                continue

        # Block @import and other at-rules
        if '@import' in value_lower or '@' in value:
            continue

        # Block behavior property (IE-specific)
        if key.lower() == 'behavior':
            continue

        # Block closing style tag attempts
        if '</style' in value_lower or '<script' in value_lower:
            continue

        # Passed all checks, add to sanitized dict
        sanitized[key] = value

    return sanitized


def validate_redirect_url(url, allowed_hosts):
    """
    Validate redirect URL to prevent open redirect vulnerabilities.
    Only allows relative URLs or URLs to allowed hosts.

    Args:
        url (str): The redirect URL to validate
        allowed_hosts (list): List of allowed hostnames

    Returns:
        bool: True if URL is safe, False otherwise
    """
    if not url:
        return False

    # Allow relative URLs (starting with /)
    if url.startswith('/') and not url.startswith('//'):
        return True

    # Parse the URL
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    # If no scheme and no netloc, it's a relative URL
    if not parsed.scheme and not parsed.netloc:
        return True

    # If it has a scheme, check if it's HTTP/HTTPS
    if parsed.scheme and parsed.scheme not in ['http', 'https']:
        return False

    # If it has a host, check if it's in allowed list
    if parsed.netloc:
        # Remove port for comparison
        host = parsed.netloc.split(':')[0].lower()
        return host in [h.lower() for h in allowed_hosts]

    return False


def validate_slug(slug):
    """
    Validate URL slug to ensure it's safe and URL-friendly.

    Args:
        slug (str): The slug to validate

    Returns:
        bool: True if valid, False otherwise
    """
    if not slug:
        return False

    # Slug should only contain lowercase letters, numbers, and hyphens
    # Must not start or end with hyphen
    pattern = r'^[a-z0-9]+(?:-[a-z0-9]+)*$'
    return bool(re.match(pattern, slug.lower()))


def sanitize_widget_content(content):
    """
    Sanitize widget content field based on widget type.

    Args:
        content (str): Widget content

    Returns:
        str: Sanitized content
    """
    # For now, just use HTML sanitization
    # This can be extended to handle different content types
    return sanitize_html_content(content)
