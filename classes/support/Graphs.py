import array
import logging
import os
import typing

import numpy.typing as nptyp
import matplotlib.pyplot as plt

DIRECTORY = 'tmp/graphs/'


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

def create_pie(guild_id: int, values: list[int], labels:  list[str]):
	filename = f'{guild_id}_ban_status.png'
	plt.pie(values, labels=labels, autopct=lambda p: p.round(2), explode=calculate_explode(values))
	plt.savefig(DIRECTORY + filename)
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
