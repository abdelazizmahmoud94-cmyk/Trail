"""Full integration: WITS -> ARHPP -> PLC -> Dashboard."""

import socket
import time
import threading
import logging

logging.basicConfig(level=logging.INFO,
                      format="%(asctime)s [%(threadName)-15s] %(levelname)s %(message)s")

from arhpp.sensors.bridge import WITS2PLC, BridgeConfig


def mudlogger_simulator(duration_s=30.0):
    time.sleep(2.0)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(("127.0.0.1", 14200))
        print("[MUDLOGGER] Connected")
    except Exception as e:
        print(f"[MUDLOGGER] Connect failed: {e}")
        return
    t0 = time.time()
    tick = 0
    while time.time() - t0 < duration_s:
        if time.time() - t0 > 15.0:
            q_out = 650.0 + 100.0 * min(
                1.0, (time.time() - t0 - 15.0) / 5.0)
            pit_gain = min(10.0, (time.time() - t0 - 15.0) * 2.0)
            gas_bg = 25.0 + 100.0 * min(
                1.0, (time.time() - t0 - 15.0) / 5.0)
        else:
            q_out = 650.0
            pit_gain = 0.0
            gas_bg = 15.0
        line = (f"0108 14550.0 0120 80.0 0122 3200.0 "
                f"0128 650.0 0132 {q_out:.1f} 0136 12.5 "
                f"0141 {gas_bg:.1f} 0148 0.0 0150 250.0 "
                f"0913 9500.0 0915 11.30\n")
        sock.sendall(line.encode("utf-8"))
        tick += 1
        time.sleep(0.2)
    sock.close()
    print(f"[MUDLOGGER] Sent {tick} records")


def main():
    print("=" * 70)
    print("  ARHPP - Full Integration Example")
    print("=" * 70)
    bridge = WITS2PLC(BridgeConfig(
        wits_enabled=True, wits_port=14200,
        plc_enabled=True, plc_rate_hz=50.0,
        physics_rate_hz=10.0, sensor_update_rate_hz=10.0))
    ml_thread = threading.Thread(target=mudlogger_simulator,
                                    args=(25.0,), daemon=True)
    ml_thread.start()
    print("\nStarting Bridge...")
    bridge.start()
    time.sleep(1.0)
    if bridge.plc:
        bridge.plc.kick_auto_arm()
        print("Kick Auto-Control armed")

    print("\nMonitoring...")
    print("-" * 70)
    print(f"{'t':>5} {'SPP':>8} {'Q_in':>7} {'Q_out':>7} "
          f"{'BHP':>9} {'ECD':>7} {'Kick':>6} {'Loss':>6} "
          f"{'ChokeA%':>8} {'Safe':>5}")
    print("-" * 70)
    t0 = time.time()
    try:
        while time.time() - t0 < 22.0:
            time.sleep(1.0)
            arhpp = bridge.get_arhpp_result()
            wits = bridge.get_latest_wits()
            if not wits or not arhpp:
                continue
            inp = wits.arhpp_inputs
            plc_status = (bridge.plc.get_status()
                            if bridge.plc else None)
            choke_a = (bridge.plc.get_choke_feedback("CHOKE-A")
                        if bridge.plc else None)
            print(f"{time.time()-t0:>5.1f} "
                  f"{inp.get('spp_psi',0):>8.1f} "
                  f"{inp.get('q_in_gpm',0):>7.1f} "
                  f"{inp.get('q_out_gpm',0):>7.1f} "
                  f"{arhpp.get('bhp_psi',0):>9.1f} "
                  f"{arhpp.get('ecd_ppg',0):>7.3f} "
                  f"{arhpp.get('kick_probability',0)*100:>5.0f}% "
                  f"{arhpp.get('loss_fraction',0)*100:>5.1f}% "
                  f"{choke_a['actual_pct'] if choke_a else 0:>8.2f} "
                  f"{'YES' if plc_status and plc_status.safe_mode else 'no':>5}")
    except KeyboardInterrupt:
        pass
    print("\nStopping Bridge...")
    bridge.stop()
    print("=" * 70)


