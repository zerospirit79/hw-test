%define _unpackaged_files_terminate_build 0
%define mod_name hw_test
%def_with check

Name: hw-test
Version: 2.0.0
Release: alt3
Summary: Hardware compatibility testing tool for ALT Linux
Summary(ru-RU): Инструмент тестирования оборудования для ALT Linux
Group: System/Configuration/Other
License: GPLv3+
Url: https://github.com/zerospirit79/hw-test

Source: %name-%version.tar
#Patch: %name-%version-alt.patch
BuildArch: noarch

# Python dependencies
BuildRequires(pre): rpm-build-pyproject
BuildRequires: python3(setuptools)
BuildRequires: python3(wheel)
BuildRequires: python3(black)
Requires: python3 >= 3.8
Requires: python3-module-psutil >= 5.9.0
Requires: python3-module-py-cpuinfo >= 9.0.0
Requires: python3-module-packaging >= 21.0
Requires: python3-module-pexpect >= 4.8.0

# Test dependencies
%if_with check
BuildRequires: python3(pytest)
BuildRequires: python3(pytest-cov)
BuildRequires: python3(pytest-mock)
%endif

# System tools required for hardware detection
Requires: dmidecode 
Requires: sos 
Requires: system-report 
Requires: acpica 
Requires: dmidecode 
Requires: lsscsi
Requires: lshw
Requires: inxi
Requires: pciutils
Requires: usbutils
Requires: hdparm
Requires: smartmontools
Requires: stress-ng
Requires: cpupower
Requires: sysfsutils

# Network tools
Requires: iputils
Requires: iperf3
Requires: iw
Requires: ethtool

# Firmware update (optional but recommended)
Requires: fwupd

# Graphics testing
Requires: glmark2
Requires: mesa-dri-drivers

# Audio testing
Requires: alsa-utils
Requires: pulseaudio-utils

# Disk testing
Requires: fio

# System tools
Requires: systemd-utils
Requires: jq
Requires: gzip
Requires: numactl

# GUI tools (optional, for interactive mode)
Requires: yad
Requires: xdg-utils
#Requires: paplay
Requires: notify-send

# For server/headless systems (optional)
Requires: dialog

# Video recording for express test (required for certification)
Requires: ffmpeg

# Bluetooth testing (optional)
Requires: bluez-tools

# Input testing (optional)
Requires: libinput-tools
Requires: evtest

# IPMI/BMC management (optional, for servers)
Requires: ipmitool

# Smart card support (optional)
Requires: pcsc-lite
Requires: pcsc-tools

%py3_provides %name

%description
hw-test is a comprehensive hardware compatibility testing tool for ALT Linux.
It performs automated tests on CPU, memory, disk, network, graphics, audio,
and other hardware components.

Features:
- Hardware detection and cataloging
- System preparation and update
- Performance benchmarks (CPU, disk, graphics)
- Firmware update checks
- Express tests for quick validation
- Comprehensive log collection
- Test continuation after reboot

%description -l ru_RU
hw-test — это комплексный инструмент тестирования совместимости оборудования
для ALT Linux. Он выполняет автоматизированные тесты процессора, памяти,
дисков, сети, графики, аудио и других компонентов оборудования.

Возможности:
- Определение и каталогизация оборудования (CPU, память, диски, сеть, GPU, аудио, USB, NUMA, IPMI)
- Подготовка и обновление системы
- Тесты производительности (CPU, диск, графика)
- Проверка обновлений прошивок
- Экспресс-тесты для быстрой проверки (время загрузки, отзывчивость, I/O, сеть, Wi-Fi, аудио, спящий режим, функциональные клавиши)
- Комплексный сбор журналов
- Продолжение теста после перезагрузки
- Видеозапись для сертификации
- Проверка Bluetooth, веб-камер, сканеров отпечатков, смарт-карт

%prep
%setup
%autopatch -p1

%build
%pyproject_build

%install
%pyproject_install

# Install configuration file
install -d %buildroot/etc/hw-test
install -m 644 etc/hw-test.conf.example %buildroot/etc/hw-test.conf

%post
# Create data directories if they don't exist
if [ ! -d /var/lib/hw-test ]; then
    mkdir -p %buildroot/var/lib/hw-test/logs
    chmod 755 %buildroot/var/lib/hw-test %buildroot/var/lib/hw-test/logs
fi
if [ ! -d /var/log/hw-test ]; then
    mkdir -p %buildroot/var/log/hw-test
    chmod 755 %buildroot/var/log/hw-test
fi
# Ensure proper ownership (root:root)
chown -R root:root /var/lib/hw-test /var/log/hw-test 2>/dev/null || true

# Create data directories
#install -d %buildroot/var/lib/hw-test
#chmod 755 %buildroot/var/lib/hw-test
#install -d %buildroot/var/lib/hw-test/logs
#chmod 755 %buildroot/var/lib/hw-test/logs
#install -d %buildroot/var/log/hw-test
#chmod 755 %buildroot/var/log/hw-test
#install -Dm 755 usr/share/applications/%name.desktop %buildroot%_desktopdir/

%check
%pyproject_run_pytest

%files
%doc README.md
%config(noreplace) /etc/hw-test.conf
%dir %attr(0755,root,root) %_localstatedir/%name
%dir %attr(0755,root,root) %_localstatedir/%name/logs
%dir %attr(0755,root,root) %_logdir/%name
%_bindir/%name
%_desktopdir/%name.desktop
%python3_sitelibdir/%mod_name/
%python3_sitelibdir/%{pyproject_distinfo %mod_name}/

%changelog
* Mon Mar 30 2026 Pavel Shilov <zerospirit@altlinux.org> 2.0.0-alt1
- Initial build for Sisyphus.
* Tue Mar 31 2026 Pavel Shilov <zerospirit@altlinux.org> 2.0.0-alt2
- Fixed file writing to use root privileges via su - authentication
- All log and report files now written using run_as_root() to avoid permission errors
- Application authenticates as root at startup and uses su - for privileged operations
* Tue Mar 31 2026 Pavel Shilov <zerospirit@altlinux.org> 2.0.0-alt3
- Added GUI test selection dialog with yad
- Test selection menu now shows after hardware detection with system information
- New module: test_selector_gui.py for interactive test parameter selection
* Tue Mar 31 2026 Pavel Shilov <zerospirit@altlinux.org> 2.0.0-alt4
- Fixed _run_command() return value in step_01_hardware_detection.py (now returns 3 values)
- Added missing 'os' import in step_01_hardware_detection.py
- Code formatted with black
- Fixed tests to disable pexpect mocking (tests/test_auth.py)
- All 76 tests passing
