"""Site service for domain lookup and site operations"""
from flask import current_app
from app.models.site import Site


class SiteService:
    """Service for handling site-related operations"""

    @staticmethod
    def get_site_by_domain(domain):
        """
        Look up a site by its domain.

        Args:
            domain (str): Domain name (with or without port)

        Returns:
            Site: Site object or None
        """
        return Site.get_by_domain(domain)

    @staticmethod
    def is_admin_domain(host):
        """
        Check if the request is coming from an admin domain.

        Args:
            host (str): Host header from request

        Returns:
            bool: True if admin domain
        """
        host_lower = host.lower()
        host_without_port = host_lower.split(':')[0]

        admin_domains = current_app.config.get('ADMIN_DOMAINS', [])
        admin_domains_lower = [d.lower() for d in admin_domains]

        return (host_lower in admin_domains_lower or
                host_without_port in admin_domains_lower or
                host_without_port in ['localhost', '127.0.0.1'])
