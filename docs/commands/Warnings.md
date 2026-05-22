---
layout: default
title: Warnings
parent: Commands
nav_order: 11
---

<h1>Warnings</h1>
<h6>version: 3.4.0: Now with a warning system!</h6>
<h6>Documentation automatically generated from docstrings.</h6>

Represents a cog that also doubles as a parent :class:`discord.app_commands.Group` for
the application commands defined within it.

This inherits from :class:`Cog` and the options in :class:`CogMeta` also apply to this.
See the :class:`Cog` documentation for methods.

Decorators such as :func:`~discord.app_commands.guild_only`, :func:`~discord.app_commands.guilds`,
and :func:`~discord.app_commands.default_permissions` will apply to the group if used on top of the
cog.

Hybrid commands will also be added to the Group, giving the ability to categorize slash commands into
groups, while keeping the prefix-style command as a root-level command.

For example:

.. code-block:: python3

    from discord import app_commands
    from discord.ext import commands

    @app_commands.guild_only()
    class MyCog(commands.GroupCog, group_name='my-cog'):
        pass

.. versionadded:: 2.0


### `warn`

**Usage:** `/warnings warn <member> <kick> <inform>`

> Create a warning for the selected member with the options to inform them, kick them, and permanent logging.

Permissions:
- manage messages

---

### `manage`

**Usage:** `/warnings manage <user>`

> Allows you to manage the warnings you have, as well as add evidence or even take actions against the user.

Permissions:
- manage messages

---

