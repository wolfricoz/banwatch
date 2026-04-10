import logging

import discord.ui

from database.transactions.BanReasonTransactions import BanReasonsTransactions
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
				"reason"      : "Compromised Account / Bot",
				"description" : "Compromised or hacked account activity",
				"ban_reason"  : "Member's account has been compromised or hacked and is actively dming users or spamming chats with phishing links or malicious content.",
				"emote"       : "🤖"
			},
			{
				"reason"      : "Plagiarism",
				"description" : "Copying or stealing others' content without permission",
				"ban_reason"  : "Member posted content copied from others without proper credit, authorization, or attribution, violating community rules and/or intellectual property standards.",
				"emote"       : "📋"
			},
			{
				"reason"      : "Lying About Age",
				"description" : "Member provided false information about their age, violating server policies",
				"ban_reason"  : "Member provided inaccurate or false information regarding their age, violating server or platform policies.",
				"emote"       : "🎂"
			},
			{
				"reason"      : "Inappropriate Username or Profile",
				"description" : "Member used an offensive or misleading name, avatar, or status",
				"ban_reason"  : "Member’s profile, including username, avatar, or status, contained offensive, inappropriate, or misleading content such as slurs, explicit material, or impersonation.",
				"emote"       : "👤"
			},
			{
				"reason"      : "Intentional Disruption",
				"description" : "Member displayed hostility or disruptive behaviour",
				"ban_reason"  : "Member displayed hostility or behaved in a disruptive way towards staff and other servers members with the intention of inciting conflict or creating division in the community.",
				"emote"       : "🛡️"
			},
			{
				"reason"      : "Unauthorized Advertising",
				"description" : "Member promoted external servers, products, or services without permission",
				"ban_reason"  : "Member promoted external content, services, or communities without explicit authorization, violating server rules.",
				"emote"       : "📢"
			},
			{
				"reason"      : "Spam",
				"description" : "Flooding chat or DMing users with unwanted content",
				"ban_reason"  : "Member repeatedly sent unsolicited messages, links, or content in server chats or direct messages.",
				"emote"       : "📨"
			},
			{
				"reason"      : "Bypassing Filters",
				"description" : "Member attempted to evade word filters, mutes, or moderation systems",
				"ban_reason"  : "Member intentionally circumvented content filters, mutes, or moderation systems to post restricted or prohibited content.",
				"emote"       : "🔧"
			},
			{
				"reason"      : "Ban Evasion",
				"description" : "Member returned after being banned using an alternate account",
				"ban_reason"  : "Member rejoined the server using a different account to avoid an existing ban, circumventing moderation and ignoring prior disciplinary actions. ",
				"emote"       : "🚷"
			},
			{
				"reason"      : "Repeated Rule Violations",
				"description" : "Member repeatedly violated server rules, despite receiving warnings and/or other disciplinary action from staff",
				"ban_reason"  : "Member repeatedly violated server rules, despite receiving warnings and/or other disciplinary action from staff.",
				"emote"       : "📜"
			},
			{
				"reason"      : "Harassment",
				"description" : "[Evidence required] Targeted bullying or repeated unwanted contact",
				"ban_reason"  : "Member repeatedly contacted other members with unwanted behaviour, messages or content causing discomfort or distress, disregarding requests, warnings or disciplinary actions to stop",
				"emote"       : "🚫"
			},
			{
				"reason"      : "Impersonation",
				"description" : "Pretending to be staff or another user",
				"ban_reason"  : "Member impersonated a staff member or another member with the intent to deceive, mislead, or manipulate others. This behavior undermines trust in the community, violates server rules, and is considered a serious breach of conduct.",
				"emote"       : "🕵️"
			},
			{
				"reason"      : "NSFW Content",
				"description" : "Posting or linking sexually explicit, graphic, or disturbing material",
				"ban_reason"  : "Member posted or shared sexually explicit, graphic, or otherwise disturbing content outside of designated NSFW channels, violating server guidelines.",
				"emote"       : "🔞"
			},
			{
				"reason"      : "Raid",
				"description" : "Participating in or organizing mass disruption",
				"ban_reason"  : "Member participated in or coordinated a raid, including mass messaging, flooding, or targeted disruption, intended to disturb or damage the community.",
				"emote"       : "🎯"
			},
			{
				"reason"      : "Hate Speech",
				"description" : "[Evidence required] Racist, sexist, homophobic, or otherwise discriminatory language",
				"ban_reason"  : "Member engaged in hate speech or used discriminatory language targeting individuals or groups based on race, ethnicity, gender, sexual orientation, religion, or other protected characteristics.",
				"emote"       : "❌"
			},
			{
				"reason"      : "Doxxing",
				"description" : "[Evidence required] Member shared or threatened to share private or identifying information",
				"ban_reason"  : "Member threatened or attempted to expose or share private, sensitive, or personally identifying information of others without consent.",
				"emote"       : "🕵️‍♂️"
			},
			{
				"reason"      : "Threats / Violence",
				"description" : "[Evidence required] Direct threats, intimidation, or indications of potential physical harm",
				"ban_reason"  : "Member made threats, exhibited intimidating behavior, or suggested potential physical or psychological harm toward others, creating a risk to the safety and well-being of the community. ",
				"emote"       : "⚠️"
			},
			{
				"reason"      : "Severe TOS Violation",
				"description" : "This account was removed due to a significant breach of Discord\’s Terms of Service. Details are not retained or disclosed. ",
				"ban_reason"  : "This account was removed due to a significant breach of Discord’s Terms of Service. Details are not retained or disclosed, please reach out to the server for more information.",
				"emote"       : "🚨"
			}
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



