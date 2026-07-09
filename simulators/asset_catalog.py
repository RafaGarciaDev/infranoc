"""
InfraNOC - Catalogo declarativo da fabrica Vale Verde S/A (planta PSA).

Modelo ISA-95: Area -> Linha -> Equipamento.
Consumido pelo asset_simulator para gerar metricas Prometheus.
"""
from typing import TypedDict


class EquipmentInfo(TypedDict):
    prefix: str
    sim_type: str


# Especificacao de cada tipo de equipamento.
# prefix vai no nome do ativo, sim_type vai como label pro Prometheus/importer.
EQUIPMENT_SPEC: dict[str, EquipmentInfo] = {
    "PLC":            {"prefix": "CLP",     "sim_type": "plc"},
    "HMI":            {"prefix": "HMI",     "sim_type": "hmi"},
    "SENS_TEMP_PAST": {"prefix": "SENS-TP", "sim_type": "sensor_temp_past"},
    "SENS_TEMP_CF":   {"prefix": "SENS-TC", "sim_type": "sensor_temp_cf"},
    "SENS_PRESS":     {"prefix": "SENS-PR", "sim_type": "sensor_press"},
    "SENS_LEVEL":     {"prefix": "SENS-LV", "sim_type": "sensor_level"},
    "SENS_FLOW":      {"prefix": "SENS-FL", "sim_type": "sensor_flow"},
    "SENS_VIBR":      {"prefix": "SENS-VB", "sim_type": "sensor_vibr"},
    "MOTOR":          {"prefix": "MOT",     "sim_type": "motor"},
    "TANK":           {"prefix": "TQ",      "sim_type": "tank"},
    "AIR_COMP":       {"prefix": "COMPR",   "sim_type": "air_compressor"},
    "BOILER":         {"prefix": "CALD",    "sim_type": "steam_boiler"},
    "CHILLED_PUMP":   {"prefix": "BOMBA",   "sim_type": "chilled_water_pump"},
    "SERVER":         {"prefix": "SRV",     "sim_type": "server"},
    "WS":             {"prefix": "WS",      "sim_type": "workstation"},
    "SW":             {"prefix": "SW",      "sim_type": "switch"},
    "ROUTER":         {"prefix": "RTR",     "sim_type": "router"},
    "FW":             {"prefix": "FW",      "sim_type": "firewall"},
    "AP":             {"prefix": "AP",      "sim_type": "wifi_ap"},
    "UPS":            {"prefix": "UPS",     "sim_type": "ups"},
    "GEN":            {"prefix": "GER",     "sim_type": "generator"},
    "CAM":            {"prefix": "CAM",     "sim_type": "camera"},
    "PRN":            {"prefix": "PRN",     "sim_type": "printer"},
    "AC":             {"prefix": "AC",      "sim_type": "air_conditioner"},
    "WEIGH":          {"prefix": "BAL",     "sim_type": "weighing_scale"},
    "SCALE":          {"prefix": "SCL",     "sim_type": "lab_scale"},
    "BARCODE":        {"prefix": "LEIT",    "sim_type": "barcode_reader"},
}


# Modelo declarativo da fabrica.
# Estrutura: area_key -> {code, name, short, lines: {line_code: {eq_kind: qty}}}
FACTORY_MODEL: dict[str, dict] = {
    "RECEBIMENTO": {
        "code": "PSA-AREA-RECEBIMENTO",
        "name": "Recebimento",
        "short": "RECEB",
        "lines": {
            "DOC-01":     {"PLC":2, "CAM":4, "WS":3, "BARCODE":3, "PRN":1},
            "DOC-02":     {"PLC":2, "CAM":4, "WS":3, "BARCODE":3, "PRN":1},
            "TANQUE-CRU": {"TANK":6, "SENS_LEVEL":6, "SENS_TEMP_CF":3, "MOTOR":3, "SENS_VIBR":3},
            "CONTROLE":   {"WS":4, "PRN":1, "SW":1, "SERVER":1},
            "CAM-PERIM":  {"CAM":6},
        },
    },
    "PASTEURIZACAO": {
        "code": "PSA-AREA-PASTEURIZACAO",
        "name": "Pasteurizacao",
        "short": "PAST",
        "lines": {
            "L1":         {"PLC":3, "HMI":2, "SENS_TEMP_PAST":5, "SENS_PRESS":4, "MOTOR":4, "SENS_VIBR":4, "SENS_FLOW":3, "CAM":2},
            "L2":         {"PLC":3, "HMI":2, "SENS_TEMP_PAST":5, "SENS_PRESS":4, "MOTOR":4, "SENS_VIBR":4, "SENS_FLOW":3, "CAM":2},
            "L3":         {"PLC":3, "HMI":2, "SENS_TEMP_PAST":5, "SENS_PRESS":4, "MOTOR":4, "SENS_VIBR":4, "SENS_FLOW":3, "CAM":2},
            "CONTROLE":   {"WS":8, "PRN":2, "SW":1, "SERVER":1},
            "CAM-PERIM":  {"CAM":8},
        },
    },
    "ENVASE": {
        "code": "PSA-AREA-ENVASE",
        "name": "Envase",
        "short": "ENV",
        "lines": {
            "L1":         {"PLC":3, "HMI":2, "MOTOR":4, "SENS_VIBR":4, "WEIGH":3, "SENS_PRESS":2, "WS":4, "CAM":3, "PRN":1},
            "L2":         {"PLC":2, "HMI":1, "MOTOR":3, "SENS_VIBR":3, "WEIGH":2, "WS":3, "CAM":2, "PRN":1},
            "L3":         {"PLC":2, "HMI":1, "MOTOR":3, "SENS_VIBR":3, "WEIGH":2, "WS":3, "CAM":2, "PRN":1},
            "L4":         {"PLC":2, "HMI":1, "MOTOR":3, "SENS_VIBR":3, "WEIGH":1, "WS":3, "CAM":2, "PRN":1},
            "CONTROLE":   {"WS":10, "PRN":2, "SW":1, "SERVER":1},
            "CAM-PERIM":  {"CAM":8},
        },
    },
    "CAMARAS-FRIAS": {
        "code": "PSA-AREA-CAMARAS-FRIAS",
        "name": "Camaras Frias",
        "short": "CF",
        "lines": {
            "CF01":       {"SENS_TEMP_CF":4, "MOTOR":2, "SENS_VIBR":2, "CHILLED_PUMP":2, "CAM":3},
            "CF02":       {"SENS_TEMP_CF":4, "MOTOR":2, "SENS_VIBR":2, "CHILLED_PUMP":2, "CAM":3},
            "CF03":       {"SENS_TEMP_CF":4, "MOTOR":2, "SENS_VIBR":2, "CHILLED_PUMP":2, "CAM":3},
            "CF04":       {"SENS_TEMP_CF":4, "MOTOR":2, "SENS_VIBR":2, "CHILLED_PUMP":2, "CAM":3},
            "CONTROLE":   {"WS":3, "PRN":1, "SW":1},
            "CAM-PERIM":  {"CAM":6},
        },
    },
    "EXPEDICAO": {
        "code": "PSA-AREA-EXPEDICAO",
        "name": "Expedicao",
        "short": "EXPED",
        "lines": {
            "DOC-01":     {"CAM":4, "WS":4, "BARCODE":4, "WEIGH":2, "PRN":1},
            "DOC-02":     {"CAM":4, "WS":4, "BARCODE":4, "WEIGH":2, "PRN":1},
            "PICKING":    {"WS":8, "BARCODE":6, "PRN":2, "CAM":3},
            "SEP":        {"WS":5, "BARCODE":4, "CAM":4, "PRN":1},
            "CONTROLE":   {"WS":5, "PRN":2, "SW":1, "SERVER":1},
        },
    },
    "UTILIDADES": {
        "code": "PSA-AREA-UTILIDADES",
        "name": "Utilidades",
        "short": "UTIL",
        "lines": {
            "ENERGIA":    {"UPS":8, "GEN":3, "PLC":2, "SENS_PRESS":2},
            "AR-COMP":    {"AIR_COMP":4, "MOTOR":4, "SENS_PRESS":4, "SENS_VIBR":4},
            "VAPOR":      {"BOILER":3, "MOTOR":3, "SENS_PRESS":4, "SENS_TEMP_PAST":3, "SENS_FLOW":3},
            "AGUA":       {"MOTOR":4, "SENS_FLOW":4, "SENS_PRESS":3, "TANK":3},
            "CONTROLE":   {"WS":4, "PRN":1, "PLC":2, "HMI":2},
        },
    },
    "LABORATORIO": {
        "code": "PSA-AREA-LABORATORIO",
        "name": "Laboratorio",
        "short": "LAB",
        "lines": {
            "QA-BENCH":   {"WS":8, "PRN":2, "WEIGH":4, "SCALE":4},
            "QA-INSTR":   {"WS":5, "PRN":2, "WEIGH":3, "SCALE":3},
            "CONTROLE":   {"WS":5, "PRN":2, "SERVER":1},
        },
    },
    "TI-DATACENTER": {
        "code": "PSA-AREA-TI-DATACENTER",
        "name": "TI Datacenter",
        "short": "DC",
        "lines": {
            "RACK01":     {"SERVER":4, "SW":3, "UPS":2, "AC":2},
            "RACK02":     {"SERVER":4, "SW":3, "UPS":2, "AC":2},
            "RACK03":     {"SERVER":4, "SW":3, "UPS":2, "AC":2},
            "CORE":       {"SW":5, "ROUTER":3, "FW":2},
            "WIFI":       {"AP":40},
            "NOC":        {"WS":10, "SERVER":3, "SW":2, "PRN":2},
        },
    },
}


def build_assets() -> list[dict]:
    """
    Gera a lista completa de ativos com base no FACTORY_MODEL.

    Cada ativo:
      - name: PSA-{SHORT}-{LINE}-{PREFIX}-{NN}
      - sim_type: chave logica para o render do simulator e para o importer
      - site: "PSA"
      - area: chave curta (RECEBIMENTO, PASTEURIZACAO, ...)
      - area_code: codigo completo (PSA-AREA-...)
      - linha: codigo da linha
    """
    assets: list[dict] = []
    for area_key, area in FACTORY_MODEL.items():
        for line_code, equipments in area["lines"].items():
            for eq_kind, qty in equipments.items():
                spec = EQUIPMENT_SPEC[eq_kind]
                for i in range(1, qty + 1):
                    name = f"PSA-{area['short']}-{line_code}-{spec['prefix']}-{i:02d}"
                    assets.append({
                        "name": name,
                        "sim_type": spec["sim_type"],
                        "site": "PSA",
                        "area": area_key,
                        "area_code": area["code"],
                        "linha": line_code,
                    })
    return assets


if __name__ == "__main__":
    from collections import Counter
    lst = build_assets()
    print(f"Total: {len(lst)} ativos")
    print("Por sim_type:", dict(Counter(a["sim_type"] for a in lst)))
    print("Por area:", dict(Counter(a["area"] for a in lst)))