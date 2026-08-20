---
layout: default
title: Architecture
nav_order: 19
---

# Architecture & flow diagrams
{: .no_toc }

How Banwatch is put together and how a ban travels through it. Every diagram on this page
is generated from the code it describes — file and function names are given underneath each
one so a diagram can be checked against the source rather than trusted.

<details open markdown="block">
  <summary>Table of contents</summary>
  {: .text-delta }
- TOC
{:toc}
</details>

---

## 1. System overview

Banwatch is a single Python process: a sharded discord.py bot, a FastAPI app, and a
background task queue sharing one MySQL/MariaDB database.

```mermaid
flowchart LR
    subgraph dc["Discord"]
        GW["Gateway events<br/>member ban / unban / join / update"]
        REST["Discord REST API"]
    end

    subgraph proc["Banwatch process (main.py)"]
        LIS["Listeners<br/>listeners/*.py"]
        COGS["Command cogs<br/>modules/*.py"]
        VIEWS["Buttons & views<br/>view/*.py"]
        CHK["BanChecker<br/>classes/ban/BanChecker.py"]
        BANS["Bans<br/>classes/bans.py"]
        CFG["ConfigData<br/>per-guild config cache"]
        Q["Priority queue<br/>classes/queue.py"]
        LOOPS["Task loops<br/>modules/refresher.py<br/>modules/tasks.py"]
    end

    DB[("MySQL / MariaDB<br/>SQLAlchemy + Alembic")]
    SENTRY["Sentry<br/>errors & traces"]
    API["FastAPI<br/>api.py, api/*.py"]

    GW --> LIS
    LIS --> CHK
    COGS --> CHK
    VIEWS --> CHK
    CHK --> BANS
    LOOPS --> BANS
    BANS --> Q
    Q -->|rate-limited sends| REST
    CHK <--> CFG
    BANS <--> DB
    CFG <--> DB
    API <--> DB
    proc -.-> SENTRY
```

Everything that talks to Discord in bulk goes through the priority queue
(`classes/queue.py`, priorities: 2 = high, 1 = normal, 0 = low) so a mass operation cannot
exhaust the API rate limit. `ConfigData` is a singleton cache of the `config` table, read on
nearly every path.

---

## 2. The ban flow (live ban)

This is the main path: a moderator bans someone in a server that has Banwatch, and
`listeners/on_member_ban.py` decides what happens next.

```mermaid
flowchart TD
    START(["on_member_ban<br/>guild, user"]) --> SELF{"Is the user<br/>Banwatch itself?"}
    SELF -->|yes| STOP1(["Log and stop"])
    SELF -->|no| ISBOT{"Is the user<br/>a bot?"}
    ISBOT -->|yes| STOP2(["Log and stop"])
    ISBOT -->|no| DEDUPE["Delete any earlier ban row<br/>for this user + server"]

    DEDUPE --> FETCH["Fetch the ban entry<br/>reason + user"]
    FETCH --> RESOLVE["Resolve the mod channel<br/>resolve_ban_channel"]

    RESOLVE --> HIDDEN{"Is the server<br/>hidden?"}
    HIDDEN -->|yes| REC(["Record the ban silently<br/>never broadcast"])
    HIDDEN -->|no| SHORT["BanChecker.short_run<br/>cheap string-only rules"]

    SHORT --> VERDICT{"Verdict"}
    VERDICT -->|HIDE| EVAL(["evaluate_ban<br/>store as hidden, stop"])
    VERDICT -->|anything else| PREMIUM{"Premium cross-ban<br/>enabled?"}

    PREMIUM -->|yes| MIRROR["Ban the user in the<br/>owner's other servers"]
    PREMIUM -->|no| PROMPT
    MIRROR --> NOTIFY{"Mod channel<br/>available?"}
    NOTIFY -->|yes| SUMMARY["Post the cross-ban summary"]
    NOTIFY -->|no| SKIP["Skip the summary<br/>it names the banned user"]
    SUMMARY --> PROMPT
    SKIP --> PROMPT

    PROMPT["send_review_prompt"] --> HASCH{"Usable<br/>mod channel?"}
    HASCH -->|yes| BUTTONS(["Post 'share this ban?'<br/>+ action buttons"])
    HASCH -->|no| WARN(["Warn the server in a random<br/>channel — no ban details"])
```

`listeners/on_member_ban.py`, `classes/ban/BanChecker.py:short_run`.

The pre-check is deliberately cheap: only the string-only auto-hide rules run on every ban.
The full rule set runs later, when a moderator actually presses a button.

---

## 3. Choosing where to post, and what happens when there is nowhere

Every ban message a server sees goes to its configured mod channel. When that channel is
unset, deleted, or unwritable, Banwatch warns the server in a random channel it *can* post
in, rather than failing silently.

```mermaid
flowchart TD
    A["Need to post ban information"] --> B{"Mod channel<br/>configured?"}
    B -->|no| W["problem = UNSET"]
    B -->|yes| C{"Channel still<br/>exists?"}
    C -->|no| W2["problem = UNREACHABLE"]
    C -->|yes| D{"Can the bot<br/>view + send there?"}
    D -->|no| W2
    D -->|yes| E["Send to the mod channel"]
    E --> F{"Send succeeded?"}
    F -->|yes| OK(["Done"])
    F -->|no| W2

    W --> G
    W2 --> G

    G{"Warned this guild for<br/>this source recently?"}
    G -->|yes| MUTE(["Stay quiet<br/>log only"])
    G -->|no| H["Pick a RANDOM text channel<br/>the bot can post in<br/>(never the broken one)"]
    H --> I{"Found one?"}
    I -->|yes| J(["Post the warning:<br/>what is wrong + how to fix it<br/>NO ban details"])
    I -->|no| K(["Last resort:<br/>DM the server owner"])
```

`classes/ban/ban_channel.py`.

Two rules hold this together:

- **Ban details go to the mod channel or nowhere.** The fallback channel is picked because
  it is *reachable*, not because it is private — it may well be a public channel. The
  warning therefore never names the banned user or quotes the ban reason.
- **Warnings are rate limited per guild and per source.** A server that bans ten people in
  a row is told once (`DEFAULT_COOLDOWN`, 1 hour). Background sources — the two-hourly ban
  sweep and bans arriving from other servers — use `SLOW_COOLDOWN`, once a day.

---

## 4. The BanChecker rule pipeline

`BanChecker` is the single source of truth for ban vetting; every path routes through it.
Rules run in a fixed order and the **first** rule to reach a verdict wins — `perform_action`
skips every later rule once the status is no longer `PROMPT`.

```mermaid
flowchart TD
    IN(["run()<br/>status = PROMPT"]) --> R1["check_cross_ban<br/>reason starts with 'cross-ban from …'"]
    R1 --> R2["assess_value<br/>empty / low-value / [hidden] reasons"]
    R2 --> R3["check_flagged_terms<br/>block outranks review"]
    R3 --> R4["migrated_ban<br/>reason starts with '[migrated'"]
    R4 --> R5["check_bot<br/>target is a bot account"]
    R5 --> R6["check_staff<br/>target is Banwatch staff"]
    R6 --> R7["check_word_count<br/>fewer than 4 words"]
    R7 --> R8["check_pii<br/>email / phone / date of birth"]
    R8 --> OUT(["Final status"])

    R1 -.->|HIDE| OUT
    R2 -.->|HIDE| OUT
    R3 -.->|HIDE or REVIEW| OUT
    R4 -.->|HIDE| OUT
    R5 -.->|REVIEW| OUT
    R6 -.->|REVIEW| OUT
    R7 -.->|SHORT| OUT
    R8 -.->|REVIEW| OUT
```

`classes/ban/BanChecker.py:run`. The live path calls `short_run()` instead, which runs only
the first two rules plus `migrated_ban`.

Order is load-bearing: a one-word slur must be caught by `check_flagged_terms` (HIDE) before
`check_word_count` can downgrade it to SHORT, and a cross-ban must be hidden before anything
else looks at its wording. Both are covered by `tests/test_modules/test_ban_checker.py`.

---

## 5. What each verdict does

```mermaid
flowchart LR
    subgraph verdicts["BanChecker verdict"]
        H["HIDE"]
        R["REVIEW"]
        S["SHORT"]
        P["PROMPT"]
        A["APPROVE"]
    end

    H --> H1["Stored hidden<br/>never shared, never shown"]
    R --> R1{"Bulk sweep?"}
    R1 -->|yes| R2["Stored hidden + evidence request<br/>until proof is supplied"]
    R1 -->|no| R3["Stored unapproved<br/>queued for Banwatch staff"]
    S --> S1["Stored unapproved<br/>quality review of short reasons"]
    P --> P1{"Bulk sweep?"}
    P1 -->|yes| P2["Stored approved<br/>broadcast silently"]
    P1 -->|no| P3["Ask the server:<br/>share, log, or hide?"]
    A --> A1["Stored approved<br/>broadcast silently"]
```

`classes/ban/BanChecker.py:evaluate_ban`. "Bulk sweep" is the `server_only=True` flag, set
when the periodic scan imports a server's existing bans — in that mode Banwatch never asks
the server a question it did not expect.

---

## 6. The moderator's choice

When a ban is not auto-hidden, the server's staff get four buttons. Pressing one runs the
**full** rule set (not the cheap pre-check) before anything is stored or shared.

```mermaid
flowchart TD
    B(["Ban prompt in the mod channel"]) --> CH{"Which button?"}
    CH -->|Hide Ban| HD(["Stored hidden<br/>nobody else sees it"])
    CH -->|Broadcast| FULL
    CH -->|Broadcast with proof| EV1["Collect evidence message"] --> FULL
    CH -->|Log only| FULL
    CH -->|Log with proof| EV2["Collect evidence message"] --> FULL

    FULL["BanChecker.run — full rule set"] --> V{"Verdict"}
    V -->|HIDE| DENY(["Refused: reason contains<br/>blocked content. Stored hidden."])
    V -->|REVIEW| STAFF(["Stored unapproved →<br/>Banwatch staff approval queue"])
    V -->|otherwise| STORE["Stored approved"]

    STORE --> SIL{"Log only?"}
    SIL -->|yes| DM(["DM the banned user<br/>no broadcast"])
    SIL -->|no| CAST(["Broadcast to the network"])
```

`view/buttons/banoptionbuttons.py`. "Log only" still means other servers see the ban when
the user joins them or is looked up — it only suppresses the push notification.

---

## 7. Broadcasting a ban to the network

```mermaid
sequenceDiagram
    participant S as Origin server
    participant B as Banwatch
    participant DB as Database
    participant O as Other servers
    participant U as Banned user
    participant A as Banwatch approval channel

    S->>B: Ban approved for sharing
    B->>DB: Store ban (approved)
    loop every other server
        B->>B: receive_all enabled, or user is a member?
        alt yes
            B->>O: Post ban embed in that server's mod channel
            B->>DB: Record the message id
        else no usable mod channel
            B->>O: Warn in a random channel (no ban details)
        end
    end
    B->>U: DM — you were banned, here is how to appeal
    B->>A: Post to the central approval channel
    A->>A: Open a thread: previous bans, RP-security link, evidence
```

`classes/bans.py:check_guilds`, `inform_server`, `send_to_ban_channel`, `open_thread`.

Recording the message id per server (`ban_messages`) is what makes revocation possible: when
a ban is lifted, Banwatch knows exactly which message to delete in which server.

---

## 8. The periodic sweep

Every two hours Banwatch walks every server it is in, imports bans it has not seen, and
drops bans that no longer exist.

```mermaid
flowchart TD
    T(["Every 2 hours<br/>modules/refresher.py"]) --> LOOP["For each server"]
    LOOP --> REG["Register / refresh the server row<br/>and its invite"]
    REG --> PERM{"Has ban_members?"}
    PERM -->|no| PN(["Skip + permission notice"])
    PERM -->|yes| HID{"Server hidden?"}
    HID -->|yes| SKIP(["Skip"])
    HID -->|no| CH{"Usable mod channel?"}
    CH -->|no| WARN(["Skip + warn in a random channel<br/>at most once a day"])
    CH -->|yes| SCAN["Walk the server's ban list"]

    SCAN --> KNOWN{"Already known?"}
    KNOWN -->|yes| NEXT["Next ban"]
    KNOWN -->|no| RUN["BanChecker.run + evaluate_ban<br/>server_only = true"]
    RUN --> NEXT
    NEXT --> SCAN

    SCAN --> STALE["Remove bans that are<br/>no longer in the server"]
    STALE --> GONE["Soft-delete servers<br/>Banwatch was removed from"]
    GONE --> CACHE(["Rebuild the ban cache"])
```

`classes/bans.py:update` and `check_guild_bans`. This is also the repair path: once a server
fixes its mod channel, the next sweep picks up every ban it missed in the meantime.

---

## 9. Lifting a ban

```mermaid
flowchart TD
    U(["Member unbanned in the origin server"]) --> AUD["Read the unban reason<br/>from the audit log"]
    AUD --> REV["revoke_bans"]
    REV --> MSG["For every server that received it:<br/>reply with the reason, delete the message"]
    MSG --> DEL["Soft-delete the ban row"]
    DEL --> DONE(["User no longer flagged"])
```

`listeners/on_member_unban.py`, `classes/bans.py:revoke_bans`. A soft delete
(`deleted_at`) hides the record everywhere immediately; the row is removed permanently when
the same user is banned again in that server, and by the staff purge tools.

---

## 10. Someone with a record joins a server

```mermaid
flowchart TD
    J(["Member joins"]) --> Q["Look up the member's<br/>approved, non-hidden bans"]
    Q --> ANY{"Any records?"}
    ANY -->|no| END(["Nothing happens"])
    ANY -->|yes| CH{"Mod channel set?"}
    CH -->|no| N1(["Notice: set a mod channel"])
    CH -->|yes| PUB{"More than 50 members<br/>can read that channel?"}
    PUB -->|yes| N2(["Refuse to post details<br/>— prevents public shaming"])
    PUB -->|no| SHOW(["Post the record<br/>+ lookup buttons"])
```

`listeners/on_join.py`. Banwatch never bans anyone automatically — it reports, the server
decides.

---

## 11. Appeals

```mermaid
sequenceDiagram
    participant U as Banned user
    participant B as Banwatch
    participant M as Server moderators
    participant DB as Database

    U->>B: /appeal create (server)
    B->>B: Appeals allowed? Not blacklisted? No existing appeal?
    B->>DB: Store the appeal (pending)
    B->>M: Post the appeal + buttons in the mod channel
    M->>B: Respond / change status
    B->>DB: Store the message thread
    B->>U: Deliver the response by DM
    M->>B: approved / denied
    B->>DB: Update the appeal status
```

`modules/Appeals.py`, `view/buttons/appealbuttons.py`. Appeals are per ban, and a user may
only have one open appeal per server.

---

## 12. Evidence

```mermaid
flowchart TD
    E(["Evidence submitted<br/>/evidence add or a button"]) --> STORE["Mirror the attachments into<br/>the Banwatch evidence channel"]
    STORE --> ROW["Store the text + attachment URLs<br/>against the ban"]
    ROW --> STATE{"Ban state"}
    STATE -->|hidden or unapproved| BACK(["Return it to the staff<br/>approval queue for review"])
    STATE -->|already shared| THREAD(["Add it to the ban's thread<br/>so other servers can see it"])
```

`classes/evidence.py`. Attachments are re-uploaded to a Banwatch-controlled channel so the
evidence survives the original message being deleted; the database stores URLs, not files.

---

## 13. Data model

```mermaid
erDiagram
    SERVERS ||--o{ BANS : "issues"
    SERVERS ||--o{ CONFIG : "configures"
    SERVERS ||--o{ BAN_REASONS : "defines"
    SERVERS ||--o{ BAN_MESSAGES : "received"
    SERVERS ||--o{ WARNINGS : "issues"
    BANS ||--o{ PROOF : "evidenced by"
    BANS ||--o{ APPEALS : "appealed by"
    APPEALS ||--o{ APPEAL_MSGS : "discussed in"
    WARNINGS ||--o{ WARNING_EVIDENCE : "evidenced by"

    SERVERS {
        bigint id PK "Discord guild id"
        string name
        string owner
        bigint owner_id
        int member_count
        string invite
        bool hidden
        bool active
        datetime premium
        datetime deleted_at "soft delete"
    }
    BANS {
        bigint ban_id PK "user id + guild id"
        bigint uid "banned user"
        bigint gid FK "server"
        string reason
        bigint message "broadcast message id"
        bool approved
        bool verified
        bool hidden
        string staff
        datetime edited
        string edited_by
        datetime deleted_at "soft delete"
    }
    PROOF {
        int id PK
        bigint ban_id FK
        bigint uid "submitter"
        string proof
        string attachments "JSON list of URLs"
    }
    APPEALS {
        bigint id PK
        bigint ban_id FK
        string message
        enum status "approved / pending / denied"
    }
    APPEAL_MSGS {
        bigint id PK
        bigint appeal_id FK
        bigint sender
        bigint recipient
        string message
    }
    BAN_MESSAGES {
        int id PK
        bigint server_id FK
        bigint ban_id
        bigint message_id "for revocation"
    }
    CONFIG {
        int id PK
        bigint guild FK
        string key
        string value
    }
    WARNINGS {
        bigint id PK
        bigint user_id
        bigint guild_id FK
        string reason
    }
    WARNING_EVIDENCE {
        int id PK
        bigint warning_id FK
        bigint message_id
    }
    STAFF {
        int id PK
        bigint uid
        string role
    }
    FLAGGED_TERMS {
        int id PK
        string term
        string action "block / review / countblock / countreview"
        bool regex
        bool active
    }
```

`database/current.py`. Note `ban_id = user_id + guild_id`: the ban key is derived, which is
why a user can hold only one ban record per server, and why re-banning replaces the old row.

`STAFF` and `FLAGGED_TERMS` are global tables with no server relationship — they belong to
Banwatch itself rather than to any one server.

---

## Keeping these diagrams honest

If you change the ban flow, update the diagram in the same commit. The rule ordering in
§4 and the verdict routing in §5 are both pinned by
`tests/test_modules/test_ban_checker.py`, and the fallback behaviour in §3 by
`tests/test_modules/test_ban_channel.py` — if a diagram and a test disagree, the test is
right.
