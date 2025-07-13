import discord.ui

class ReasonSelect(discord.ui.Select):
    def __init__(self, reasons):
        options = [
            discord.SelectOption(
                label=reason.get('reason', "Custom")[:99],
                value=reason.get('ban_reason', "custom")[:99],
                description=reason.get('description', "")[:99],
                emoji=reason.get('emote')
            )
            for reason in reasons
        ]

        super().__init__(
            placeholder="Select your ban reason here!",
            options=options,
            min_values=1,
            max_values=1
        )

    async def callback(self, interaction: discord.Interaction):
        selected_value = self.values[0]
        self.view.reason = selected_value
        self.view.stop()

class SelectReason(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.reason = None
        self.reasons = [
	        {
		        "reason"      : "Custom",
		        "description" : "Select this to input a custom reason",
		        "ban_reason"  : "custom",
		        "emote"       : "📝"

	        },
	        {
		        "reason"      : "Harassment",
		        "description" : "Targeted bullying, threats, or repeated unwanted contact",
		        "ban_reason"  : "User engaged in targeted harassment, including threats or persistent unwanted interactions",
		        "emote"       : "🚫"
	        },
	        {
		        "reason"      : "Hate Speech",
		        "description" : "Racist, sexist, homophobic, or otherwise discriminatory language",
		        "ban_reason"  : "User used hate speech or discriminatory language based on race, gender, or identity",
		        "emote"       : "❌"
	        },
	        {
		        "reason"      : "Spam",
		        "description" : "Flooding chat or DMing users with unwanted content",
		        "ban_reason"  : "User spammed messages, links, or unsolicited content repeatedly in chat or DMs",
		        "emote"       : "📨"
	        },
	        {
		        "reason"      : "Impersonation",
		        "description" : "Pretending to be staff or another user",
		        "ban_reason"  : "User impersonated a staff member or another user to mislead others",
		        "emote"       : "🕵️"
	        },
	        {
		        "reason"      : "NSFW Content",
		        "description" : "Posting or linking sexually explicit or graphic material",
		        "ban_reason"  : "User posted or shared explicit NSFW content in violation of server guidelines",
		        "emote"       : "🔞"
	        },
	        {
		        "reason"      : "Raid",
		        "description" : "Participating in or organizing mass disruption",
		        "ban_reason"  : "User participated in or coordinated a raid to disrupt the server",
		        "emote"       : "🎯"
	        },
	        {
		        "reason"      : "Scam or Phishing",
		        "description" : "Attempting to steal information or promote scams",
		        "ban_reason"  : "User attempted to scam others or distributed phishing links to steal credentials",
		        "emote"       : "🎣"
	        },
	        {
		        "reason"      : "Malicious Links",
		        "description" : "Posting harmful or misleading URLs",
		        "ban_reason"  : "User posted harmful or deceptive links potentially containing malware or exploits",
		        "emote"       : "🔗"
	        },
	        {
		        "reason"      : "Alt Evasion",
		        "description" : "Using alternate accounts to evade bans or restrictions",
		        "ban_reason"  : "User used alternate accounts to bypass existing bans or mutes",
		        "emote"       : "👥"
	        },
	        {
		        "reason"      : "Repeated Rule Violations",
		        "description" : "User consistently broke server rules over time, despite receiving multiple warnings, mutes, or temporary bans",
		        "ban_reason"  : "User demonstrated a continued disregard for server guidelines by repeatedly violating rules even after receiving prior warnings and disciplinary actions. Their behavior showed no signs of improvement and disrupted the community",
		        "emote"       : "📜"
	        },
	        {
		        "reason"      : "Lying About Age",
		        "description" : "User provided false information about their age, violating server policies",
		        "ban_reason"  : "User was found to have lied about their age, breaching age-related server or platform rules",
		        "emote"       : "🎂"
	        },
	        {
		        "reason"      : "Trolling",
		        "description" : "User intentionally provoked or disrupted conversations for attention or chaos",
		        "ban_reason"  : "User engaged in disruptive behavior, including baiting others and derailing discussions",
		        "emote"       : "🎭"
	        },
	        {
		        "reason"      : "Doxxing",
		        "description" : "User shared or threatened to share private or identifying information",
		        "ban_reason"  : "User attempted to expose another user's personal or private information without consent",
		        "emote"       : "🕵️‍♂️"
	        },
	        {
		        "reason"      : "Unauthorized Advertising",
		        "description" : "User promoted external servers, products, or services without permission",
		        "ban_reason"  : "User advertised external content, such as Discord servers or websites, against server policy",
		        "emote"       : "📢"
	        },
	        {
		        "reason"      : "Bypassing Filters",
		        "description" : "User attempted to evade word filters, mutes, or moderation systems",
		        "ban_reason"  : "User intentionally bypassed content filters or moderation tools to post restricted content",
		        "emote"       : "🔧"
	        },
	        {
		        "reason"      : "Threats of Violence",
		        "description" : "User made or implied threats of physical harm to others",
		        "ban_reason"  : "User issued threats or language suggesting harm toward individuals or groups",
		        "emote"       : "⚠️"
	        },
	        {
		        "reason"      : "Disrespecting Staff",
		        "description" : "User repeatedly ignored or disrespected server staff instructions or authority",
		        "ban_reason"  : "User was hostile or dismissive toward staff members and refused to comply with rules",
		        "emote"       : "🛡️"
	        },
	        {
		        "reason"      : "Inappropriate Username or Profile",
		        "description" : "User used an offensive or misleading name, avatar, or status",
		        "ban_reason"  : "User's profile contained inappropriate or rule-breaking elements such as slurs or impersonation",
		        "emote"       : "👤"
	        },
	        {
		        "reason"      : "Excessive Drama",
		        "description" : "User continuously stirred conflict or created division within the community",
		        "ban_reason"  : "User caused frequent interpersonal conflicts, disrupting community peace",
		        "emote"       : "🔥"
	        },
	        {
		        "reason"      : "Ban Evasion",
		        "description" : "User returned after being banned using an alternate account",
		        "ban_reason"  : "User rejoined the server using a different account to avoid an existing ban",
		        "emote"       : "🚷"
	        },
	        {
		        "reason"      : "Plagiarism",
		        "description" : "Copying or stealing others' content without permission",
		        "ban_reason"  : "User posted content copied from others without proper credit or authorization, violating community rules",
		        "emote"       : "📋"
	        },
        ]

        self.add_item(ReasonSelect(self.reasons))