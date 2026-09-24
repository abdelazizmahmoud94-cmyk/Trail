"""Build all ARHPP Excel templates."""

from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment


OUT = Path(__file__).resolve().parent.parent / "excel_input"
OUT.mkdir(exist_ok=True)
HDR_FILL = PatternFill("solid", fgColor="1F4E79")
HDR_FONT = Font(color="FFFFFF", bold=True)
TITLE_FONT = Font(bold=True, size=14, color="1F4E79")


def _style(ws, row=1):
    for c in ws[row]:
        c.fill = HDR_FILL
        c.font = HDR_FONT
        c.alignment = Alignment(horizontal="center", vertical="center")


def make(name, sheets):
    wb = Workbook()
    wb.remove(wb.active)
    for sn, cfg in sheets.items():
        ws = wb.create_sheet(sn)
        start = 1
        if cfg.get("title"):
            ws["A1"] = cfg["title"]
            ws["A1"].font = TITLE_FONT
            start = 3
        for j, h in enumerate(cfg["headers"], 1):
            ws.cell(row=start, column=j, value=h)
        _style(ws, start)
        for i, row in enumerate(cfg.get("rows", []), start + 1):
            for j, v in enumerate(row, 1):
                ws.cell(row=i, column=j, value=v)
        for col in ws.columns:
            w = max(len(str(c.value or "")) for c in col) + 3
            ws.column_dimensions[col[0].column_letter].width = min(w, 30)
    wb.save(OUT / name)
    print(f"  + {name}")


def build_all():
    print("ARHPP - Building Excel templates...")

    make("01_Well_Header.xlsx", {"Well": {
        "title": "Well Header",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [
            ["Well Name", "KU-EXAMPLE-1", ""],
            ["Rig Name", "RIG-XX", ""],
            ["Field", "Field-A", ""],
            ["Operator", "KOC", ""],
            ["Country", "Kuwait", ""],
            ["RKB", 65.0, "ft"],
            ["Water Depth", 0.0, "ft"],
            ["Datum", "RKB", ""]]}})

    make("02_Survey.xlsx", {"Survey": {
        "title": "Well Survey (MD/Inc/Azi)",
        "headers": ["MD_ft", "Inc_deg", "Azi_deg", "TVD_ft", "N_ft",
                     "E_ft", "DLS"],
        "rows": [
            [0, 0, 0, None, None, None, None],
            [500, 0.5, 45, None, None, None, None],
            [1000, 1, 45, None, None, None, None],
            [2000, 3, 60, None, None, None, None],
            [3000, 8, 75, None, None, None, None],
            [5000, 20, 90, None, None, None, None],
            [8000, 30, 95, None, None, None, None],
            [12000, 35, 100, None, None, None, None],
            [15000, 30, 105, None, None, None, None]]}})

    make("03_Hole_Program.xlsx", {"HoleProgram": {
        "title": "Hole Sections",
        "headers": ["Section", "Hole_ID_in", "Top_MD_ft",
                     "Bottom_MD_ft", "Casing_OD_in", "Casing_ID_in",
                     "Shoe_MD_ft"],
        "rows": [
            ["Surface", 26, 0, 1500, 20, 19, 1500],
            ["Intermediate", 17.5, 1500, 6000, 13.375, 12.415, 6000],
            ["Intermediate-2", 12.25, 6000, 11000, 9.625, 8.681, 11000],
            ["Production", 8.5, 11000, 15000, None, None, None]]}})

    make("04_Casing_Program.xlsx", {"Casing": {
        "title": "Casing Strings",
        "headers": ["String", "OD_in", "ID_in", "Top_MD_ft",
                     "Shoe_MD_ft", "Weight_ppf", "Grade"],
        "rows": [
            ["Surface", 20, 19, 0, 1500, 94, "K55"],
            ["Intermediate", 13.375, 12.415, 0, 6000, 68, "L80"],
            ["Intermediate-2", 9.625, 8.681, 0, 11000, 47, "N80"]]}})

    make("05_BHA_String.xlsx", {"String": {
        "title": "Drillstring / BHA",
        "headers": ["Order", "Name", "Type", "OD_in", "ID_in", "Length_ft"],
        "rows": [
            [1, "DP 5\"", "DP", 5, 4.276, 12000],
            [2, "HWDP", "HWDP", 5, 3, 600],
            [3, "DC 6.5\"", "DC", 6.5, 2.8125, 360],
            [4, "MWD", "MWD", 6.75, 2.5, 30],
            [5, "Motor", "Motor", 6.75, 2.5, 25],
            [6, "Stabilizer", "Stabilizer", 8.375, 2.5, 5],
            [7, "Bit 8.5\"", "Bit", 8.5, 1.5, 1]]}})

    make("06_Mud_Properties.xlsx", {"Mud": {
        "title": "Mud Properties",
        "headers": ["Fluid_ID", "MW_ppg", "PV_cP", "YP_lbf",
                     "Fann600", "Fann300", "Fann200", "Fann100",
                     "Fann6", "Fann3", "Temp_F"],
        "rows": [
            ["MUD-13.5", 13.5, 28, 18, 74, 46, 38, 28, 8, 6, 150],
            ["MUD-10.7", 10.7, 18, 12, 48, 30, 24, 18, 5, 4, 120]]}})

    make("07_Fluid_Segments_String.xlsx", {"String_Fluids": {
        "title": "String Fluids",
        "headers": ["Fluid_ID", "MW_ppg", "Top_MD_ft", "Bottom_MD_ft"],
        "rows": [
            ["MUD-13.5", 13.5, 0, 8000],
            ["MUD-10.7", 10.7, 8000, 15000]]}})

    make("08_Fluid_Segments_Annulus.xlsx", {"Annulus_Fluids": {
        "title": "Annulus Fluids",
        "headers": ["Fluid_ID", "MW_ppg", "Top_MD_ft", "Bottom_MD_ft"],
        "rows": [
            ["MUD-10.7", 10.7, 0, 10000],
            ["MUD-13.5", 13.5, 10000, 15000]]}})

    make("09_Nozzles.xlsx", {"Nozzles": {
        "title": "Bit Nozzles",
        "headers": ["Nozzle", "Size_32nd_in", "TFA_in2"],
        "rows": [[1, 14, 0], [2, 14, 0], [3, 14, 0],
                  [4, 0, 0], [5, 0, 0], [6, 0, 0]]}})

    make("10_Pump_Data.xlsx", {"Pump": {
        "title": "Pump",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["Q_pump", 650, "gpm"], ["SPM", 60, "spm"],
                  ["SBP", 250, "psi"],
                  ["Pump Efficiency", 0.95, ""]]}})

    make("11_Temperature_Profile.xlsx", {"Geotherm": {
        "title": "Geotherm",
        "headers": ["TVD_ft", "Temp_F"],
        "rows": [[0, 90], [2000, 130], [5000, 180],
                  [8000, 220], [11000, 260], [15000, 310]]}})

    make("12_Bit_Config.xlsx", {
        "BitConfig": {
            "title": "Bit Config",
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [["Bit Diameter", 8.5, "in"], ["Cd", 0.95, ""]]},
        "Nozzles": {
            "title": "Nozzles",
            "headers": ["Nozzle", "Size_32nd_in", "TFA_in2"],
            "rows": [[1, 14, 0], [2, 14, 0], [3, 14, 0],
                      [4, 0, 0], [5, 0, 0], [6, 0, 0]]}})

    make("13_Hydraulics_Options.xlsx", {"Options": {
        "title": "Hydraulics Options",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["Flow Rate", 650, "gpm"], ["SBP", 250, "psi"],
                  ["RPM", 120, "rpm"], ["Eccentricity", 0.5, ""]]}})

    make("14_UTube_Config.xlsx", {"Config": {
        "title": "U-Tube Config",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["U-Tube Enabled", "TRUE", ""],
                  ["Choke Closed", "FALSE", ""]]}})

    make("15_Flow_Out_Data.xlsx", {"FlowOut": {
        "title": "Flow Out",
        "headers": ["Time_min", "Q_out_gpm", "Pit_Gain_bbl",
                     "Pumps_Off", "Connection"],
        "rows": [[0, 650, 0, "FALSE", "FALSE"],
                  [5, 645, 0, "FALSE", "FALSE"],
                  [10, 620, 0.5, "FALSE", "FALSE"],
                  [15, 640, 0.5, "FALSE", "TRUE"],
                  [20, 0, 3, "TRUE", "FALSE"],
                  [25, 0, 2.5, "TRUE", "FALSE"],
                  [30, 0, 1, "TRUE", "FALSE"]]}})

    make("16_Trip_Config.xlsx", {"TripConfig": {
        "title": "Trip Config",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["Direction", "out", "in/out"],
                  ["Start MD", 15000, "ft"],
                  ["End MD", 2000, "ft"],
                  ["Trip Speed", 3, "ft/s"],
                  ["Closed End", "FALSE", ""],
                  ["Time Step", 30, "s"],
                  ["Surge Target", 250, "psi"]]}})

    make("17_Cuttings_Config.xlsx", {"Cuttings": {
        "title": "Cuttings",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["ROP", 60, "ft/hr"], ["RPM", 120, "rpm"],
                  ["Cuttings Density", 21.7, "ppg"],
                  ["Cuttings Size", 0.25, "in"]]}})

    make("18_Gas_Config.xlsx", {"Gas": {
        "title": "Gas Config",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["Gas Influx", 15, "bbl"],
                  ["Gas Influx MD", 14500, "ft"],
                  ["Gas SG", 0.65, ""],
                  ["OBM Dissolved Base", 0.35, ""],
                  ["Surface Temp", 90, "F"],
                  ["Geothermal Gradient", 0.015, "F/ft"]]}})

    make("19_Events_Config.xlsx", {
        "Kick": {
            "title": "Kick Inputs",
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [["Q_in", 650, "gpm"], ["Q_out", 660, "gpm"],
                      ["Pit Gain", 0, "bbl"],
                      ["Connection Gas", 0, "units"],
                      ["Background Gas", 12, "units"],
                      ["Trip Gas", 0, "units"],
                      ["Pumps Off", "FALSE", ""],
                      ["TVD", 15000, "ft"], ["MW", 13.5, "ppg"],
                      ["Annular FP", 400, "psi"],
                      ["SBP", 250, "psi"],
                      ["Kick Duration", 0, "min"]]},
        "Nozzle": {
            "title": "Nozzle",
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [["Expected Bit dP", 1243, "psi"],
                      ["Actual Bit dP", 1243, "psi"],
                      ["TFA Expected", 0.4509, "in2"],
                      ["Cd", 0.95, ""]]},
        "Balling": {
            "title": "Balling",
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [["SPP Baseline", 3200, "psi"],
                      ["SPP Current", 3200, "psi"],
                      ["Torque Baseline", 18000, "ftlb"],
                      ["Torque Current", 18000, "ftlb"],
                      ["ROP Baseline", 60, "ft/hr"],
                      ["ROP Current", 60, "ft/hr"],
                      ["WOB Baseline", 25, "klb"],
                      ["WOB Current", 25, "klb"],
                      ["Formation", "shale", ""],
                      ["Mud Type", "OBM", ""]]},
        "PackOff": {
            "title": "Pack-Off",
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [["SPP Baseline", 3200, "psi"],
                      ["SPP Current", 3200, "psi"],
                      ["Torque Baseline", 18000, "ftlb"],
                      ["Torque Current", 18000, "ftlb"],
                      ["Drag Baseline", 30, "klb"],
                      ["Drag Current", 30, "klb"],
                      ["Flow In", 650, "gpm"],
                      ["Flow Out", 650, "gpm"]]},
        "Washout": {
            "title": "Washout",
            "headers": ["Parameter", "Value", "Unit"],
            "rows": [["SPP Baseline", 3200, "psi"],
                      ["SPP Current", 3200, "psi"],
                      ["SPP Noise Std", 20, "psi"],
                      ["Flow In", 650, "gpm"],
                      ["Flow Out", 650, "gpm"],
                      ["Q Step", 0, "gpm"],
                      ["SPP Response Ratio", 1.0, ""]]}})

    make("20_Pore_Pressure_Config.xlsx", {"Config": {
        "title": "PP Config",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["MW Normal", 8.65, "ppg"],
                  ["OBG Shallow", 14, "ppg"],
                  ["OBG Deep", 18.5, "ppg"],
                  ["Transition TVD", 8000, "ft"],
                  ["Eaton Exp dc", 1.2, ""],
                  ["Eaton Exp sigma", 1.0, ""],
                  ["W_dc", 0.40, ""], ["W_sigma", 0.20, ""],
                  ["W_gas", 0.15, ""], ["W_temp", 0.10, ""],
                  ["W_field", 0.15, ""],
                  ["Surface Temp", 90, "F"],
                  ["Geothermal Gradient", 0.015, "F/ft"]]}})

    make("21_Drilling_Events_Log.xlsx", {"Log": {
        "title": "Drilling Log",
        "headers": ["Time_min", "MD_ft", "TVD_ft", "ROP_ft_hr", "RPM",
                     "WOB_klb", "Bit_Dia_in", "MW_ppg",
                     "Torque_ftlb", "SPP_psi", "Temp_F",
                     "TotalGas", "BG", "CG", "TG", "POG",
                     "Connection", "PumpsOff"],
        "rows": [
            [0, 10000, 9500, 60, 120, 25, 8.5, 10.5, 18000, 3200,
             180, 15, 10, 0, 0, 0, "FALSE", "FALSE"],
            [60, 10100, 9600, 45, 120, 25, 8.5, 10.5, 18500, 3250,
             185, 22, 14, 0, 0, 0, "FALSE", "FALSE"],
            [90, 10130, 9630, 30, 120, 25, 8.5, 10.5, 19000, 3300,
             188, 35, 18, 55, 0, 0, "TRUE", "FALSE"],
            [150, 12000, 11400, 35, 120, 28, 8.5, 10.5, 20000, 3400,
             210, 25, 15, 0, 0, 0, "FALSE", "FALSE"],
            [210, 14000, 13200, 18, 120, 32, 8.5, 10.8, 24000, 3650,
             250, 60, 25, 0, 0, 45, "FALSE", "TRUE"],
            [270, 15300, 14300, 12, 120, 35, 8.5, 11.2, 28000, 3900,
             280, 95, 35, 0, 0, 70, "FALSE", "TRUE"]]}})

    make("22_Sensor_Config.xlsx", {"Adapter": {
        "title": "Sensor Config",
        "headers": ["Parameter", "Value", "Unit"],
        "rows": [["Adapter Type", "CSV", "CSV/WITS/WITSML"],
                  ["CSV Path", "excel_input/23_realtime_stream.csv", ""],
                  ["Tick Seconds", 1.0, "s"],
                  ["Buffer Size", 3600, "samples"]]}})

    make("30_Historical_Wells.xlsx", {"Wells": {
        "title": "Historical Wells - Calibration Dataset",
        "headers": ["Well_ID", "Formation", "MD_ft", "TVD_ft",
                     "Hole_ID_in", "Pipe_OD_in", "Pipe_ID_in",
                     "MW_in_ppg", "MW_out_ppg",
                     "Temp_in_F", "Temp_out_F", "BHT_F",
                     "Fann600", "Fann300", "Fann200", "Fann100",
                     "Fann6", "Fann3",
                     "Gels_10s", "Gels_10min",
                     "Q_gpm", "RPM", "ROP_ft_hr", "WOB_klb",
                     "SBP_psi", "Eccentricity",
                     "PWD_BHP_psi", "PWD_ECD_ppg", "SPP_psi",
                     "Q_out_gpm",
                     "HadKick", "KickSeverity", "HadLosses",
                     "LossClass",
                     "PP_ref_ppg", "FG_ref_ppg",
                     "TFA_in2", "Cd"],
        "rows": [
            ["RA-0915", "Mid_Marrat_mid", 15690, 15530,
             16.0, 5.5, 4.56, 13.50, 10.69, 115, 128, 280,
             74, 46, 38, 28, 8, 6, 8, 18,
             199.3, 80, 25, 25, 27.5, 0.3,
             9266, 11.37, 47.5, 201,
             "FALSE", "none", "FALSE", "none",
             10.75, 12.50, 0.994, 0.95],
            ["ZK-22", "Zubair_base", 10550, 10550,
             12.25, 5.0, 4.276, 13.0, 12.9, 120, 155, 240,
             65, 40, 32, 22, 7, 5, 7, 16,
             650, 120, 45, 30, 0, 0.4,
             5900, 13.05, 3150, 655,
             "FALSE", "none", "FALSE", "none",
             11.20, 17.20, 0.45, 0.95],
            ["MK-44", "Makhul", 12729, 12729,
             8.5, 5.0, 4.276, 16.4, 15.8, 130, 175, 265,
             85, 52, 42, 30, 10, 7, 9, 22,
             800, 100, 35, 28, 150, 0.5,
             9100, 16.55, 3450, 815,
             "TRUE", "moderate", "FALSE", "none",
             15.05, 18.20, 0.994, 0.95],
            ["RT-08", "Ratawi_LS", 11185, 11185,
             12.25, 5.5, 4.56, 14.8, 14.7, 125, 160, 250,
             78, 48, 38, 27, 9, 6, 8, 20,
             720, 110, 50, 32, 0, 0.45,
             7600, 13.25, 3300, 640,
             "FALSE", "none", "TRUE", "partial",
             13.05, 17.80, 0.994, 0.95],
            ["GT-15", "Gotnia", 13980, 13980,
             8.5, 5.0, 4.276, 19.8, 19.7, 135, 185, 290,
             120, 72, 58, 42, 14, 10, 12, 28,
             620, 90, 20, 35, 200, 0.55,
             12800, 19.75, 4100, 615,
             "FALSE", "none", "FALSE", "none",
             18.45, 18.90, 0.994, 0.95]]}})

    # Output placeholders
    for name, sheets in [
        ("90_Output_Geometry.xlsx", {"Volumes": {
            "title": "Computed Volumes",
            "headers": ["Item", "Value", "Unit"],
            "rows": [["String Internal Volume", None, "bbl"],
                      ["String Displacement", None, "bbl"],
                      ["Annular Volume", None, "bbl"],
                      ["Open Hole Volume", None, "bbl"],
                      ["Cased Hole Volume", None, "bbl"]]}}),
        ("91_Output_Hydrostatic.xlsx", {
            "String": {
                "title": "String Hydrostatic",
                "headers": ["Fluid", "MW", "Top_MD", "Bot_MD",
                             "Top_TVD", "Bot_TVD", "Vol", "Ph_psi"],
                "rows": []},
            "Annulus": {
                "title": "Annulus Hydrostatic",
                "headers": ["Fluid", "MW", "Top_MD", "Bot_MD",
                             "Top_TVD", "Bot_TVD", "Vol", "Ph_psi"],
                "rows": []},
            "UTube": {
                "title": "U-Tube",
                "headers": ["Item", "Value", "Unit"],
                "rows": [["String Ph", None, "psi"],
                          ["Annulus Ph", None, "psi"],
                          ["U-Tube dP", None, "psi"]]}}),
        ("92_Output_Pressure_Ledger.xlsx", {"Ledger": {
            "title": "Pressure Ledger",
            "headers": ["Component", "Value_psi"],
            "rows": [["Hydrostatic (String)", None],
                      ["Hydrostatic (Annulus)", None],
                      ["Pipe Friction", None],
                      ["Annular Friction", None],
                      ["Bit dP", None], ["SBP", None],
                      ["U-Tube", None], ["Surge", None],
                      ["Swab", None], ["Gas Effect", None],
                      ["Loss Effect", None], ["BHP", None],
                      ["ECD (ppg)", None]]}}),
        ("A6_Dashboard.xlsx", {
            "Dashboard": {
                "title": "ARHPP Final Dashboard",
                "headers": ["Item", "Value"],
                "rows": []},
            "Alerts": {
                "title": "Alerts",
                "headers": ["Alert"],
                "rows": []}}),
    ]:
        make(name, sheets)

    print(f"\nDone. Files in: {OUT}\n")


if __name__ == "__main__":
    build_all()
