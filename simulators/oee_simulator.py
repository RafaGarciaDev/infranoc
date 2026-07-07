"""
InfraNOC - OEE Simulator
Expoe metricas de OEE (Overall Equipment Effectiveness) para as 4 linhas
de producao da Vale Verde. OEE = Disponibilidade x Performance x Qualidade.
Porta: 9201
"""
import math
import random
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

random.seed(17)

LINES = [
    {"id": 1, "name": "L1-UHT-Leite",       "product": "Leite UHT"},
    {"id": 2, "name": "L2-Iogurte",         "product": "Iogurte"},
    {"id": 3, "name": "L3-Queijo-Frescal",  "product": "Queijo Frescal"},
    {"id": 4, "name": "L4-Manteiga",        "product": "Manteiga"},
]

STOP_REASONS = [
    "setup", "manutencao_preventiva", "quebra_equipamento",
    "falta_materia_prima", "limpeza_cip", "troca_produto",
]

_events = {}

def maybe_event(name, prob=0.003, dur=(120, 600)):
    """Mesma logica do asset_simulator: eventos aleatorios de parada."""
    now = time.time()
    end = _events.get(name)
    if end and now < end:
        return True
    if random.random() < prob:
        _events[name] = now + random.randint(*dur)
        return True
    return False

def wave(period, amp, base):
    return base + amp * math.sin(2 * math.pi * time.time() / period)

def render():
    lines_out = []

    def add(metric, labels, value):
        lbl = ",".join(f'{k}="{v}"' for k, v in labels.items())
        lines_out.append(f"{metric}{{{lbl}}} {value}")

    for line in LINES:
        lid = str(line["id"])
        lname = line["name"]
        product = line["product"]
        base_labels = {"line": lid, "line_name": lname, "product": product}

        stopped = maybe_event(lname)
        add("infranoc_line_running", base_labels, 0 if stopped else 1)

        if stopped:
            # Motivo da parada (aleatorio mas fixo enquanto o evento dura)
            reason_seed = int(_events[lname]) % len(STOP_REASONS)
            reason = STOP_REASONS[reason_seed]
            add("infranoc_line_stop_reason",
                {**base_labels, "reason": reason}, 1)
            add("infranoc_availability_percent", base_labels, 0)
            add("infranoc_performance_percent", base_labels, 0)
            add("infranoc_quality_percent", base_labels, 0)
            add("infranoc_oee_percent", base_labels, 0)
            continue

        # Metricas em operacao normal
        # Disponibilidade: 85-98% (oscila com onda longa)
        avail = round(wave(1800, 6, 91) + random.uniform(-2, 2), 1)
        avail = max(0, min(100, avail))

        # Performance: 80-97%
        perf = round(wave(900, 8, 88) + random.uniform(-3, 3), 1)
        perf = max(0, min(100, perf))

        # Qualidade: 95-99.5% (mais estavel)
        qual = round(wave(3600, 2, 97) + random.uniform(-0.8, 0.8), 1)
        qual = max(0, min(100, qual))

        oee = round((avail * perf * qual) / 10000, 1)

        add("infranoc_availability_percent", base_labels, avail)
        add("infranoc_performance_percent", base_labels, perf)
        add("infranoc_quality_percent", base_labels, qual)
        add("infranoc_oee_percent", base_labels, oee)

        # Contadores de producao
        produced = int(wave(600, 200, 1500) + random.randint(-50, 50))
        rejected = int(produced * (100 - qual) / 100)
        add("infranoc_units_produced_total", base_labels, max(0, produced))
        add("infranoc_units_rejected_total", base_labels, max(0, rejected))

    return "\n".join(lines_out) + "\n"

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
        pass

if __name__ == "__main__":
    port = 9201
    print(f"[oee_simulator] servindo {len(LINES)} linhas em http://0.0.0.0:{port}/metrics")
    HTTPServer(("0.0.0.0", port), MetricsHandler).serve_forever()