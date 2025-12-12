import logging

import discord.ui

from database.databaseController import BanReasonsTransactions
from view.base.secureview import SecureView


class ReasonSelect(discord.ui.Select) :
	def __init__(self, reasons) :
		options = [
			discord.SelectOption(
				label=reason.get('reason', "Custom")[:99],
				value=reason.get('reason', "custom")[:99],
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

	async def callback(self, interaction: discord.Interaction) :
		selected_value = self.values[0]
		self.view.reason = selected_value
		self.view.interaction = interaction
		self.view.stop()


class SelectReason(SecureView) :
	def __init__(self) :
		super().__init__(timeout=None)
		self.reason = None
		self.interaction = None
		self.current_page = 0
		banreasons = BanReasonsTransactions().get_all()



		self.reasons = [
			{
				"reason"      : "Custom",
				"description" : "Select this to input a custom reason",
				"ban_reason"  : "custom",
				"emote"       : "📝"

			},
			{
				"reason"      : "Harassment",
				"description" : "Targeted bullying or repeated unwanted contact",
				"ban_reason"  : "User engaged in harassment, including repeated unwanted messages, interactions, or behavior directed at another member that caused discomfort or distress, violating community guidelines and expectations for respectful conduct.",
				"emote"       : "🚫"
			},
			{
				"reason"      : "Threats / Violence",
				"description" : "Direct threats, intimidation, or indications of potential physical harm",
				"ban_reason"  : "User made threats, exhibited intimidating behavior, or suggested potential physical or psychological harm toward others, creating a risk to the safety and well-being of the community. Such behavior violates server rules and is not tolerated.",
				"emote"       : "⚠️"
			},
			{
				"reason"      : "Hate Speech",
				"description" : "Racist, sexist, homophobic, or otherwise discriminatory language",
				"ban_reason"  : "User engaged in hate speech or used discriminatory language targeting individuals or groups based on race, ethnicity, gender, sexual orientation, religion, or other protected characteristics. This behavior violates community standards, creates a hostile environment, and is strictly prohibited to maintain safety and inclusivity.",
				"emote"       : "❌"
			},
			{
				"reason"      : "Spam",
				"description" : "Flooding chat or DMing users with unwanted content",
				"ban_reason"  : "User repeatedly sent unsolicited messages, links, or content in server chats or direct messages, causing disruption and violating community guidelines. Such behavior interferes with normal communication and the overall user experience, warranting moderation action.",
				"emote"       : "📨"
			},
			{
				"reason"      : "Impersonation",
				"description" : "Pretending to be staff or another user",
				"ban_reason"  : "User impersonated a staff member or another member with the intent to deceive, mislead, or manipulate others. This behavior undermines trust in the community, violates server rules, and is considered a serious breach of conduct.",
				"emote"       : "🕵️"
			},
			{
				"reason"      : "NSFW Content",
				"description" : "Posting or linking sexually explicit, graphic, or disturbing material",
				"ban_reason"  : "User posted or shared sexually explicit, graphic, or otherwise disturbing content outside of designated NSFW channels, violating server guidelines. This behavior exposes members to inappropriate material, disrupts the community environment, and is strictly prohibited to maintain safety and comfort.",
				"emote"       : "🔞"
			},
			{
				"reason"      : "Raid",
				"description" : "Participating in or organizing mass disruption",
				"ban_reason"  : "User participated in or coordinated a raid, including mass messaging, flooding, or targeted disruption, intended to disturb or damage the community. Such actions breach server rules and can negatively affect the server's stability and user experience.",
				"emote"       : "🎯"
			},
			{
				"reason"      : "Scam or Phishing",
				"description" : "Attempting to steal information or promote scams",
				"ban_reason"  : "User attempted to defraud or deceive members through scams, phishing links, or malicious requests for sensitive information. This behavior violates community rules, endangers members' security, and may indicate compromised or malicious intent.",
				"emote"       : "🎣"
			},
			{
				"reason"      : "Malicious Links",
				"description" : "Posting harmful or misleading URLs",
				"ban_reason"  : "User shared links that were harmful, deceptive, or potentially contained malware or exploits, putting members' devices and data at risk. Posting such content violates server rules and can compromise the safety and security of the community.",
				"emote"       : "🔗"
			},
			{
				"reason"      : "Alt Evasion",
				"description" : "Using alternate accounts to evade bans or restrictions",
				"ban_reason"  : "User attempted to bypass existing bans, mutes, or restrictions by using alternate accounts. This behavior undermines moderation efforts, violates server rules, and demonstrates a deliberate attempt to avoid accountability within the community.",
				"emote"       : "👥"
			},
			{
				"reason"      : "Repeated Rule Violations",
				"description" : "User consistently broke server rules over time, despite receiving multiple warnings, mutes, or temporary bans",
				"ban_reason"  : "User demonstrated a persistent disregard for server rules by repeatedly violating guidelines despite prior warnings or disciplinary actions. Their ongoing behavior disrupted the community, interfered with normal interactions, and showed no signs of compliance or improvement.",
				"emote"       : "📜"
			},
			{
				"reason"      : "Lying About Age",
				"description" : "User provided false information about their age, violating server policies",
				"ban_reason"  : "User provided inaccurate or false information regarding their age, violating server or platform policies. This behavior can lead to exposure to inappropriate content and breaches age-related rules designed to protect the community.",
				"emote"       : "🎂"
			},
			{
				"reason"      : "Trolling",
				"description" : "User intentionally provoked or disrupted conversations for attention or chaos",
				"ban_reason"  : "User engaged in disruptive behavior intended to provoke, derail discussions, or incite conflict among members. Such actions interfere with community harmony, violate server guidelines, and diminish the quality of discussions.",
				"emote"       : "🎭"
			},
			{
				"reason"      : "Doxxing",
				"description" : "User shared or threatened to share private or identifying information",
				"ban_reason"  : "User attempted to expose or share private, sensitive, or personally identifying information of others without consent. This behavior endangers members’ privacy and safety and is strictly prohibited by server rules.",
				"emote"       : "🕵️‍♂️"
			},
			{
				"reason"      : "Unauthorized Advertising",
				"description" : "User promoted external servers, products, or services without permission",
				"ban_reason"  : "User promoted external content, services, or communities without explicit authorization, violating server rules. Unauthorized advertising can disrupt discussions, annoy members, and undermine the integrity of the community environment.",
				"emote"       : "📢"
			},
			{
				"reason"      : "Bypassing Filters",
				"description" : "User attempted to evade word filters, mutes, or moderation systems",
				"ban_reason"  : "User intentionally circumvented content filters, mutes, or moderation systems to post restricted or prohibited content. This behavior undermines moderation efforts and violates server rules, threatening the community’s safety and order.",
				"emote"       : "🔧"
			},
			{
				"reason"      : "Disrespecting Staff",
				"description" : "User repeatedly ignored or disrespected server staff instructions or authority",
				"ban_reason"  : "User displayed hostility, dismissiveness, or noncompliance toward server staff, repeatedly ignoring instructions or attempting to undermine authority. Such behavior disrupts moderation processes and negatively affects community management.",
				"emote"       : "🛡️"
			},
			{
				"reason"      : "Inappropriate Username or Profile",
				"description" : "User used an offensive or misleading name, avatar, or status",
				"ban_reason"  : "User’s profile, including username, avatar, or status, contained offensive, inappropriate, or misleading content such as slurs, explicit material, or impersonation. This behavior violates community standards and creates an unsafe or disruptive environment.",
				"emote"       : "👤"
			},
			{
				"reason"      : "Excessive Drama",
				"description" : "User continuously stirred conflict or created division within the community",
				"ban_reason"  : "User repeatedly instigated interpersonal conflicts, gossip, or disruptive behavior, creating division and tension within the community. Such actions violate server rules and interfere with normal interactions among members.",
				"emote"       : "🔥"
			},
			{
				"reason"      : "Ban Evasion",
				"description" : "User returned after being banned using an alternate account",
				"ban_reason"  : "User rejoined the server using a different account to avoid an existing ban, circumventing moderation and ignoring prior disciplinary actions. This behavior undermines server rules and demonstrates deliberate evasion of accountability.",
				"emote"       : "🚷"
			},
			{
				"reason"      : "Plagiarism",
				"description" : "Copying or stealing others' content without permission",
				"ban_reason"  : "User posted content copied from others without proper credit, authorization, or attribution, violating community rules and intellectual property standards. This behavior diminishes trust and disrupts the integrity of the server’s content.",
				"emote"       : "📋"
			},
		]
		self.custom_reasons = [{
			"reason"      : reason.name,
			"description" : reason.description,
			"ban_reason"  : reason.reason,
			"emote"       : '⚙️'
		} for reason in banreasons]

		self._remove_duplicates()


		self.all_reasons = self.custom_reasons + self.reasons

		self.items_per_page = 25
		self.total_pages = (len(self.all_reasons) + self.items_per_page - 1) // self.items_per_page

		self._update_page()

	def _update_page(self) :
		# Clear existing items
		self.clear_items()

		# Calculate slice for current page
		start = self.current_page * self.items_per_page
		end = start + self.items_per_page
		page_reasons = self.all_reasons[start :end]

		# Add select menu (row 0)
		select = ReasonSelect(page_reasons)
		self.add_item(select)

		# Add navigation buttons if multiple pages (row 1)

		logging.info(f"Total pages: {self.total_pages}, Current page: {self.current_page}")

		if self.total_pages > 1 :


			# Previous button
			prev_button = discord.ui.Button(
				label="◀ Previous",
				style=discord.ButtonStyle.primary,
				disabled=(self.current_page == 0),
				row=1  # Add this
			)
			prev_button.callback = self._previous_page
			self.add_item(prev_button)

			# Page indicator
			page_button = discord.ui.Button(
				label=f"Page {self.current_page + 1}/{self.total_pages}",
				style=discord.ButtonStyle.secondary,
				disabled=True,
				row=1  # Add this
			)
			self.add_item(page_button)

			# Next button
			next_button = discord.ui.Button(
				label="Next ▶",
				style=discord.ButtonStyle.primary,
				disabled=(self.current_page >= self.total_pages - 1),
				row=1  # Add this
			)
			next_button.callback = self._next_page
			self.add_item(next_button)

	async def _previous_page(self, interaction: discord.Interaction) :
		self.current_page = max(0, self.current_page - 1)
		self._update_page()
		await interaction.response.edit_message(view=self)

	async def _next_page(self, interaction: discord.Interaction) :
		self.current_page = min(self.total_pages - 1, self.current_page + 1)
		self._update_page()
		await interaction.response.edit_message(view=self)

	def _remove_duplicates(self):
		default_names = [reason['reason'].lower() for reason in self.reasons]
		custom_names = [reason['reason'].lower() for reason in self.custom_reasons]
		for custom_name in custom_names :
			if custom_name in default_names :
				index = default_names.index(custom_name)
				self.reasons.pop(index)

	def get_reason(self) :
		for reason in self.all_reasons :
			if reason.get('reason', "custom").lower() == self.reason.lower() :
				return reason.get('ban_reason')
		return "custom"



