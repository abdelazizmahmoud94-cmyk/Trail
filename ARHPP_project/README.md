# ARHPP v2.0

**Adaptive Real-Time Hydraulics & Pore Pressure Platform**

Digital Twin للبئر يُفسّر كل psi.

## Install

```bash
pip install -r requirements.txt
python -m excel_templates.build_templates
python -m api.server
```

## Features

- 27 engines (Hydraulics, T&D, Pore Pressure, Events, PLC)
- Pressure Ledger (كل psi مُفسّر)
- U-Tube as flow driver
- Multi-Fluid Tracking
- Kuwait RA-0915 calibration
- WITS/WITSML sensors
- Calibration Sandbox
- ML Enhancement
- Web Dashboard

## Docs

- `docs/ARCHITECTURE.md`
- `docs/API.md`
- `docs/DEPLOY.md`
