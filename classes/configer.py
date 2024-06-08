"""This class generates the config file, with functions to change and get values from it"""
import json
import logging
import os
from abc import ABC, abstractmethod


class Configer(ABC):
    """This class generates the config file, with functions to change and get values from it"""

    @staticmethod
    @abstractmethod
    async def create(guildid, guildname):
        """Creates the config"""
        dictionary = {
            "Name"      : guildname,
            "modchannel": 0,
        }
        json_object = json.dumps(dictionary, indent=4)
        if os.path.exists(f"configs/{guildid}.json"):
            with open(f"configs/template.json", "w") as outfile:
                outfile.write(json_object)
        else:
            with open(f"configs/{guildid}.json", "w") as outfile:
                outfile.write(json_object)
                logging.info(f"config created for {guildid}")

    @staticmethod
    @abstractmethod
    async def create_bot_config(guildid):
        """Creates the general config"""
        dictionary = {
            "blacklist": [],
        }
        json_object = json.dumps(dictionary, indent=4)
        if os.path.exists(f"configs/{guildid}.json"):
            return
        with open(f"configs/config.json", "w") as outfile:
            outfile.write(json_object)
            logging.info(f"config created for {guildid}")

    @staticmethod
    @abstractmethod
    async def change(guildid, interaction, channelid, key):
        """Changes value in the config"""
        if os.path.exists(f"configs/{guildid}.json"):
            with open(f"configs/{guildid}.json") as f:
                data = json.load(f)
                data[key] = channelid
            with open(f"configs/{guildid}.json", 'w') as f:
                json.dump(data, f, indent=4)
            await interaction.followup.send(f"Config key **{key}** changed to **{channelid}**")

    @staticmethod
    @abstractmethod
    async def get(guildid, key):
        """Gets a value from the config"""
        if os.path.exists(f"configs/{guildid}.json"):
            with open(f"configs/{guildid}.json") as f:
                data = json.load(f)
                return data[key]

    @staticmethod
    @abstractmethod
    async def add_to_blacklist(guildid):
        """Adds a server to the blacklist"""
        if os.path.exists(f"configs/config.json"):
            with open(f"configs/config.json") as f:
                data = json.load(f)
                data["blacklist"].append(guildid)
            with open(f"configs/config.json", 'w') as f:
                json.dump(data, f, indent=4)
                logging.info(f"{guildid} added to blacklist")

    @staticmethod
    @abstractmethod
    async def remove_from_blacklist(guildid):
        """Removes a server from the blacklist"""
        if os.path.exists(f"configs/config.json"):
            with open(f"configs/config.json") as f:
                data = json.load(f)
                data["blacklist"].remove(guildid)
            with open(f"configs/config.json", 'w') as f:
                json.dump(data, f, indent=4)
                logging.info(f"{guildid} removed from blacklist")

    @staticmethod
    @abstractmethod
    async def is_blacklisted(guildid):
        """Checks if a server is blacklisted"""
        if os.path.exists(f"configs/config.json"):
            with open(f"configs/config.json") as f:
                data = json.load(f)
                if guildid in data["blacklist"]:
                    return True