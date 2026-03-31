#!/bin/bash
### This file is covered by the GNU General Public License
### version 3 or later.
###
### Copyright (C) 2024-2026, ALT Linux Team

###############################
### DE-independent launcher ###
###############################

# Safety first
set -o errexit
set -o noglob
set -o nounset

have_kde5=
have_xfce=
have_mate=
have_gnome=

is_pkg_installed()
{
	rpm -q -- "$1" &>/dev/null
}

has_binary()
{
	type -p -- "$1" &>/dev/null
}

if is_pkg_installed gnome-shell; then
	have_gnome=1
fi

if is_pkg_installed kde || is_pkg_installed kde5 ||
   is_pkg_installed plasma6-plasma5support-common
then
	have_kde5=1
fi

if is_pkg_installed xfce4-minimal ||
   is_pkg_installed xfce4-default
then
	have_xfce=1
fi

if is_pkg_installed mate-minimal ||
   is_pkg_installed mate-default ||
   is_pkg_installed mate-window-manager
then
	have_mate=1
fi

# Terminal command
CMD="hw-test --desktop-icon"

# Try to launch in appropriate terminal
if [ -n "$have_gnome" ] && has_binary kgx; then
	exec kgx -T "HW Test" -e "$CMD"
elif [ -n "$have_kde5" ] && has_binary konsole; then
	exec konsole -T "HW Test" -e "$CMD"
elif [ -n "$have_mate" ] && has_binary mate-terminal; then
	exec mate-terminal --window -t "HW Test" -e "$CMD"
elif [ -n "$have_xfce" ] && has_binary xfce4-terminal; then
	exec xfce4-terminal -T "HW Test" -e "$CMD"
elif has_binary gnome-terminal; then
	exec gnome-terminal -t "HW Test" -e "$CMD"
elif has_binary xterm; then
	exec xterm -T "HW Test" -e "$CMD"
fi

# Fallback: just run the command
exec $CMD
