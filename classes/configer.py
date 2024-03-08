"""This class generates the config file, with functions to change and get values from it"""
import json
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
            print(f"{guildid} already has a config")
            with open(f"configs/template.json", "w") as outfile:
                outfile.write(json_object)
        else:
            with open(f"configs/{guildid}.json", "w") as outfile:
                outfile.write(json_object)
                print(f"config created for {guildid}")

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
