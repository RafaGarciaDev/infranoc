"""
InfraNOC — Asset Simulator
Expoe metricas Prometheus para ~330 ativos ficticios da fabrica Vale Verde.
Porta: 9200
"""
import math
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

random.seed(42)  # ativos determinsticos entre reinicios

# -----------------------------------------------------------------------------
# Cadastro de ativos
# -----------------------------------------------------------------------------
def build_assets():
    assets = []

    # Servidores TI e OT (nao inclui DC01/MES01 que sao reais)
    for name in ["PSA-TI-DC02", "PSA-TI-FS01", "PSA-TI-ERP01", "PSA-TI-BKP01",
                 "PSA-OT-SCADA01", "SPO-TI-DC03"]:
        assets.append({"name": name, "type": "server", "site": name[:3]})

    # Switches de acesso da producao
    for i in range(1, 7):
        assets.append({"name": f"PSA-NET-SW-ACC-PROD{i:02d}",
                       "type": "network", "site": "PSA"})

    # Access points wifi
    for i in range(1, 15):
        assets.append({"name": f"PSA-NET-AP-{i:02d}",
                       "type": "network", "site": "PSA"})

    # No-breaks (UPS)
    for tag in ("TI01", "OT01", "DC01"):
        assets.append({"name": f"PSA-INFRA-UPS-{tag}",
                       "type": "power", "site": "PSA"})

    # Impressoras
    for i in range(1, 19):
        assets.append({"name": f"PSA-PRN-{i:02d}",
                       "type": "printer", "site": "PSA"})

    # CLPs (4 linhas x 3 equipamentos)
    for linha in range(1, 5):
        for eq in range(1, 4):
            assets.append({"name": f"PSA-OT-CLP-L{linha}-{eq:02d}",
                           "type": "plc", "site": "PSA", "line": linha})

    # Sensores camara fria (-18C)
    for i in range(1, 5):
        assets.append({"name": f"PSA-OT-SENS-CF{i:02d}-T",
                       "type": "temp", "site": "PSA", "target": -18})

    # Sensores pasteurizacao (+72C)
    for i in range(1, 3):
        assets.append({"name": f"PSA-OT-SENS-PAST-T{i}",
                       "type": "temp", "site": "PSA", "target": 72})

    # Cameras
    for i in range(1, 25):
        assets.append({"name": f"PSA-SEC-CAM-{i:02d}",
                       "type": "camera", "site": "PSA"})

    # Workstations
    for i in range(1, 26):
        assets.append({"name": f"PSA-WS-{i:03d}",
                       "type": "workstation", "site": "PSA"})

    return assets

ASSETS = build_assets()

# -----------------------------------------------------------------------------
# Simulacao de eventos (falhas aleatorias com duracao randomica)
# -----------------------------------------------------------------------------
_events = {}  # nome -> timestamp de fim do evento

def maybe_event(name, prob=0.002, dur=(60, 300)):
    """Retorna True se o ativo esta em evento (falha). Novos eventos surgem com
    probabilidade `prob` por chamada e duram `dur` segundos."""
    now = time.time()
    end = _events.get(name)
    if end and now < end:
        return True
    if random.random() < prob:
        _events[name] = now + random.randint(*dur)
        return True
    return False

def wave(period, amp, base):
    """Onda senoidal para simular variacao natural (CPU, rede)."""
    return base + amp * math.sin(2 * math.pi * time.time() / period)

# -----------------------------------------------------------------------------
# Render das metricas no formato Prometheus
# -----------------------------------------------------------------------------
def render():
    lines = []

    def add(metric, labels, value):
        lbl = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines.append(f"{metric}{{{lbl}}} {value}")

    for a in ASSETS:
        name, t = a["name"], a["type"]
        down = maybe_event(name)
        add("infranoc_asset_up",
            {"asset": name, "type": t, "site": a["site"]},
            0 if down else 1)
        if down:
            continue

        if t in ("server", "workstation"):
            add("infranoc_cpu_percent", {"asset": name},
                round(wave(120, 25, 40) + random.uniform(-5, 5), 1))
            add("infranoc_mem_percent", {"asset": name},
                round(wave(300, 15, 55), 1))
            add("infranoc_disk_percent", {"asset": name},
                round(random.uniform(35, 78), 1))

        elif t == "network":
            add("infranoc_net_throughput_mbps",
                {"asset": name, "dir": "in"},
                round(wave(60, 200, 300), 1))
            add("infranoc_ports_up", {"asset": name},
                random.randint(18, 24))

        elif t == "power":
            on_batt = maybe_event(name, 0.001, (120, 600))
            add("infranoc_ups_on_battery", {"asset": name},
                1 if on_batt else 0)
            add("infranoc_ups_battery_percent", {"asset": name},
                round(random.uniform(40, 99), 1))

        elif t == "printer":
            add("infranoc_printer_toner_percent", {"asset": name},
                round(random.uniform(5, 95), 1))
            add("infranoc_printer_pages_total", {"asset": name},
                random.randint(1000, 90000))

        elif t == "plc":
            fault = maybe_event(name, 0.003, (120, 400))
            add("infranoc_plc_status",
                {"asset": name, "line": str(a["line"])},
                0 if fault else 1)
            add("infranoc_plc_counter_total", {"asset": name},
                random.randint(10000, 500000))

        elif t == "temp":
            target = a["target"]
            drift = maybe_event(name, 0.0015, (180, 600))
            offset = random.uniform(3, 8) if drift else random.uniform(-1.2, 1.2)
            add("infranoc_temp_celsius",
                {"asset": name, "target": str(target)},
                round(target + offset, 2))

        elif t == "camera":
            add("infranoc_camera_fps", {"asset": name},
                random.choice([15, 25, 30]))

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
