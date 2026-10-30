#!/bin/sh
# Transcribe each finished recorder session into a campaign checkout and push it
# on its own branch, session/<day>, for the GM (or a debrief agent) to review.
# Run it from cron on the machine with the recordings; it skips sessions still
# recording (no info.json) and those already done (.transcribed).
#   transcribe-new.sh <recordings dir> <campaign checkout>
# TTRPG overrides the tools command (default: the campaign's tools/bin/ttrpg).
set -eu
recordings=$(cd "${1:?recordings directory}" && pwd)
campaign=${2:?campaign checkout}
ttrpg=${TTRPG:-tools/bin/ttrpg}
cd "$campaign"
for dir in "$recordings"/*/; do
	dir=${dir%/}
	[ -f "$dir/info.json" ] && [ ! -e "$dir/.transcribed" ] || continue
	day=$(basename "$dir" | cut -c1-10)
	# ponytail: a second recording the same day (bot restarted mid-session) replaces the first transcript; merge both dirs if that happens.
	git fetch -q origin
	git checkout -q -B "session/$day" origin/main
	git submodule update -q --init tools
	"$ttrpg" transcribe "$dir" --day "$day"
	git add "sessions/$day"
	git commit -q -m "Transcript of the $day session"
	git push -q origin "session/$day"
	touch "$dir/.transcribed"
	echo "pushed session/$day"
done
