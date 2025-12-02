import json
import requests

from OLogger.MyLogger import myLogger
from Api.RoleReq_class import RoleReq
from Api.RoleResp_class import RoleResp


class APIClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update ({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        })

    def get_data(self, endpoint):
        url = f"{self.base_url}/{endpoint}"
        response = self.session.get(url)
        return response.json()


if __name__ == '__main__':
    client = APIClient("https://api.example.com", "YOUR_TOKEN")
    data = client.get_data("users")