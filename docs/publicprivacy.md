---
layout: default
title: privacy
nav_order: 2
---

<h1 align="center">Privacy Policy</h1>

### Short Version:

All the data collected by Ban Watch is strictly used to inform other server owners of potential threats to their
servers. We do not sell or distribute any data to third parties and we do not store any Personal Identifying
Information - any and all information given is provided by discord's API. Bans are temporarily cached on the server for
24 hours to prevent spamming the discord API. If you have any questions or concerns, please contact the developers in
our support discord.

Banwatch follows all of GDPR's guidelines and regulations; especially as we do not store any personal information; the
information is provided by discord's API.

# What data do we collect?

We collect the following data from the discord API every two hours or when a ban is detected:

- User ID
- Ban reason
- Guild ID

Next to that we also collect information in our support server that is provided by the server owner:

- Proof about the ban, to ensure that the ban is legitimate
- User ID and username
- the ban reason
- the guild name, the guild owner, and the guild ID

# How do we use this data?

<b>The data we collect is used to inform other server owners of potential threats to their servers.</b>

We do not sell or
distribute any data to third parties and we do not store any Personal Identifying Information - any and all information
is provided by discord's API. Bans are temporarily cached on the server for 24 hours to prevent spamming the discord API
and to improve the start up times of the bot to ensure that the bot is always available. After 24 hours this cache is
deleted and rebuilt.

User messages are <b>not</b> stored in any way, shape, or form. the `message_content intent` is currently used for a
handful of commands to provide context about the ban, which is stored on the server under the ban entry to provide
context about the ban. It also uses this intent to search for information from a partnered bot which can provide more
context to bans. Be sure to check out the RP Security Bot!

# Consenting to the data collection

If you run one of the commands that require the `message_content` intent, you are consenting to the data being collected
and stored.
these commands are:

- `/evidence add`

# How can I request my data to be removed?

To have your data removed, you can contact the owner of the server who banned you, as they can remove the ban from their
server; banwatch will automatically remove the ban from the cache within 24 hours. As bans do not fall under personal
identifying information, we do not have to remove the data from the cache per GDPR guidelines.

Personal information is defined as any information that can be used to identify a person, such as a name, address, phone
number, email address, or IP address, credit cards, social security numbers. As we do not store any personal
information, we do not have to remove any data from the cache. If a ban may have the potential to contain personal
information, we may request the server owner to update the ban to remove the personal information.

# Q&A
* Q: Can the bot read my messages?
* A: While the bot has permission to read PUBLIC messages, it does not read them as server moderation is outside of banwatch's scope. The bot only reads messages when a command is run that requires the `message_content` intent.
* Q: Can the bot read my DMs?
* A: If you DM the bot, the bot can read your messages. The bot does not have access to your private dms with other users.
* Q: Can the bot see my IP address?
* A: No, the bot does not have access to your IP address; discord hides this information from bots.
* Q: Can the bot see my email address?
* A: No, the bot does not have access to your email address; discord hides this information from bots.
* Q: Can the bot see my credit card information?
* A: No, the bot does not have access to your credit card information; discord hides this information from bots.
* Q: How are fraudulant or misleading bans handled?
* A: If we are informed about a fraudulant/misleading ban we will investigate the claims, and if found that these claims have merrit we will hide the bans, and remove our bot from the offending server if needed.
* Q: Is Banwatch a spy bot?
* A: No, Banwatch is not a spy bot. Banwatch is a bot that helps server owners keep their servers safe by informing them of potential threats to their server.
* Q: is Banwatch verified?
* A: Yes, Banwatch is verified by discord. You can see this by the checkmark next to the bot's name. This means that discord has looked at the bot and has verified that it is safe to use.
# What if I have more questions?

If you have any questions or concerns, please contact the developers in our support discord. You can join the support
server by clicking [here](https://discord.gg/q7Ukwe2FC2).

