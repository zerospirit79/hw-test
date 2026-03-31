#!/bin/bash
### This file is covered by the GNU General Public License
### version 3 or later.
###
### Copyright (C) 2024-2026, ALT Linux Team

################################################
### hw-test autorun script to resume testing ###
################################################

# Safety first
set -o errexit
set -o noglob
set -o nounset

# Executable file name
readonly progname="hw-test"

# Last working directory
readonly lastdir="$HOME/HW-TEST"

# The desktop file for hw-test autorun
readonly desktopfile="$HOME/.config/autostart/$progname.desktop"

# The command to be executed
readonly cmd="$progname --desktop-icon --continue"

# Checking files of the last testing
if [ ! -L "$lastdir" ] || [ -z "${DISPLAY-}" ] ||
   [ ! -s "$lastdir/$progname.log" ] || [ ! -s "$lastdir"/STATE/STEP ] ||
   [ ! -f "$lastdir"/STATE/start.txt ] || [ ! -s "$lastdir"/STATE/settings.ini ]
then
	exec rm -f -- "$desktopfile"
	exit 1
fi

# Reading system settings
. "$lastdir"/STATE/settings.ini

# Let the window manager finish loading the desktop first
if [ -n "${have_gnome-}" ] && type -p kgx >/dev/null; then
	sleep 5 && exec kgx -T "HW Test" -e "$cmd"
elif [ -n "${have_kde5-}" ] && type -p konsole >/dev/null; then
	sleep 5 && exec konsole -T "HW Test" -e "$cmd"
elif [ -n "${have_mate-}" ] && type -p mate-terminal >/dev/null; then
	sleep 5 && exec mate-terminal --window -t "HW Test" -e "$cmd"
elif [ -n "${have_xfce-}" ] && type -p xfce4-terminal >/dev/null; then
	sleep 5 && exec xfce4-terminal -T "HW Test" -e "$cmd"
elif type -p gnome-terminal >/dev/null; then
	sleep 5 && exec gnome-terminal -t "HW Test" -e "$cmd"
else
	exec rm -f -- "$desktopfile"
fi

exit 1
