"""Ключи настроек, сохраняемых в STATE/settings.ini (наследие internal.sh)."""

from __future__ import annotations

# Расшифровка сокращённых имён флагов опциональных тестов (для разработчиков).
# Значения в runtime: "" = выкл., "1" = вкл.
SETTINGS_KEY_HELP: dict[str, str] = {
    "colormode": "Режим ANSI-цветов терминала",
    "repodate": "Дата снимка репозитория (ГГГГ-ММ-ДД)",
    "compname": "Имя тестируемого компьютера (для архива результатов)",
    "rundir": "Каталог запуска (устаревшее)",
    "langid": "Локаль интерфейса: ru или en",
    "have_altsp": "Обнаружен ALT SP (сертифицированный дистрибутив)",
    "have_systemd": "Система использует systemd",
    "install_mate": "Установить MATE при доустановке графики",
    "distroname": "Полное имя дистрибутива",
    "distro": "Код ветки дистрибутива (p10, Sisyphus, …)",
    "repo": "Суффикс репозитория",
    "have_xorg": "Доступна графическая подсистема X11/Wayland",
    "have_kde5": "Установлена среда KDE Plasma 5",
    "have_mate": "Установлена среда MATE",
    "have_xfce": "Установлена среда Xfce",
    "have_gnome": "Установлена среда GNOME",
    "archname": "Архитектура CPU (x86_64, aarch64, …)",
    "pctype": "Тип устройства: Personal, Notebook, Server, Virtual, …",
    "drives": "Список дисков для тестов (через пробел)",
    "ifaces": "Сетевые интерфейсы для тестов",
    "fwupd_test": "Тест обновления прошивки (fwupd)",
    "devel_test": "Пакеты для разработки (опционально)",
    "xprss_test": "Экспресс-тест (раздел 9 методики)",
    "infb_test": "InfiniBand / RDMA (libibverbs)",
    "sound_test": "Тест звуковой подсистемы",
    "numa_test": "Тест NUMA (numactl)",
    "ipmi_test": "Тест IPMI (ipmitool)",
    "webcam_test": "Тест веб-камеры",
    "power_test": "Тест питания (suspend/hibernate)",
    "fprnt_test": "Тест сканера отпечатков (fprintd)",
    "bluez_test": "Тест Bluetooth",
    "scard_test": "Тест смарт-карт (pcsc)",
    "fio_test": "Тест дисков fio (diskperf)",
    "v3d_test": "3D-тест glmark2",
    "update_apt_lists": "Обновлять индексы APT перед тестами",
    "dist_upgrade": "Выполнять dist-upgrade перед тестами",
    "update_kernel": "Обновлять ядро перед тестами",
    "local_url": "URL локального зеркала репозитория",
    "local_mirror": "Строка fstab для сетевого зеркала",
    "mirror_subdir": "Подкаталог зеркала с репозиториями",
    "local_media_base": "Базовый каталог съёмных носителей (/media/user)",
    "local_media_check": "Метка/подкаталог с зеркалом на носителе",
    "unsafe_diskperf": "Разрешить тесты на неразмонтированных дисках",
    "headless_autorun": "Автопродолжение без GUI при входе (profile.d)",
    "ping_server": "Хост для проверки интернета (ping)",
    "express_video_set": "Набор видео для экспресс-теста: youtube, rutube, vkvideo",
    "local_video_sample": "URL собственного видео для экспресс-теста",
}

# Ключи, записываемые в STATE/settings.ini (без флагов одноразового CLI).
SETTINGS_KEYS: tuple[str, ...] = tuple(SETTINGS_KEY_HELP.keys())
