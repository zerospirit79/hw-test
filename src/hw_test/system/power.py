from ..utils.shell import run

def apply_sleep_policy(mask=True):
    if mask:
        # Маскируем типовые юниты сна, не падаем при ошибке
        for unit in ("sleep.target","suspend.target","hibernate.target","hybrid-sleep.target"):
            run(f"sudo systemctl mask {unit} || true", check=False)
    else:
        for unit in ("sleep.target","suspend.target","hibernate.target","hybrid-sleep.target"):
            run(f"sudo systemctl unmask {unit} || true", check=False)
