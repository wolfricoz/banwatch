---
layout: default
title: Permissions
nav_order: 9
---

# Permissions

Banwatch needs the right Discord permissions to do its job, and the people who
configure it need the right permissions too. This page covers both.

## Bot permissions

When you invite Banwatch it requests a set of permissions. You can invite it
here:

<https://discord.com/oauth2/authorize?client_id=1047697525349564436>

The bot uses two OAuth2 scopes:

- **`bot`** — lets Banwatch join your server and act as a member.
- **`applications.commands`** — lets Banwatch register its `/` slash commands.

### What each permission is for

| Permission                                | Why Banwatch needs it                                                                                                                                         |
|-------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Ban Members**                           | Core function. Without it Banwatch cannot read your server's ban list, ban a user, or apply network bans. If this is missing the bot effectively cannot work. |
| **Kick Members**                          | Used by `/tools kick` and by automated warning punishments that kick.                                                                                         |
| **Manage Server**                         | Required to set the bot up, read server information, and access the server's invites.                                                                         |
| **Create Instant Invite**                 | Lets Banwatch generate an invite back to the server a user was banned from, so staff can review context.                                                      |
| **Send Messages**                         | Required to post ban notifications and moderation logs into your mod channel.                                                                                 |
| **Embed Links / Use Embedded Activities** | Required to send the rich embeds Banwatch uses for ban info, lookups, and onboarding.                                                                         |
| **Attach Files**                          | Used to attach evidence and to deliver exports (e.g. `/tools export_bans`).                                                                                   |
| **Manage Messages**                       | Used by `/utility clean_messages` to tidy Banwatch's own messages from a channel.                                                                             |
| **View Audit Log**                        | Lets Banwatch attribute bans/unbans to the moderator who performed them.                                                                                      |
| **Read Messages / View Channel**          | Required in the mod channel so the bot can operate there.                                                                                                     |

> Banwatch will **never** automatically ban your members without you being
> informed. The Ban Members permission is used to *read* bans and to act only
> when you or your staff choose to.

### Checking the bot's permissions

Run **`/config permissioncheck`** in your server. Banwatch replies with a
checklist (✅ / ❌) of every permission above, plus whether it can post in your
configured mod channel. **Run this first whenever something isn't working**
before contacting support.

If a permission shows ❌:

1. Go to **Server Settings → Roles → Banwatch** and enable the missing
   permission, or
2. Check **channel-level** permission overrides on your mod channel — a
   channel override can block the bot even when the role grants the permission.

## Who can configure Banwatch (user permissions)

Configuration and moderation commands are gated by Discord permissions on the
person running them:

| Command area                                                  | Permission the user needs                                          |
|---------------------------------------------------------------|--------------------------------------------------------------------|
| `/config change`, `/config appeals`, `/config visibility`     | **Manage Server**                                                  |
| `/invite` (set channel / regenerate)                          | **Manage Server**                                                  |
| `/tools ban`, `/tools mass_ban`, `/tools reban`               | **Ban Members**                                                    |
| `/tools unban`, `/tools mass_unban`                           | **Ban Members**                                                    |
| `/tools kick`                                                 | **Kick Members**                                                   |
| `/warnings warn`, `/warnings manage`, `/warnings punishments` | Moderation permissions (Kick/Ban as appropriate)                   |
| `/config permissioncheck`, `/lookup`, `/help`, `/support`     | No special permission                                              |
| `/dev ...`, `/staff ...`                                      | Bot owner / Banwatch staff only — not available to regular servers |

If you try a command without the required permission, Discord (or the bot) will
refuse it. Give yourself or your moderators the appropriate role permission to
use it.

## First-time setup checklist

1. **Invite** Banwatch with the link above and approve the requested
   permissions.
2. Run **`/config permissioncheck`** and resolve any ❌.
3. Set your mod channel: **`/config change`** → option *Mod Channel* → pick the
   channel. Banwatch will import your existing bans on first setup (expect a
   burst of messages).
4. (Optional) Enable appeals with **`/config appeals`**, set an invite channel
   with **`/invite set_channel`**, and configure warning punishments with
   **`/warnings punishments`**.
5. You're done — Banwatch runs in the background and will alert you when a
   flagged user joins.
