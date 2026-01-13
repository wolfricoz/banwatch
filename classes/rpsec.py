import os

import requests


class RpSec:
    @staticmethod
    def get_user(user_id):
        """Get the user's RP Security thread ID"""
        return None

        url = "https://rpsecurity.webrender.net/"
        data = {
            "token" : os.getenv("RPSECSECRET"),
            "userId": str(user_id)
        }
        result = requests.post(url=url, json=data)
        if result.status_code != 200:
            return None
        return int(result.text)
