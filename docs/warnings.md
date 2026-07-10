---
layout: default
title: Warnings
nav_order: 7
---

# Warnings

Warnings let you keep track of members who break the rules without jumping
straight to a ban. You can review a member's history at any time, and — if you
want — let Banwatch act automatically once someone racks up too many.

## Giving a warning

```
/warnings warn
```

Pick the member and add a reason. The warning is saved to that member's record
so you and your team can see it later. You can attach evidence to a warning the
same way you do for bans, which keeps all your notes in one place.

## Reviewing a member's warnings

```
/warnings manage
```

This shows every warning a member has, and lets you remove any that no longer
apply (for example if they were added by mistake).

## Automatic punishments

You can tell Banwatch to take action on its own once a member reaches a certain
number of warnings. Set it up with:

```
/warnings punishments
```

There are three independent thresholds:

| Setting | What it does |
| --- | --- |
| **Timeout after X warnings** | Temporarily mutes the member once they hit X warnings. |
| **Kick after X warnings** | Removes the member from the server (they can rejoin). |
| **Ban after X warnings** | Bans the member once they reach the limit. |

You can use any combination. For example, a timeout at 3 warnings and a ban at 5
gives people a chance to correct course before the most serious action. Leave a
threshold empty and that punishment simply never fires on its own.

## Tips

- Warnings are private to your server — they aren't shared across the network
  the way bans can be.
- Keep reasons clear and factual. If a warning later leads to a ban, a good
  paper trail helps everyone understand why.
- Removing a warning does not undo a punishment that already happened; it just
  updates the member's record going forward.

## Related pages

- [Bans](bans.md) — how bans are processed and shared.
- [Evidence](evidence.md) — attaching proof to warnings and bans.
