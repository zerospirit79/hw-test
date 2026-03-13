from __future__ import annotations
import json
import re
from typing import Any, Dict, Tuple, List

from .utils.cmd import run_cmd

def _run_sensors_json() -> Tuple[int, str, str]:
    r = run_cmd(["sensors", "-j"], timeout=20)
    return r["rc"], r["stdout"], r["stderr"]

def _run_sensors_text() -> Tuple[int, str, str]:
    r = run_cmd(["sensors"], timeout=20)
    return r["rc"], r["stdout"], r["stderr"]

def _parse_text(text: str) -> Dict[str, Any]:
    # Очень приблизительный парсер текстового вывода sensors
    # Формат разделён по чипам; строки вида:
    # coretemp-isa-0000
    # Adapter: ISA adapter
    # Package id 0:  +45.0°C  (high = +100.0°C, crit = +100.0°C)
    chips: Dict[str, Any] = {}
    current_chip = None
    for line in text.splitlines():
        if not line.strip():
            continue
        # Заголовок чипа: без двоеточий и с адаптером на следующей строке
        if re.match(r'^[A-Za-z0-9_.\-:]+$', line.strip()) and not line.startswith('Adapter:'):
            current_chip = line.strip()
            chips.setdefault(current_chip, {"Adapter": None, "sensors": {}})
            continue
        if line.startswith("Adapter:") and current_chip:
            chips[current_chip]["Adapter"] = line.split(":", 1)[1].strip()
            continue
        if current_chip:
            # Пример: "Package id 0:  +45.0°C  (high = +100.0°C, crit = +100.0°C)"
            m = re.match(r'^([^:]+):\s+([+\-]?\d+(\.\d+)?)°C', line)
            if m:
                label = m.group(1).strip()
                val = float(m.group(2))
                chips[current_chip]["sensors"][label] = {"temp_c": val}
                continue
            # Вольтаж: "Vcore:        1.10 V"
            m = re.match(r'^([^:]+):\s+([+\-]?\d+(\.\d+)?)\s*V\b', line)
            if m:
                label = m.group(1).strip()
                val = float(m.group(2))
                chips[current_chip]["sensors"][label] = {"voltage_v": val}
                continue
            # Вентиляторы: "fan1:        1234 RPM"
            m = re.match(r'^([^:]+):\s+(\d+)\s*RPM\b', line)
            if m:
                label = m.group(1).strip()
                val = int(m.group(2))
                chips[current_chip]["sensors"][label] = {"fan_rpm": val}
                continue
    return chips

def run(json_out: bool = False) -> int:
    # Пытаемся получить JSON из sensors -j
    rc, out, err = _run_sensors_json()
    parsed: Dict[str, Any] = {}
    mode = "json"
    if rc == 0 and out.strip():
        try:
            parsed = json.loads(out)
        except Exception:
            parsed = {}
    if not parsed:
        # fallback: текстовый разбор
        mode = "text"
        rc_t, out_t, err_t = _run_sensors_text()
        if rc_t != 0:
            if json_out:
                print(json.dumps({"error": "sensors_failed", "stderr": err_t}, ensure_ascii=False, indent=2))
            else:
                print("Ошибка: sensors не выполнился")
                if err_t:
                    print(err_t.strip())
            return 0
            parsed = _parse_text(out_t)

    if json_out:
        print(json.dumps({"mode": mode, "data": parsed}, ensure_ascii=False, indent=2))
        return 0

    # Человекочитаемый вывод: краткое резюме температур/кулеров
    temps: List[Tuple[str, str, float]] = []
    fans: List[Tuple[str, str, int]] = []

    if mode == "json":
        # sensors -j отдаёт структуру: { "chip": { "Adapter": "...", "feature": { "temp1": { "temp1_input": 45.0, ... }}}}
        for chip, chip_data in parsed.items():
            if not isinstance(chip_data, dict):
                continue
            for feat, feat_data in chip_data.items():
                if feat == "Adapter":
                    continue
                if not isinstance(feat_data, dict):
                    continue
                # Температуры
                for k, v in feat_data.items():
                    if isinstance(v, dict):
                        temp = v.get("temp1_input") or v.get("temp2_input") or v.get("input")
                        if isinstance(temp, (int, float)):
                            temps.append((chip, feat, float(temp)))
                        rpm = v.get("fan1_input") or v.get("fan2_input")
                        if isinstance(rpm, (int, float)):
                            fans.append((chip, feat, int(rpm)))
    else:
        # уже сплющено в _parse_text
        for chip, chip_data in parsed.items():
            sensors = chip_data.get("sensors", {})
            for label, vals in sensors.items():
                if "temp_c" in vals:
                    temps.append((chip, label, float(vals["temp_c"])))
                if "fan_rpm" in vals:
                    fans.append((chip, label, int(vals["fan_rpm"])))

    if temps:
        avg = sum(t for _, _, t in temps) / len(temps)
        max_t = max(temps, key=lambda x: x[2])
        min_t = min(temps, key=lambda x: x[2])
        print(f"Температуры: датчиков={len(temps)}, ср={avg:.1f}°C, мин={min_t[2]:.1f}°C, макс={max_t[2]:.1f}°C")
    else:
        print("Температуры: нет данных")

    if fans:
        max_f = max(fans, key=lambda x: x[2])
        print(f"Кулеры: датчиков={len(fans)}, макс={max_f[2]} RPM")
    else:
        print("Кулеры: нет данных")

    return 0
