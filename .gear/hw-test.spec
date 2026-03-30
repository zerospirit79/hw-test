%define _unpackaged_files_terminate_build 0

Name: hw-test
Version: 2.0.0
Release: alt1
Summary: Hardware compatibility testing tool for ALT Linux
Summary(ru-RU): Инструмент тестирования оборудования для ALT Linux
Group: System/Configuration/Other
License: GPLv3+
Url: https://github.com/zerospirit79/hw-test

Source: %name-%version.tar
Patch: %name-%version-alt.patch
BuildArch: noarch

# Python dependencies
BuildRequires(pre): rpm-build-pyproject
BuildRequires: python3(setuptools)
BuildRequires: python3(wheel)
Requires: python3 >= 3.8
Requires: python3-module-psutil >= 5.9.0
Requires: python3-module-py-cpuinfo >= 9.0.0
Requires: python3-module-packaging >= 21.0

# System tools required for hardware detection
Requires: dmidecode
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

# GUI tools (optional, for interactive mode)
Requires: yad
Requires: xdg-utils
Requires: paplay
Requires: libnotify-tools

# For server/headless systems (optional)
Requires: dialog

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
- Определение и каталогизация оборудования
- Подготовка и обновление системы
- Тесты производительности (CPU, диск, графика)
- Проверка обновлений прошивок
- Экспресс-тесты для быстрой проверки
- Комплексный сбор журналов
- Продолжение теста после перезагрузки

%prep
%setup -q
%autopatch -p1

%build
%pyproject_build

%install
%pyproject_install

# Install configuration file
install -d %buildroot/etc/hw-test
install -m 644 etc/hw-test.conf.example %buildroot/etc/hw-test.conf

# Create data directories
install -d %buildroot/var/lib/hw-test
install -d %buildroot/var/lib/hw-test/logs
install -d %buildroot/var/log/hw-test

# Create documentation
install -d %buildroot/usr/share/doc/%name-%version
install -m 644 README.md CHANGELOG.md LICENSE %buildroot/usr/share/doc/%name-%version/

%post
# Set permissions for data directories
if [ -d /var/lib/hw-test ]; then
    chmod 755 /var/lib/hw-test
    chmod 755 /var/lib/hw-test/logs
fi

if [ -d /var/log/hw-test ]; then
    chmod 755 /var/log/hw-test
fi

# Create symlink for results
if [ ! -e ~/HW-TEST ]; then
    ln -sf /var/lib/hw-test ~/HW-TEST 2>/dev/null ||:
fi

%postun
# Cleanup on complete removal
if [ "$1" = "0" ]; then
    rm -rf /var/lib/hw-test 2>/dev/null ||:
    rm -rf /var/log/hw-test 2>/dev/null ||:
fi

%files
%doc README.md CHANGELOG.md LICENSE
%config(noreplace) /etc/hw-test.conf
%dir /var/lib/hw-test
%dir /var/lib/hw-test/logs
%dir /var/log/hw-test
%_bindir/%name
%python3_sitelibdir/%name/
%python3_sitelibdir/%{pyproject_distinfo %name}/

%changelog
* Mon Mar 30 2026 Pavel Shilov <zerospirit@altlinux.org> 2.0.0-alt1
- Initial build for Sisyphus.
