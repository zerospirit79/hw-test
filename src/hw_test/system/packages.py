from ..utils.shell import run

COMMON_PKGS = ["inxi","pciutils","usbutils","dmidecode","iproute2","ethtool","curl","psmisc"]
GRAPHICAL_PKGS = ["xorg-x11","xinit","alsa-utils"]
MEDIA_PKGS = ["mpv","firefox","chromium"]

def ensure_packages(want_graphics=True, want_media=True):
    pkgs = COMMON_PKGS[:]
    if want_graphics:
        pkgs += GRAPHICAL_PKGS
    if want_media:
        pkgs += MEDIA_PKGS
    run("sudo apt-get update || true", check=False)
    run("sudo apt-get install -y " + " ".join(pkgs), check=False)
