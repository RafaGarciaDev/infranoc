"""
InfraNOC - Asset Simulator (Fase 4.5)
Expoe metricas Prometheus para ~600 ativos da fabrica Vale Verde S/A.

Labels em todas as metricas: asset, site, area, linha, sim_type.
Porta: 9200
"""
import math
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

from asset_catalog import build_assets

random.seed(42)  # ativos determinsticos entre reinicios

ASSETS = build_assets()

# -----------------------------------------------------------------------------
# Simulacao de eventos (falhas aleatorias com duracao randomica)
# -----------------------------------------------------------------------------
_events: dict[str, float] = {}  # nome -> timestamp de fim do evento


def maybe_event(name: str, prob: float = 0.002, dur: tuple[int, int] = (60, 300)) -> bool:
    """True se o ativo esta em evento. Novos eventos surgem com probabilidade `prob`
    por chamada e duram `dur` segundos."""
    now = time.time()
    end = _events.get(name)
    if end and now < end:
        return True
    if random.random() < prob:
        _events[name] = now + random.randint(*dur)
        return True
    return False


def wave(period: float, amp: float, base: float) -> float:
    """Onda senoidal para simular variacao natural (CPU, rede, temp)."""
    return base + amp * math.sin(2 * math.pi * time.time() / period)


# -----------------------------------------------------------------------------
# Render das metricas no formato Prometheus
# -----------------------------------------------------------------------------
def _base_labels(asset: dict) -> dict:
    return {
        "asset": asset["name"],
        "site": asset["site"],
        "area": asset["area"],
        "linha": asset["linha"],
        "sim_type": asset["sim_type"],
    }


def render() -> str:
    lines: list[str] = []

    def add(metric: str, labels: dict, value) -> None:
        lbl = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines.append(f"{metric}{{{lbl}}} {value}")

    for a in ASSETS:
        name = a["name"]
        st = a["sim_type"]
        base = _base_labels(a)

        down = maybe_event(name)
        add("infranoc_asset_up", base, 0 if down else 1)
        if down:
            continue

        # ---------- TI ----------
        if st in ("server", "workstation"):
            add("infranoc_cpu_percent", base,
                round(wave(120, 25, 40) + random.uniform(-5, 5), 1))
            add("infranoc_mem_percent", base,
                round(wave(300, 15, 55), 1))
            add("infranoc_disk_percent", base,
                round(random.uniform(35, 78), 1))

        elif st in ("switch", "router", "firewall", "wifi_ap"):
            add("infranoc_net_throughput_mbps",
                {**base, "dir": "in"},
                round(wave(60, 200, 300), 1))
            add("infranoc_ports_up", base,
                random.randint(18, 24))

        elif st in ("ups", "generator"):
            on_batt = maybe_event(name, 0.001, (120, 600))
            add("infranoc_ups_on_battery", base, 1 if on_batt else 0)
            add("infranoc_ups_battery_percent", base,
                round(random.uniform(40, 99), 1))

        elif st == "printer":
            add("infranoc_printer_toner_percent", base,
                round(random.uniform(5, 95), 1))
            add("infranoc_printer_pages_total", base,
                random.randint(1000, 90000))

        elif st == "camera":
            add("infranoc_camera_fps", base,
                random.choice([15, 25, 30]))

        elif st == "air_conditioner":
            add("infranoc_temp_celsius", base,
                round(wave(600, 2, 22), 2))

        # ---------- OT: controle ----------
        elif st == "plc":
            fault = maybe_event(name, 0.003, (120, 400))
            add("infranoc_plc_status", base, 0 if fault else 1)
            add("infranoc_plc_counter_total", base,
                random.randint(10000, 500000))

        elif st == "hmi":
            add("infranoc_hmi_alarms_active", base, random.randint(0, 3))

        # ---------- OT: sensores ----------
        elif st == "sensor_temp_past":
            target = 72.0
            drift = maybe_event(name, 0.0015, (180, 600))
            offset = random.uniform(3, 8) if drift else random.uniform(-1.2, 1.2)
            add("infranoc_temp_celsius", base, round(target + offset, 2))

        elif st == "sensor_temp_cf":
            target = -18.0
            drift = maybe_event(name, 0.002, (180, 600))
            # drift pra cima simula degelo/falha de compressor (pode passar de -2 e disparar alerta)
            offset = random.uniform(15, 22) if drift else random.uniform(-1.5, 1.5)
            add("infranoc_temp_celsius", base, round(target + offset, 2))

        elif st == "sensor_press":
            # pasteurizacao roda ~3.5 bar; drift sobe pra 4.5+ e dispara alerta
            drift = maybe_event(name, 0.0018, (120, 400))
            base_p = 3.5
            val = base_p + (random.uniform(1.2, 1.8) if drift else random.uniform(-0.3, 0.4))
            add("infranoc_pressure_bar", base, round(val, 2))

        elif st == "sensor_level":
            add("infranoc_level_percent", base,
                round(wave(900, 25, 55), 1))

        elif st == "sensor_flow":
            add("infranoc_flow_lpm", base,
                round(wave(180, 40, 120) + random.uniform(-5, 5), 1))

        elif st == "sensor_vibr":
            # ISO 10816: > 7.1 mm/s dispara alerta
            drift = maybe_event(name, 0.0018, (300, 800))
            val = random.uniform(5.5, 8.5) if drift else random.uniform(1.5, 4.5)
            add("infranoc_vibration_mmps", base, round(val, 2))

        # ---------- OT: rotativos e vasos ----------
        elif st == "motor":
            running = 0 if maybe_event(name, 0.001, (60, 200)) else 1
            add("infranoc_motor_running", base, running)
            add("infranoc_motor_hours_total", base,
                random.randint(1000, 60000))

        elif st == "tank":
            add("infranoc_level_percent", base,
                round(wave(1200, 30, 55), 1))

        elif st == "air_compressor":
            add("infranoc_pressure_bar", base,
                round(wave(240, 0.8, 7.5), 2))
            add("infranoc_motor_hours_total", base,
                random.randint(5000, 40000))

        elif st == "steam_boiler":
            add("infranoc_pressure_bar", base,
                round(wave(300, 0.5, 8.0), 2))
            add("infranoc_temp_celsius", base,
                round(wave(300, 8, 165), 1))

        elif st == "chilled_water_pump":
            running = 0 if maybe_event(name, 0.0015, (60, 240)) else 1
            add("infranoc_motor_running", base, running)
            add("infranoc_flow_lpm", base,
                round(wave(180, 20, 90), 1))

        # ---------- Laboratorio / balancas / leitores ----------
        elif st in ("weighing_scale", "lab_scale"):
            add("infranoc_scale_reads_total", base,
                random.randint(100, 30000))

        elif st == "barcode_reader":
            add("infranoc_barcode_reads_total", base,
                random.randint(500, 200000))

    return "\n".join(lines) + "\n"


# -----------------------------------------------------------------------------
# Servidor HTTP
# -----------------------------------------------------------------------------
class MetricsHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            body = render().encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *_):
        pass  # silencia log de acesso


if __name__ == "__main__":
    port = 9200
    print(f"[asset_simulator] servindo {len(ASSETS)} ativos em http://0.0.0.0:{port}/metrics")
    HTTPServer(("0.0.0.0", port), MetricsHandler).serve_forever()