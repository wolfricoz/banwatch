---
layout: default
title: Glossary
nav_order: 13
---

# Glossary

Plain-language definitions of the terms you'll see around Banwatch.

**Banwatch network** — The collection of all servers using Banwatch. When you
share a ban, it becomes visible to the rest of the network so other communities
can make informed decisions.

**Network ban** — A ban that has been shared to the network. Other servers can
see it when they look up the user or when that user joins their server.

**Mod channel** — The channel you pick for Banwatch to post ban information and
alerts. Set it with `/config change` → *Mod Channel*. This is the one setting
every server should configure.

**Lookup** — Checking a user's ban history with `/lookup`. You can search by the
user or by a ban ID.

**Checkall** — Scanning every current member of your server against the global
ban database with `/checkall`.

**Checkall cache** — A short-lived copy of ban data used to make `/checkall`
fast. It refreshes about every 10 minutes, which is why a newly hidden ban can
briefly still appear.

**Verified ban** — A ban that Banwatch staff have reviewed and confirmed as
legitimate, backed by evidence. Verification helps other servers trust the
record.

**Hidden ban** — A ban that is not broadcast and can't be seen by regular users.
Bans with no reason, a `[hidden]` tag, or insufficient proof end up hidden. Only
Banwatch staff can see them.

**Silent ban** — A ban that isn't broadcast to other servers, but is still shown
to staff when the user joins a server that uses Banwatch. Add the `[silent]` tag
to a ban message to make it silent.

**Evidence / proof** — Text, screenshots, or files attached to a ban or warning
that explain what happened. See [Evidence](evidence.md).

**Evidence archive** — The channel where warning evidence is stored, set through
`/config change`.

**Appeal** — A banned user's request to have a ban reconsidered. Servers choose
whether to allow appeals with `/config appeals`. See [Appeals](appeals.md).

**Bot-trap** — A premium feature (a button or a role) that automatically bans
anyone who triggers it, used to catch self-bots and bad actors.

**Cross-ban** — A premium feature that copies a ban from your main server to the
other servers you own.

**Sensitive / flagged word** — A word in a ban reason that triggers extra review
by Banwatch staff, to prevent harmful rumors from spreading without proof. The
list is kept private on purpose.

**Visibility** — Whether your server's bans show up in public lookups. Toggle it
with `/config visibility`.

**Support server** — The Discord server where you can get help, report issues,
and appeal decisions. Reach it with `/support`.
