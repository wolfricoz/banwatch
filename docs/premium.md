---
layout: default
title: Premium
nav_order: 8
---

# Premium features

Premium unlocks a handful of extra tools for servers that want more automation
and network reach. Everything below is optional and off until you turn it on.

## Cleanup

**Remove deleted accounts** — `/premium remove_deleted`

Discord accounts that get deleted leave behind "ghost" members and stale ban
entries. This command tidies them up, removing deleted users from your server
and your ban list in one go.

## Bot-traps

Bot-traps are designed to automatically catch bad actors and self-bots. This is
the one place Banwatch will ban someone without asking first — because you
deliberately set the trap.

**Trap button** — `/premium bot_trap_button`

Creates a button that instantly bans anyone who clicks it. Genuine members have
no reason to press it, so it's a simple way to catch curious self-bots and
rule-breakers.

**Trap role** — `/premium bot_trap_role`

Designates a role that bans anyone it's assigned to. Useful against bots that
automatically grab every role they can.

## Network features

**Receive all bans** — `/premium toggle_feature`

Turns on a firehose of *every* ban made across the entire Banwatch network. This
is a lot of notifications — Banwatch will ask you to confirm before enabling it.
Most servers don't need this; the normal join-time warnings are usually enough.

**Cross-ban** — `/premium toggle_feature`

If you run more than one server, a ban made in your main server is automatically
applied to the others you own. You only need to enable it on the main server.

## Faster moderation

**Ban presets** — `/premium ban_presets`

Save common ban reasons as presets so your team can apply consistent, ready-made
reasons in a couple of clicks instead of retyping them each time.

## Turning features on and off

Most toggles live under `/premium toggle_feature`, which walks you through
enabling or disabling each one. Bot-traps and ban presets have their own
commands listed above.

## Related pages

- [Full command reference](commands/Premium.md)
- [Bans](bans.md) — how sharing and verification work.
