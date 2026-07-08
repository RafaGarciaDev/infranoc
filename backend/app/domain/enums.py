import enum


class Criticality(str, enum.Enum):
    Low = "Low"
    Medium = "Medium"
    High = "High"
    Critical = "Critical"


class AssetStatus(str, enum.Enum):
    Active = "Active"
    Maintenance = "Maintenance"
    Retired = "Retired"
    Storage = "Storage"
    Faulty = "Faulty"


class AssetType(str, enum.Enum):
    Server = "Server"
    Workstation = "Workstation"
    Laptop = "Laptop"
    NetworkSwitch = "NetworkSwitch"
    Router = "Router"
    Firewall = "Firewall"
    AccessPoint = "AccessPoint"
    Printer = "Printer"
    UPS = "UPS"
    Generator = "Generator"
    ACUnit = "ACUnit"
    PLC = "PLC"
    HMI = "HMI"
    SCADA = "SCADA"
    Sensor = "Sensor"
    Scale = "Scale"
    Camera = "Camera"
    NVR = "NVR"
    Phone = "Phone"
    StorageArray = "StorageArray"
    TapeLibrary = "TapeLibrary"
    Other = "Other"


class Layer(str, enum.Enum):
    """Camada do ativo dentro da fabrica."""
    TI = "TI"
    OT = "OT"
    Physical = "Physical"