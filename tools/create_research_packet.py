from __future__ import annotations
import argparse, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from aggie_analytics.experimentation.contracts import ExperimentResultPacket

def main() -> int:
    ap=argparse.ArgumentParser(description="Validate a research-plane result packet; protected metrics are forbidden.")
    ap.add_argument("packet_json", type=Path)
    args=ap.parse_args()
    data=json.loads(args.packet_json.read_text(encoding="utf-8"))
    pkt=ExperimentResultPacket(**data)
    pkt.validate()
    print(json.dumps({"result_id":pkt.result_id,"validated":True,"protected_metrics":False},indent=2))
    return 0
if __name__=="__main__": raise SystemExit(main())
