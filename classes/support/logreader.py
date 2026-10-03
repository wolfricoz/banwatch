"""Reads the bot's own log files (written by modules.logs) back as whole records.

A record is one log call: its timestamped first line plus any lines that follow it without a timestamp,
such as a traceback. Timestamps are the naive local time the file formatter writes.
"""
import glob
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator

LOG_GLOB = os.path.join("logs", "log.txt*")
# Matches the file formatter in modules.logs: '%(asctime)s:%(name)s:%(levelname)s: %(message)s'
RECORD_START = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+:.*?:(DEBUG|INFO|WARNING|ERROR|CRITICAL): (.*)$")


@dataclass
class LogRecord :
	time: datetime
	level: str
	message: str
	text: str  # every line of the record as written, first line included


def log_files(since: datetime) -> list[str] :
	"""The log files that can hold lines written since `since`, oldest first. A rotated file stops being
	written to when it rotates, so one last modified before `since` has nothing newer in it."""
	cutoff = since.timestamp()
	paths = []
	for path in glob.glob(LOG_GLOB) :
		try :
			if os.path.getmtime(path) >= cutoff :
				paths.append(path)
		except OSError :
			continue
	return sorted(paths, key=os.path.getmtime)


def read_records(since: datetime, paths: list[str] = None) -> Iterator[LogRecord] :
	for path in paths if paths is not None else log_files(since) :
		try :
			with open(path, encoding="utf-8", errors="replace") as file :
				record = None
				for line in file :
					match = RECORD_START.match(line.rstrip("\n"))
					if match is None :
						if record is not None :
							record.text += line
						continue
					if record is not None and record.time >= since :
						yield record
					record = LogRecord(datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S"),
					                   match.group(2), match.group(3), line)
				if record is not None and record.time >= since :
					yield record
		except OSError as e :
			logging.warning(f"Could not read log file {path}: {e}")
