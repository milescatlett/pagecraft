import os
import requests
from datetime import datetime, timedelta

class CaspioAPI:
    """Helper class for interacting with Caspio REST API"""

    def __init__(self):
        self.access_token = None
        self.token_expires = None

    @property
    def account_id(self):
        """Read account_id from environment each time (supports hot-reload of .env)"""
        return os.environ.get('CASPIO_ACCOUNT_ID', '')

    @property
    def client_id(self):
        """Read client_id from environment each time"""
        return os.environ.get('CASPIO_CLIENT_ID', '')

    @property
    def client_secret(self):
        """Read client_secret from environment each time"""
        return os.environ.get('CASPIO_CLIENT_SECRET', '')

    @property
    def base_url(self):
        return f"https://{self.account_id}.caspio.com/integrations/rest/v3"

    @property
    def token_url(self):
        return f"https://{self.account_id}.caspio.com/oauth/token"

    def is_configured(self):
        """Check if Caspio credentials are configured"""
        return bool(self.account_id and self.client_id and self.client_secret)

    def get_access_token(self):
        """Get OAuth2 access token using client credentials"""
        if not self.is_configured():
            return None

        # Return cached token if still valid
        if self.access_token and self.token_expires and datetime.now() < self.token_expires:
            return self.access_token

        try:
            response = requests.post(
                self.token_url,
                data={
                    'grant_type': 'client_credentials',
                    'client_id': self.client_id,
                    'client_secret': self.client_secret
                },
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )

            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 86400)  # Default 24 hours
                self.token_expires = datetime.now() + timedelta(seconds=expires_in - 60)  # Refresh 1 min early
                return self.access_token
            else:
                print(f"Failed to get Caspio access token: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error getting Caspio access token: {e}")
            return None

    def _make_request(self, endpoint, method='GET', params=None):
        """Make an authenticated request to the Caspio API"""
        token = self.get_access_token()
        if not token:
            return None

        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        url = f"{self.base_url}/{endpoint}"

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            else:
                response = requests.request(method, url, headers=headers, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                print(f"Caspio API error: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error calling Caspio API: {e}")
            return None

    def get_applications(self):
        """Get list of all bridge applications"""
        result = self._make_request('bridgeApplications')
        if result and 'Result' in result:
            return result['Result']
        return []

    def get_datapages(self):
        """Get all datapages organized by app and folder"""
        if not self.is_configured():
            return {'configured': False, 'apps': []}

        apps = self.get_applications()
        if not apps:
            return {'configured': True, 'apps': [], 'error': 'Failed to fetch applications'}

        result = []
        for app in apps:
            app_name = app.get('AppName', 'Unknown')
            external_key = app.get('ExternalKey', '')

            # Get datapages for this app using ExternalKey (not AppName)
            datapages_result = self._make_request(f'bridgeApplications/{external_key}/datapages')

            if datapages_result and 'Result' in datapages_result:
                datapages = datapages_result['Result']

                # Organize by folder
                folders = {}
                no_folder = []

                for dp in datapages:
                    dp_name = dp.get('Name', 'Unnamed')
                    dp_key = dp.get('AppKey', '')
                    dp_folder = dp.get('Path', '').strip('/')

                    datapage_info = {
                        'name': dp_name,
                        'key': dp_key,
                        'appName': app_name,
                        'deployUrl': f"https://{self.account_id}.caspio.com/dp/{dp_key}"
                    }

                    if dp_folder:
                        if dp_folder not in folders:
                            folders[dp_folder] = []
                        folders[dp_folder].append(datapage_info)
                    else:
                        no_folder.append(datapage_info)

                app_data = {
                    'name': app_name,
                    'id': external_key,
                    'folders': [{'name': k, 'datapages': v} for k, v in sorted(folders.items())],
                    'datapages': no_folder  # Datapages not in any folder
                }
                result.append(app_data)

        return {'configured': True, 'apps': result}


# Global instance
caspio_api = CaspioAPI()
