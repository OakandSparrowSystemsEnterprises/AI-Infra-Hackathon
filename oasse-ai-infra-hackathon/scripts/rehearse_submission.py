"""Repeatable rehearsal: no auto-installs, hardware commands, or online submission."""
from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

from oasse_physical_ai.evidence_bundle import verify_bundle
from oasse_physical_ai.readiness import environment_report, readiness


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',required=True,help='New, empty directory outside the source tree')
    parser.add_argument('--profile',choices=['reference','native'],default='reference')
    parser.add_argument('--gatekeeper-probe',help='Previously recorded non-actuating endpoint probe')
    parser.add_argument('--onsite-acceptance',help='Operator attestation JSON, not a safety certification')
    args=parser.parse_args()
    app=Path(__file__).resolve().parents[1]
    output=Path(args.output).resolve()
    if output.is_relative_to(app.parent): raise ValueError('rehearsal artifacts must be outside source')
    if output.exists() and any(output.iterdir()): raise ValueError('output must be new or empty')
    output.mkdir(parents=True,exist_ok=True)
    sha=subprocess.check_output(['git','rev-parse','HEAD'],cwd=app,text=True).strip()
    dirty=bool(subprocess.check_output(['git','status','--porcelain'],cwd=app,text=True).strip())
    env=os.environ.copy()
    # Every rehearsal uses local reference authority. Live endpoint checks are separate and non-actuating.
    for key in ('GATEKEEPER_URL','GATEKEEPER_TOKEN','EVIDENCE_MAX_AGE_MS','MIN_CONFIDENCE','MAX_SPEED_MPS'):
        env.pop(key,None)
    env['AUTHORITY_MODE']='reference'
    if args.profile=='native':
        for name in ('mujoco','openvino'): importlib.import_module(name)
        env['OASSE_NATIVE_CAMERA_TESTS']='1'
    else:
        env.pop('OASSE_NATIVE_CAMERA_TESTS',None)
    commands=[['-m','pytest','tests','-q','--junitxml='+str(output/'tests.xml')],
              ['scripts/run_demo.py']]
    if args.profile=='native':
        commands.extend([['scripts/run_mujoco_demo.py','--output',str(output/'mujoco.json')],
            ['scripts/run_native_vision_demo.py','--output',str(output/'vision.json'),'--artifacts-dir',str(output/'vision')],
            ['scripts/run_inspection_demo.py','--bundle',str(output/'inspection'),'--zip',str(output/'inspection.zip')]])
    records=[]
    for index,command in enumerate(commands):
        started=time.monotonic()
        log=output/f'command-{index}.txt'
        with log.open('w',encoding='utf-8') as stream:
            try:
                run=subprocess.run([sys.executable,*command],cwd=app,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=300,check=False)
                code=run.returncode
            except subprocess.TimeoutExpired:
                code=124
        records.append({'command':[sys.executable,*command],'returncode':code,'log':log.name,'elapsed_s':time.monotonic()-started})
        if code: break
    passed=len(records)==len(commands) and all(item['returncode']==0 for item in records)
    counts={}
    if (output/'tests.xml').exists():
        suites=ET.parse(output/'tests.xml').getroot()
        for key in ('tests','failures','errors','skipped'):
            counts[key]=sum(int(s.get(key,'0')) for s in suites.iter('testsuite'))
        passed &= counts.get('tests',0)>0 and counts.get('errors',0)==0 and counts.get('failures',0)==0
        if args.profile=='native': passed &= counts.get('skipped',0)==0
    manifest=None
    if passed and args.profile=='native': manifest=verify_bundle(output/'inspection')['manifest_sha256']
    probe=json.loads(Path(args.gatekeeper_probe).read_text()) if args.gatekeeper_probe else None
    acceptance=json.loads(Path(args.onsite_acceptance).read_text()) if args.onsite_acceptance else None
    report={'schema':'oasse.submission-rehearsal.v1','source_commit':sha,'source_dirty':dirty,
        'profile':args.profile,'passed':bool(passed),'tests':counts,'commands':records,'environment':environment_report(),
        'inspection_manifest_sha256':manifest,
        'readiness':readiness(bool(passed and not dirty and args.profile=='native'),gatekeeper_probe=probe,onsite_acceptance=acceptance),
        'submitted':False,'physical_hardware_commanded':False}
    (output/'rehearsal.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    versions=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
    (output/'installed-versions.txt').write_text(versions,encoding='utf-8')
    print(json.dumps({'passed':bool(passed),'tests':counts,'readiness':report['readiness'],'report':str(output/'rehearsal.json')},indent=2))
    if not passed: raise SystemExit(1)


if __name__=='__main__': main()
