import array
import logging
import os
import typing
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import numpy.typing as nptyp
import matplotlib.pyplot as plt
from matplotlib.font_manager import font_family_aliases

DIRECTORY = 'tmp/graphs/'

DISCORD_DARK = '#313338'       # Main chat background
DISCORD_TEXT = '#F2F3F5'       # Off-white text
DISCORD_COLORS = [
    '#5865F2',  # Blurple
    '#23A55A',  # Green
    '#F0B232',  # Yellow
    '#F23F43',  # Red
    '#949BA4',  # Gray
]

def calculate_explode(values, wedge = 0.1):
	if len(values) <= 1:
		return [wedge]

	# Instead of highest number, using index.
	result = []
	highest = 0

	# Loop over the items.
	for index, value in enumerate(values):

		if value > values[highest]:
			highest = index

		result.append(0)

	# Now we have found the largest item, we give it the wedge.
	result[highest] = wedge

	return result


def create_pie(guild_id: int, values: list[int], labels: list[str], title="Placeholder title") :
	filtered_data = [(v, l) for v, l in zip(values, labels) if v > 0]
	if not filtered_data :
		return None
	values, labels = zip(*filtered_data)
	values = list(values)
	labels = list(labels)

	total = sum(values)
	filename = f'{guild_id}_ban_status.png'

	fig, ax = plt.subplots(figsize=(6, 6), facecolor=DISCORD_DARK)
	ax.set_facecolor(DISCORD_DARK)

	wedges, texts, autotexts = ax.pie(
		values,
		labels=labels,
		autopct=lambda p : f'{round(p * total / 100)}',
		explode=calculate_explode(values),
		colors=DISCORD_COLORS[:len(values)],  # Applies the Discord palette
		textprops={'color' : DISCORD_TEXT, 'fontsize' : 12, 'fontfamily' : 'sans-serif'},
		wedgeprops={'edgecolor' : DISCORD_DARK, 'linewidth' : 0.5}
	)


	for autotext in autotexts :
		autotext.set_weight('bold')
		autotext.set_color('#FFFFFF')

	plt.title(title, color=DISCORD_TEXT, fontsize=16, fontfamily='sans-serif', weight='bold')


	plt.tight_layout()
	plt.savefig(DIRECTORY + filename, facecolor=fig.get_facecolor(), bbox_inches='tight', dpi=150)
	plt.close()

	return DIRECTORY + filename


def create_ban_trend_chart(guild_id: int, data: dict) :
	filename = f'{guild_id}_ban_trend.png'

	# 1. Parse and sort data by date to ensure chronological order
	raw_dates = list(data.keys()) if isinstance(data, dict) else [x[0] for x in data]
	counts = list(data.values()) if isinstance(data, dict) else [x[1] for x in data]

	# Convert string dates to datetime objects for proper spacing
	parsed_dates = [d for d in raw_dates]
	sorted_pairs = sorted(zip(parsed_dates, counts))
	dates, counts = zip(*sorted_pairs)

	# 2. Setup Figure using your existing variables
	fig, ax = plt.subplots(figsize=(10, 5))
	fig.patch.set_facecolor(DISCORD_DARK)
	ax.set_facecolor(DISCORD_DARK)

	# 3. Plot the Line & Markers (Using Blurple for line, Gray for grid)
	ax.plot(dates, counts, color=DISCORD_COLORS[0], linewidth=3, marker='o', markersize=6, markerfacecolor=DISCORD_TEXT,
	        markeredgecolor=DISCORD_COLORS[0])

	# Fill area beneath line
	ax.fill_between(dates, counts, color=DISCORD_COLORS[0], alpha=0.15)

	# 4. Customizing Axes, Grid, and Labels
	ax.set_title('Ban Frequency Trend', color=DISCORD_TEXT, fontsize=14, pad=15, fontweight='bold')
	ax.set_xlabel('Date', color=DISCORD_TEXT, fontsize=11, labelpad=10)
	ax.set_ylabel('Number of Bans', color=DISCORD_TEXT, fontsize=11, labelpad=10)

	# Change tick colors
	ax.tick_params(colors=DISCORD_TEXT, labelsize=9)
	ax.grid(True, color=DISCORD_COLORS[4], linestyle='--', linewidth=0.5, alpha=0.5)

	for spine in ['top', 'right'] :
		ax.spines[spine].set_visible(False)
	for spine in ['left', 'bottom'] :
		ax.spines[spine].set_color(DISCORD_COLORS[4])
		ax.spines[spine].set_alpha(0.5)

	fig.autofmt_xdate()

	# 5. Save and Return
	plt.tight_layout()
	plt.savefig(DIRECTORY + filename, facecolor=fig.get_facecolor(), edgecolor='none', dpi=150)
	plt.close()

	return DIRECTORY + filename

def clean_pie(guild_id: int):
	try:
		filename = f'{guild_id}_ban_status.png'
		os.remove(DIRECTORY + filename)
	except FileNotFoundError:
		return True
	except Exception as e:
		logging.warning(f'Failed to clean the pie file: {e}')
	return True

def clean_trend(guild_id: int):
	try:
		filename = f'{guild_id}_ban_trend.png'
		os.remove(DIRECTORY + filename)
	except FileNotFoundError:
		return True
	except Exception as e:
		logging.warning(f'Failed to clean the pie file: {e}')
	return True