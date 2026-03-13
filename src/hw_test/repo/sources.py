from typing import Optional

# Замените URL ниже на ваши официальные зеркала/архивы
DEFAULT_HTTP_BASE = "http://mirror.your.alt/repo"     # пример
DEFAULT_LAN_BASE  = "http://alt-mirror.lan/repo"      # пример

def render_sources_for_release(branch: str,
                               source: str = "internet",
                               mirror_url: Optional[str] = None) -> str:
    """
    Возвращает текст для /etc/apt/sources.list.d/pc-test.list
    branch: p9|p10|p11|c9f2|c10f2|sisyphus|unknown
    source: internet|usb|lan
    mirror_url: переопределение базового URL
    """
    if source not in ("internet","usb","lan"):
        raise ValueError("source must be internet|usb|lan")

    if source == "internet":
        base = mirror_url or DEFAULT_HTTP_BASE
    elif source == "lan":
        base = mirror_url or DEFAULT_LAN_BASE
    else:  # usb
        # mirror_url должен быть вида file:///media/USER/ALT-MIRROR/{branch}/...
        if not mirror_url or not mirror_url.startswith("file://"):
            raise ValueError("for usb source provide mirror_url like file:///media/USB/ALT/{branch}")
        base = mirror_url

    # Простейшие шаблоны (apt-rpm)
    # Пример строки: rpm [alt] <url> <dist> classic
    # В реальности замените на корректные для ALT Linux строки.
    if branch == "p10":
        lines = [
            f"rpm [alt] {base}/p10 x86_64 classic",
            f"rpm [alt] {base}/p10 noarch classic",
            f"rpm [alt] {base}/p10 updates classic",
        ]
    elif branch == "p11":
        lines = [
            f"rpm [alt] {base}/p11 x86_64 classic",
            f"rpm [alt] {base}/p11 noarch classic",
            f"rpm [alt] {base}/p11 updates classic",
        ]
    elif branch == "p9":
        lines = [
            f"rpm [alt] {base}/p9 x86_64 classic",
            f"rpm [alt] {base}/p9 noarch classic",
            f"rpm [alt] {base}/p9 updates classic",
        ]
    elif branch in ("c9f2","c10f2"):
        lines = [
            f"rpm [alt] {base}/{branch} x86_64 classic",
            f"rpm [alt] {base}/{branch} noarch classic",
        ]
    elif branch == "sisyphus":
        lines = [
            f"rpm [alt] {base}/Sisyphus x86_64 classic",
            f"rpm [alt] {base}/Sisyphus noarch classic",
        ]
    else:
    # неизвестная ветка — не трогаем (вернём пустой файл)
        lines = []

    return "\n".join(lines) + ("\n" if lines else "")
