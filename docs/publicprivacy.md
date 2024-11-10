---
layout: default
title: privacy
nav_order: 2
---

<h1 align="center">Privacy Policy</h1>

### Short Version:

All the data collected by Ban Watch is strictly used to inform other server owners of potential threats to their
servers. We do not sell or distribute any data to third parties. Any data we collect is provided by Discord's API and
may now be stored long-term to improve the bot’s functionality. If you have any questions or concerns, please contact
the developers in our support Discord.

Banwatch complies with all GDPR guidelines and regulations, particularly as we do not store any personal identifying
information (PII) beyond Discord-provided data.

# What data do we collect?

We collect the following data, categorized by the primary database tables:

* Bans:
    * Ban ID
    * User ID of the banned user
    * Guild ID where the ban was issued
    * Ban reason
    * Related message ID (if applicable)
    * Approval and verification status of the ban
    * Visibility status (hidden or not)
    * Date the ban was created
    * Staff notes (added by the server owner or moderators)
    * Proof associated with the ban (details stored in the Proof table)
    * Appeal records (stored in the Appeals table)
    * Deletion date (if the ban is marked as removed)

* Staff:
    * User ID of staff members
    * Role or title of staff members

* Proof:
    * Proof ID (unique identifier)
    * Ban ID (linked to the Bans table)
    * User ID of the person submitting the proof
    * Proof description (details or evidence supporting the ban)
    * Attachments, such as images or other files relevant to the proof

* Servers:
    * Server ID (Guild ID)
    * Owner's information (username or ID)
    * Server name and member count
    * Server visibility status (hidden or not)
    * Invite link (if provided)
    * Last updated timestamp
    * Deletion timestamp (if the server entry is marked as removed)

* Appeals:
    * Appeal ID
    * Ban ID (linked to the Bans table)
    * Appeal message submitted by the user
    * Appeal status (approved, pending, or denied)

# How do we use this data?

<b>The data we collect is used solely to inform other server owners of potential threats to their servers.</b>

We do not sell or distribute data to third parties. Ban information is stored long-term in our database to ensure consistency, efficiency, and improved access for server owners. This data is kept secure and used only within the scope of Banwatch's purpose.

User messages are <b>not</b> stored. The `message_content` intent is used for a few commands that provide context about bans, with relevant information stored only within the corresponding ban entry to assist with ban verification.

# Consenting to the data collection

By running specific commands that require the message_content intent, you consent to data collection and storage. These commands include:

- /evidence add

# How can I request my data to be removed?

To remove your data, contact the server owner who issued the ban. Banwatch will automatically remove the ban from its database if the server removes it. As bans do not include PII, GDPR does not require us to delete this data. If personal data is present in a ban, we may ask the server owner to redact it.

If harmful rumors are being spread through banwatch without evidence to substantiate it, you may contact the banwatch staff team to have this ban message hidden from servers. We verify most bans with serious reasons to prevent harmful rumors.

# Q&A

* Q: Can the bot read my messages?
  * A: While the bot has permission to read PUBLIC messages, it does not read them as server moderation is outside of
  banwatch's scope. The bot only reads messages when a command is run that requires the `message_content` intent.
* Q: Can the bot read my DMs?
  * A: If you DM the bot, the bot can read your messages. The bot does not have access to your private dms with other
    users.
* Q: Can the bot see my IP address?
  * A: No, the bot does not have access to your IP address; discord hides this information from bots.
* Q: Can the bot see my email address?
  * A: No, the bot does not have access to your email address; discord hides this information from bots.
* Q: Can the bot see my credit card information?
  * A: No, the bot does not have access to your credit card information; discord hides this information from bots.
* Q: How are fraudulant or misleading bans handled?
  * A: If we are informed about a fraudulant/misleading ban we will investigate the claims, and if found that these claims
    have merrit we will hide the bans, and remove our bot from the offending server if needed.
* Q: Is Banwatch a spy bot?
  * A: No, Banwatch is not a spy bot. Banwatch is a bot that helps server owners keep their servers safe by informing them
    of potential threats to their server.
* Q: is Banwatch verified?
  * A: Yes, Banwatch is verified by discord. You can see this by the checkmark next to the bot's name. This means that
    discord has looked at the bot and has verified that it is safe to use.

# What if I have more questions?

If you have any questions or concerns, please contact the developers in our support discord. You can join the support
server by clicking [here](https://discord.gg/q7Ukwe2FC2).

