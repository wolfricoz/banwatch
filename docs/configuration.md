---
layout: default
title: Configuration
nav_order: 14
---

# Configuration reference

This page documents every configuration item defined in
`data/config/mappings.py`. These are the keys Banwatch recognizes for
**per-server configuration** — the settings a server admin sets with the
`/config`, `/invite`, `/warnings`, and `/premium` commands. Each value is stored
in the database against your server and read back through `ConfigData`.

The file defines four groups: channel settings (`Channels`), warning thresholds
(`WarningConfigs`), premium toggles (`premium_toggles`), and premium roles
(`premium_roles`).

---

## Channels

The `Channels` enum lists the channel settings Banwatch keeps for each server.
Each one maps a friendly name to the key stored in the database.

| Key                        | Stored value               | Set via                                       | Description                                                                                                                                                                                                                                    |
|----------------------------|----------------------------|-----------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `MOD_CHANNEL`              | `modchannel`               | `/config change` → *Mod Channel*              | The primary channel where Banwatch posts ban info and moderation logs. Setting it for the first time triggers an initial import of the server's existing bans, so expect a burst of messages. This is the one channel every server should set. |
| `INVITE`                   | `INVITE_CHANNEL`           | `/invite set_channel`                         | The channel used when Banwatch generates an invite back to a server a user was banned from, so staff can review context.                                                                                                                       |
| `WARNING_EVIDENCE_ARCHIVE` | `WARNING_EVIDENCE_ARCHIVE` | `/config change` → *Warning Evidence Archive* | The channel where evidence attached to warnings is stored.                                                                                                                                                                                     |
| `WARNING_LOG`              | `WARNING_LOG`              | `/config change` → *Warning Log*              | The channel where issued warnings are recorded.                                                                                                                                                                                                |

---

## Warning thresholds

The `WarningConfigs` enum defines how many warnings a member can accumulate
before an automatic punishment is applied. These are configured with
`/warnings punishments`.

| Key                | Description                                                         |
|--------------------|---------------------------------------------------------------------|
| `TIMEOUT_WARNINGS` | The warning count at which a member is automatically **timed out**. |
| `KICK_WARNINGS`    | The warning count at which a member is automatically **kicked**.    |
| `BAN_WARNINGS`     | The warning count at which a member is automatically **banned**.    |

Each threshold is independent, so you can set any combination (for example a
timeout at 3 warnings and a ban at 5). Leaving one unset simply means that
punishment is never triggered automatically.

---

## Premium toggles

`premium_toggles` defines opt-in premium features. Each is toggled with
`/premium toggle_feature`, and the text below is the confirmation prompt shown
when enabling it.

| Key           | Description                                                                                                                                                                               |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `receive_all` | Receive **every** ban made across the Banwatch network. This is high volume and will flood your server with ban notifications — the confirmation prompt warns about this before enabling. |
| `cross_ban`   | Bans made in this server are also applied to the other servers you own. Only the main server needs this enabled.                                                                          |

---

## Premium roles

`premium_roles` defines premium role-based settings, configured with the
relevant `/premium` command.

| Key         | Set via                  | Description                                                                                                                                                                                                                 |
|-------------|--------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `trap_role` | `/premium bot_trap_role` | A "bot-trap" role. Any user who is assigned this role is automatically banned. Useful for catching self-bots or bad actors that auto-grab roles. This is the one place Banwatch bans automatically, and it is fully opt-in. |

---

## Related settings not in `mappings.py`

A couple of per-server settings are handled outside this file:

- **Appeals** (`allow_appeals`) — whether users may appeal bans from your
  server. Toggled with `/config appeals`.
- **Visibility** — whether your server's bans appear in public lookups. Stored
  on the server record and toggled with `/config visibility`. Hidden bans may
  still appear in the `checkall` cache for up to 10 minutes until it refreshes.

---

*Generated for the Banwatch project.*
