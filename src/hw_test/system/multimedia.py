import shutil, subprocess, time

def play_video(urls, preferred_browser=None, timeout_sec=30):
    # Пытаемся открыть в браузере, иначе — mpv
    browser = preferred_browser or (shutil.which("firefox") and "firefox") or (shutil.which("chromium") and "chromium") or None
    if browser:
        for u in urls[:3]:
            subprocess.Popen([browser, u], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(3)
        return
    if shutil.which("mpv"):
        subprocess.Popen(["mpv", "--no-config", urls[0]], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(timeout_sec)
