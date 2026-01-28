---
layout: default
title: Staff
parent: Commands
nav_order: 7
---

<h1>Staff</h1>
<h6>version: 3.2</h6>
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


### `servers`

**Usage:** `/staff servers`

> Fetches and lists all servers the bot is currently in. This command is for internal staff use to get an overview of the bot's reach.

**Permissions:**
- Requires BanWatch Staff access.

---

### `serverinfo`

**Usage:** `/staff serverinfo <server>`

> Retrieves and displays detailed information about a specific server the bot is in. This includes owner, member counts, and bot-specific data.

**Permissions:**
- Requires BanWatch Staff access.

---

### `userinfo`

**Usage:** `/staff userinfo <user>`

> Displays detailed information about a specific user across all servers the bot shares with them. Includes ban history and server presence.

**Permissions:**
- Requires BanWatch Staff access.

---

### `verifyban`

**Usage:** `/staff verifyban <ban_id> <status> <provide_proof>`

> Changes the verification status of a ban. Verified bans are considered confirmed and may be treated with higher priority. Proof is required to verify.

**Permissions:**
- Requires BanWatch Staff access.

---

### `banvisibility`

**Usage:** `/staff banvisibility <ban_id> <hide>`

> Changes the visibility of a specific ban. Hidden bans will not appear in public logs or commands, making them visible only to staff.

**Permissions:**
- Requires BanWatch Staff access.

---

### `rpseclookup`

**Usage:** `/staff rpseclookup <user>`

> Looks up a user's record in the Roleplay Security Bot's database threads. This is a developer tool for cross-referencing security information.

**Permissions:**
- Requires BanWatch Staff access.

---

### `revokeban`

**Usage:** `/staff revokeban <banid> <reason>`

> Revokes a ban's log message from all servers. This action does not unban the user but removes the public announcement of the ban.

**Permissions:**
- Requires BanWatch Staff access.

---

### `amistaff`

**Usage:** `/staff amistaff`

> Checks if you are recognized as a BanWatch staff member. This is a simple way to verify your access level within the bot's permission system.

**Permissions:**
- None required for the user.

---

### `calc_banid`

**Usage:** `/staff calc_banid <user> <guild>`

> Calculates the unique ban ID that would be generated for a specific user in a specific guild. This is a utility for debugging and manual lookups.

**Permissions:**
- Requires BanWatch Staff access.

---

### `staff_visibility`

**Usage:** `/staff staff_visibility <server> <hide>`

> Sets the visibility of a server's bans within the BanWatch network. Hiding a server prevents its bans from being shared or viewed by other servers.

**Permissions:**
- Requires BanWatch Staff access.

---

