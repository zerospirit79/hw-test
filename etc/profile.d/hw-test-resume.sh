#!/bin/bash
# Resume hw-test after reboot when the test user logs in (SSH or local TTY).
# Headless resume is not started from multi-user.target before login.

case "${HW_TEST_RESUME_DONE-}:${-}" in
*1*) return 0 2>/dev/null || exit 0 ;;
*i*) ;;
*) return 0 2>/dev/null || exit 0 ;;
esac

[ -n "${HOME-}" ] || return 0 2>/dev/null || exit 0
[ -f "$HOME/HW-TEST/STATE/RESUME_ON_LOGIN" ] || return 0 2>/dev/null || exit 0
[ -f "$HOME/HW-TEST/STATE/STEP" ] || return 0 2>/dev/null || exit 0
[ -s "$HOME/HW-TEST/STATE/STEP" ] || return 0 2>/dev/null || exit 0
[ -f "$HOME/HW-TEST/hw-test.log" ] || return 0 2>/dev/null || exit 0
command -v hw-test >/dev/null 2>&1 || return 0 2>/dev/null || exit 0

uid="$(id -u 2>/dev/null)" || return 0 2>/dev/null || exit 0
run_dir="/run/user/$uid"
lock="$run_dir/hw-test-resume.lock"
if [ -f "$lock" ]; then
	return 0 2>/dev/null || exit 0
fi
mkdir -p "$run_dir" 2>/dev/null || return 0 2>/dev/null || exit 0
: >"$lock" 2>/dev/null || return 0 2>/dev/null || exit 0

export HW_TEST_RESUME_DONE=1
if [ "${LANG-}" = ru* ] || [ "${LC_MESSAGES-}" = ru* ]; then
	echo "hw-test: продолжение тестирования после перезагрузки..."
else
	echo "hw-test: resuming testing after reboot..."
fi
# Do not exec: if hw-test exits (e.g. false Esc cancel on console), keep the login shell.
hw-test --continue --no-autorun
rm -f "$lock" 2>/dev/null || true
