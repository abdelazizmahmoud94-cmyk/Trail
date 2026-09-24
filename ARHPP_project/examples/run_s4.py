"""ARHPP S4 — ML training + predictions."""

from arhpp.ml.trainer import train_all
from arhpp.ml.predictors import MLPredictor
from arhpp.ml.features import extract_features


def _demo_signatures():
    normal = {
        "q_in": 650, "q_out": 651, "spp": 3200,
        "rop": 45, "rpm": 120, "wob": 25, "torque": 18000,
        "mw_in": 13.5, "mw_out": 13.48, "temp_out": 180,
        "bg": 12, "cg": 0, "tg": 0, "pog": 0,
        "pit_volume": 4200, "pit_gain": 0}
    kick = dict(normal)
    kick.update({"q_out": 720, "bhp": 9300, "mw_out": 12.0,
                  "bg": 55, "cg": 80, "pit_gain": 12})
    loss = dict(normal)
    loss.update({"q_out": 520, "spp": 2750, "ann_fp": 250,
                  "pit_gain": -5})
    packoff = dict(normal)
    packoff.update({"q_out": 550, "spp": 4100,
                     "torque": 24000, "wob": 30})
    return {"normal": normal, "kick": kick,
             "loss": loss, "packoff": packoff}


def main():
    print("ARHPP — S4 ML Enhancement\n" + "=" * 70)
    print("\n[Training models]")
    report = train_all(n_per_class=250, verbose=True)

    print("\n[Demo predictions]")
    predictor = MLPredictor.get()
    sigs = _demo_signatures()
    print(f"\n  {'Case':<12}{'Anomaly':>10}{'Kick P':>10}{'Loss P':>10}")
    print("  " + "-" * 42)
    for name, reading in sigs.items():
        feats = extract_features([reading])
        pred = predictor.predict(feats)
        print(f"  {name:<12}"
              f"{pred.anomaly.normalized_score:>10.3f}"
              f"{pred.kick.probability:>10.3f}"
              f"{pred.loss.probability:>10.3f}")

    print("\n" + "=" * 70)


