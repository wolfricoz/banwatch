"""This class generates the config file, with functions to change and get values from it"""
import json
import logging
import os

cache_path = "settings/cache.json"


class LongTermCache():
    """This class generates the config file, with functions to change and get values from it"""

    def create(self):
        """Creates the config"""
        dictionary = {
            "bans": {}

        }
        json_object = json.dumps(dictionary, indent=4)
        if os.path.exists(cache_path):
            self.update()
            return
        with open(cache_path, "w") as outfile:
            outfile.write(json_object)
            logging.info(f"cache created")

    def update(self):
        """updates the dictionary"""
        with open(cache_path) as f:
            data = json.load(f)
            dictionary = {
                "bans"       : data.get("bans", {}),
                "logged_bans": data.get("logged_bans", {})
            }
        with open(cache_path, "w") as f:
            json.dump(dictionary, f, indent=4)
            logging.info(f"cache updated")

    def add_ban(self, waitid, dict):
        """Adds a ban to the cache"""
        waitid = str(waitid)
        if not os.path.exists(cache_path):
            self.create()
        with open(cache_path) as f:
            data = json.load(f)
            print(data["bans"])
            if waitid in data["bans"]:
                print("removing")
                data["bans"].pop(waitid)
            data["bans"][waitid] = dict
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=4)
            logging.info(f"ban added to cache")

    def get_ban(self, waitid):
        """Gets a ban from the cache"""
        waitid = str(waitid)
        if not os.path.exists(cache_path):
            self.create()
        with open(cache_path) as f:
            data = json.load(f)
            print(waitid)
            print(data["bans"])
            if waitid not in data["bans"]:
                return False
            return data["bans"][waitid]

    def remove_ban(self, waitid):
        """Removes a ban from the cache"""
        waitid = str(waitid)
        if not os.path.exists(cache_path):
            self.create()
        with open(cache_path) as f:
            data = json.load(f)
            if waitid not in data["bans"]:
                return False
            data["bans"].pop(waitid)
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=4)
            logging.info(f"ban removed from cache")
        return True

    def update_logged_bans(self, bans: dict):
        """Adds a ban to the cache"""
        if not os.path.exists(cache_path):
            self.create()
        with open(cache_path) as f:
            data = json.load(f)
            data["logged_bans"] = bans
        with open(cache_path, 'w') as f:
            json.dump(data, f, indent=4)
            logging.info(f"ban added to cache")

    def get_logged_bans(self):
        """Gets a ban from the cache"""
        if not os.path.exists(cache_path):
            self.create()
        with open(cache_path) as f:
            data = json.load(f)
            return data.get("logged_bans", {})
