---
layout: default
title: privacy
nav_order: 6
---

# Privacy Policy

Last updated: 22-10-2025

## Introduction

This privacy policy outlines how Ban Watch (“we,” “our,” or “us”) collects, uses, and protects your (the end user) personal data when you interact with the Ban Watch bot. By using Ban Watch, you agree to the terms and conditions of this policy.

References in this document may refer to servers as guilds, as that is the terminology used within Discord's API.

## Short Version

All the data collected by Ban Watch is strictly used to inform other server owners of potential threats to their servers. We do not sell or distribute any data to third parties. Any data we collect is provided by Discord's API and may be stored long-term to improve the bot’s functionality. If you have any questions or concerns, please contact us in our support Discord.

Banwatch complies with all GDPR guidelines and regulations, particularly as we do not store any personal identifying information (PII) beyond Discord-provided data.

## What Data Do We Collect?

We collect the following data, categorized by the primary database tables:

### Bans

- Ban ID  
- User ID of the banned user  
- Guild ID where the ban was issued  
- Ban reason  
- Related message ID (if applicable)  
- Approval and verification status of the ban  
- Visibility status (hidden or not)  
- Date the ban was created  
- Staff notes (added by the server owner or moderators)  
- Proof associated with the ban (details stored in the Proof table)  
- Appeal records (stored in the Appeals table)  
- Deletion date (if the ban is marked as removed)  

### Staff

- User ID of staff members  
- Role or title of staff members  

### Proof

- Proof ID (unique identifier)  
- Ban ID (linked to the Bans table)  
- User ID of the person submitting the proof  
- Proof description (details or evidence supporting the ban)  
- Attachments, such as images or other files relevant to the proof  

### Servers

- Server ID (Guild ID)  
- Owner's information (username or ID)  
- Server name and member count  
- Server visibility status (hidden or not)  
- Invite link (if provided)  
- Last updated timestamp  
- Deletion timestamp (if the server entry is marked as removed)  

### Appeals

- Appeal ID  
- Ban ID (linked to the Bans table)  
- Appeal message submitted by the user  
- Appeal status (approved, pending, or denied)  

## How Do We Use This Data?

The data we collect from Discord through Ban Watch is used solely to inform other server owners of potential threats to their servers.

We do not sell or distribute data to third parties. Ban information is stored long-term in our database to ensure consistency, efficiency, and improved access for server owners. This data is kept secure and used only within the scope of Banwatch's purpose.

User messages are not stored. The `message_content` intent is used for a few commands that provide context about bans, with relevant information stored only within the corresponding ban entry to assist with ban verification.

## Consenting to the Data Collection

By running specific commands that require the `message_content` intent, you consent to data collection and storage. These commands include:

- `/evidence add`

## How Can I Request My Data to Be Removed?

If you would like data about you to be removed, please contact the server owner who issued the ban. Banwatch automatically removes the corresponding record once the original ban is deleted from that server.

Banwatch processes limited information, such as Discord user IDs and ban details, for the purpose of maintaining safer online communities. This processing is based on legitimate interests under Article 6(1)(f) of the GDPR — specifically, the interest of Discord communities in preventing disruptive or harmful behavior and supporting effective moderation.

Banwatch only stores the minimum data necessary to serve this purpose. If any additional personal data (for example, screenshots or text containing personally identifiable information) is included as evidence, Banwatch administrators will request that the submitting server re-submit the evidence with such data redacted.

If you believe Banwatch has been misused — for example, if a ban contains false, misleading, or defamatory information — you may contact the Banwatch Administrators to have the report reviewed or hidden. You can do this by joining our support server. Banwatch verifies most bans with serious reasons to reduce the risk of misuse.

## Q&A

**Q: Can the bot read my messages?**  
A: While the bot has permission to read PUBLIC messages, it does not read them as server moderation is outside of Banwatch's scope. The bot only reads messages when a command is run that requires the `message_content` intent.

**Q: Can the bot read my DMs?**  
A: If you DM the bot, the bot can read your messages. The bot does not have access to your private DMs with other users.

**Q: Can the bot see my IP address?**  
A: No, the bot does not have access to your IP address; Discord hides this information from bots.

**Q: Can the bot see my email address?**  
A: No, the bot does not have access to your email address; Discord hides this information from bots.

**Q: Can the bot see my credit card information?**  
A: No, the bot does not have access to your credit card information; Discord hides this information from bots.

**Q: How are fraudulent or misleading bans handled?**  
A: If we are informed about a fraudulent/misleading ban, the administration team will investigate the claims. If these claims are determined to lack merit, we will hide the bans, and take actions against the offending server as deemed required, up to and including removing the Ban Watch bot from that server.

**Q: Is Ban Watch a spy bot?**  
A: No, Ban Watch is not a spy bot. Ban Watch is a bot that helps server owners keep their servers safe by informing them of potential threats to their server.

**Q: Is Ban Watch verified?**  
A: Yes, Ban Watch is verified by Discord. You can see this by the checkmark next to the bot's name. This means that Discord has looked at the bot and has verified that it is safe to use.

## What If I Have More Questions?

If you have any questions or concerns, please contact the developers in our support Discord. You can join the support server by clicking the link on the bot's profile
