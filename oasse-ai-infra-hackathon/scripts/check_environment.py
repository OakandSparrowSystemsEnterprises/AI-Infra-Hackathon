"""Report installed runtime capabilities without installing or moving hardware."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from oasse_physical_ai.readiness import environment_report


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output')
    parser.add_argument('--native',action='store_true',help='Import MuJoCo/OpenVINO and enumerate OpenVINO devices; no camera or robot commands')
    args=parser.parse_args()
    report=environment_report()
    if args.native:
        errors=[]
        try:
            import mujoco
            report['mujoco_version']=mujoco.__version__
        except Exception as exc:
            errors.append({'component':'mujoco','error_type':type(exc).__name__})
        try:
            import openvino as ov
            report['openvino_version']=ov.__version__
            report['openvino_available_devices']=list(ov.Core().available_devices)
        except Exception as exc:
            errors.append({'component':'openvino','error_type':type(exc).__name__})
        report['native_import_errors']=errors
    encoded=json.dumps(report,indent=2,allow_nan=False)
    print(encoded)
    if args.output: Path(args.output).write_text(encoded+'\n',encoding='utf-8')
    if args.native and report['native_import_errors']: raise SystemExit(1)


if __name__=='__main__': main()
