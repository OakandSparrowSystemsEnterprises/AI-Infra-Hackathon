from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import httpx
import numpy as np
import pytest

from oasse_physical_ai.models import EvidenceFrame, ProposedAction
from oasse_physical_ai.orchestrator import PhysicalAIOrchestrator
from oasse_physical_ai.policy import ReferenceAuthorityEngine
from oasse_physical_ai.providers.actuator import SimulatedActuator
from oasse_physical_ai.providers.anomalib_decoder import AnomalibDecoder, AnomalibOutputContract
from oasse_physical_ai.providers.opencv_camera import CameraContext, OpenCVRGBSource
from oasse_physical_ai.providers.openvino_runtime import RGBSpec
from oasse_physical_ai.tasks import InspectionTask
from oasse_physical_ai.live_probe import endpoint_url, probe_gatekeeper
from oasse_physical_ai.readiness import readiness
from oasse_physical_ai.evidence_bundle import verify_receipts, verify_record, write_bundle, verify_bundle, rgb_png


def observation(action, **extra):
    return {"object_id":action.object_id,"observed_bin":action.target_bin,"object_released":True,
            "object_speed_mps":0.,"observation_source":"test-measured-fixture",
            "observed_at_ms":int(time.time()*1000),**extra}


class CountingActuator(SimulatedActuator):
    def __init__(self): self.calls=0
    def execute(self,action):
        self.calls+=1
        return super().execute(action)


def test_complete_requires_postcondition_and_is_idempotent():
    actuator=CountingActuator()
    orch=PhysicalAIOrchestrator(actuator=actuator)
    task=InspectionTask(orch,observation)
    result=task.run()
    assert result['task_complete'] and result['status']=='COMPLETE'
    result['status']='corrupted-by-caller'
    assert task.run()['status']=='COMPLETE' and actuator.calls==1
    assert len(orch.receipts.all())==3 and orch.receipts.verify()


@pytest.mark.parametrize('scenario,status', [('stale','HELD'),('occupied','DENIED'),('identity_mismatch','DENIED'),('low_confidence','HELD')])
def test_blocked_tasks_do_not_verify_or_execute(scenario,status):
    def wrong(_): pytest.fail('verification should not run without execution')
    actuator=CountingActuator(); orch=PhysicalAIOrchestrator(actuator=actuator)
    result=InspectionTask(orch,wrong).run(scenario)
    assert result['status']==status and not result['task_complete'] and actuator.calls==0
    assert orch.receipts.verify()


@pytest.mark.parametrize('extra', [
    {'observed_bin':'elsewhere'},{'object_released':False},{'object_released':'true'},
    {'object_speed_mps':.2},{'object_id':'different'},{'observed_at_ms':0},
    {'observed_at_ms':9999999999999},{'object_speed_mps':float('nan')},
    {'object_speed_mps':True},{'observation_source':''}])
def test_bad_postconditions_never_complete(extra):
    orch=PhysicalAIOrchestrator()
    result=InspectionTask(orch,lambda a:observation(a,**extra)).run()
    assert result['execution_confirmed'] and not result['task_complete']
    assert orch.receipts.verify()


def test_task_concurrent_calls_only_dispatch_once():
    actuator=CountingActuator()
    task=InspectionTask(PhysicalAIOrchestrator(actuator=actuator),observation)
    threads=[threading.Thread(target=task.run) for _ in range(10)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert actuator.calls==1


def test_task_failure_does_not_leak_exception_message():
    def error(_): raise RuntimeError('private-key-contents')
    result=InspectionTask(PhysicalAIOrchestrator(),error).run()
    assert result['status']=='UNKNOWN' and 'private-key-contents' not in json.dumps(result)


def decoder():
    return AnomalibDecoder(AnomalibOutputContract(image_threshold=2.,pixel_threshold=1.5,
        confidence=.9,calibration_id='held-out-calibration-fixture'))


def test_anomalib_raw_scores_are_thresholded_not_falsely_normalized():
    outputs={'pred_score':np.array([4.]),'anomaly_map':np.zeros((1,1,8,8))}
    outputs['anomaly_map'][0,0,2:4,1:3]=4.
    decoded=decoder()(outputs,RGBSpec(8,8))
    assert decoded['anomaly_score']==1. and decoded['metadata']['raw_anomaly_score']==4.
    assert decoded['anomaly_bbox_xyxy']==[1/8,2/8,3/8,4/8]
    assert decoded['metadata']['score_encoding']=='binary-threshold-not-probability'


def test_anomalib_normal_classification_has_no_defect_box():
    result=decoder()({'pred_score':np.array([.2]),'anomaly_map':np.zeros((1,8,8))},RGBSpec(8,8))
    assert result['anomaly_score']==0. and result['anomaly_bbox_xyxy'] is None


@pytest.mark.parametrize('outputs', [
    {},{'pred_score':np.array([4.]),'anomaly_map':np.zeros((1,8,8))},
    {'pred_score':np.array([np.nan]),'anomaly_map':np.zeros((1,8,8))},
    {'pred_score':np.array([True]),'anomaly_map':np.zeros((1,8,8))},
    {'pred_score':np.array([1.,2.]),'anomaly_map':np.zeros((1,8,8))},
    {'pred_score':np.array([.2]),'anomaly_map':np.zeros((8,8))},
    {'pred_score':np.array([.2]),'anomaly_map':np.full((1,8,8),np.inf)},
    {'pred_score':np.array([.2]),'anomaly_map':np.full((1,8,8),-1)}])
def test_bad_anomalib_outputs_rejected(outputs):
    with pytest.raises((TypeError,ValueError,KeyError)): decoder()(outputs,RGBSpec(8,8))


class Capture:
    def __init__(self,frame=None):
        self.frame=np.full((8,8,3),[10,20,30],dtype=np.uint8) if frame is None else frame
        self.closed=False
    def isOpened(self): return not self.closed
    def set(self,*args): return True
    def read(self): return True,self.frame
    def release(self): self.closed=True


def source(context=None,capture=None):
    capture=capture or Capture()
    provider=context or (lambda:CameraContext(int(time.time()*1000),True,'test-workspace-sensor'))
    return OpenCVRGBSource(0,RGBSpec(8,8),provider,camera_id='physical-interface-test',capture_factory=lambda _:capture)


def test_opencv_converts_bgr_to_rgb_and_copies_buffer():
    capture=Capture()
    with source(capture=capture) as camera:
        first=camera.capture(); second=camera.capture()
        assert first.data[:3]==bytes([30,20,10]) and second.sequence==first.sequence+1
        capture.frame[:]=0
        assert first.data[:3]==bytes([30,20,10])
    assert capture.closed
    with pytest.raises(RuntimeError): camera.capture()


@pytest.mark.parametrize('frame',[np.zeros((7,8,3),dtype=np.uint8),np.zeros((8,8,4),dtype=np.uint8),np.zeros((8,8,3),dtype=float)])
def test_opencv_refuses_unexpected_resolution_or_dtype(frame):
    with source(capture=Capture(frame)) as camera:
        with pytest.raises(ValueError): camera.capture()


@pytest.mark.parametrize('context', [
    lambda:CameraContext(0,True,'sensor'),
    lambda:CameraContext(int(time.time()*1000)+10000,True,'sensor'),
    lambda:CameraContext(int(time.time()*1000),'true','sensor'),
    lambda:CameraContext(int(time.time()*1000),True,'unspecified'),
    lambda:CameraContext(int(time.time()*1000),True,'sensor',object_dimensions_xyz=(0.,1.,1.)),
    lambda:{}])
def test_camera_missing_or_stale_context_is_not_clear_workspace(context):
    with source(context=context) as camera:
        with pytest.raises((TypeError,ValueError)): camera.capture()


@pytest.mark.parametrize('url',[ '', 'http://example.com', 'https://u:p@example.com', 'https://example.com?token=x',
                               'https://example.com#x','https://example.com/v1/evaluate','file:///tmp/x'])
def test_unsafe_endpoint_configuration_is_rejected(url):
    with pytest.raises((TypeError,ValueError)): endpoint_url(url)


def responder(request):
    body=json.loads(request.content)
    decision=ReferenceAuthorityEngine().evaluate(EvidenceFrame(**body['evidence']),ProposedAction(**body['action']))
    return httpx.Response(200,json=decision.to_dict())


def test_probe_passes_contract_without_actuation():
    report=probe_gatekeeper('https://gatekeeper.test',expected_policy_version='physical-ai-demo-v1',transport=httpx.MockTransport(responder))
    assert report['passed'] and len(report['checks'])==6 and report['actuator_calls']==0
    assert report['connection_mode']=='injected-test-transport'
    assert not readiness(True,gatekeeper_probe=report)['onsite_submission_ready']


def test_probe_wrong_policy_fails_even_when_verdicts_match():
    report=probe_gatekeeper('https://gatekeeper.test',expected_policy_version='different',transport=httpx.MockTransport(responder))
    assert not report['passed'] and all(not check['passed'] for check in report['checks'])


def test_probe_outage_is_not_a_passing_hold():
    def down(request): raise httpx.ConnectError('offline',request=request)
    report=probe_gatekeeper('https://gatekeeper.test',expected_policy_version='deployment-v1',transport=httpx.MockTransport(down))
    assert not report['passed'] and all(not c['passed'] for c in report['checks'])


def test_real_http_loopback_contract():
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path=='/v1/evaluate'
            data=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            d=ReferenceAuthorityEngine().evaluate(EvidenceFrame(**data['evidence']),ProposedAction(**data['action']))
            encoded=json.dumps(d.to_dict()).encode()
            self.send_response(200); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(encoded))); self.end_headers(); self.wfile.write(encoded)
        def log_message(self,*args): pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever);thread.start()
    try:
        report=probe_gatekeeper(f'http://127.0.0.1:{server.server_port}',
            expected_policy_version='physical-ai-demo-v1',allow_loopback_http=True)
        assert report['passed'] and report['connection_mode']=='http-network'
    finally: server.shutdown();server.server_close();thread.join()


def record():
    orch=PhysicalAIOrchestrator();task=InspectionTask(orch,observation).run()
    return {'schema':'oasse.inspection-rehearsal.v1','source_commit':'a'*40,
            'cases':[{'scenario':'normal_sort','expected_task_complete':True,'task':task,
                      'physics_steps':0,'receipts':[r.to_dict() for r in orch.receipts.all()]}]}


def test_bundle_integrity_and_task_binding(tmp_path):
    data=record(); root=tmp_path/'bundle'
    digest=write_bundle(root,data)
    assert verify_bundle(root,expected_manifest_sha256=digest)['verified']
    (root/'record.json').write_text('{}')
    with pytest.raises(ValueError): verify_bundle(root)


def test_external_receipt_verifier_detects_tampering():
    data=record();receipts=data['cases'][0]['receipts'];verify_receipts(receipts)
    receipts[-1]['payload']['task_complete']=False
    with pytest.raises(ValueError): verify_receipts(receipts)


def test_record_cannot_claim_different_bin_from_sealed_task():
    data=record();data['cases'][0]['task']['requested_bin']='reject'
    with pytest.raises(ValueError):verify_record(data)


def test_bundle_unknown_files_rejected(tmp_path):
    root=tmp_path/'bundle';write_bundle(root,record());(root/'secret.txt').write_text('unexpected')
    with pytest.raises(ValueError):verify_bundle(root)


@pytest.mark.parametrize('name',['../escape.txt','/absolute.txt','x/../../e.txt','x\\e.txt','manifest.json','run.py'])
def test_bundle_does_not_accept_arbitrary_paths_or_code(tmp_path,name):
    with pytest.raises(ValueError):write_bundle(tmp_path/'bundle',record(),{name:b'no'})


def test_png_roundtrip():
    import struct, zlib
    pixels=bytes(range(192)); data=rgb_png(pixels,8,8)
    assert data[:8]==b'\x89PNG\r\n\x1a\n'
    offset=8; blocks=[]
    while offset<len(data):
        size=struct.unpack('>I',data[offset:offset+4])[0]
        name=data[offset+4:offset+8]; payload=data[offset+8:offset+8+size]
        crc=struct.unpack('>I',data[offset+8+size:offset+12+size])[0]
        assert zlib.crc32(name+payload)&0xffffffff==crc
        if name==b'IDAT': blocks.append(payload)
        offset+=12+size
    raw=zlib.decompress(b''.join(blocks))
    assert b''.join(raw[y*25+1:(y+1)*25] for y in range(8))==pixels


def test_rehearsal_success_never_implies_onsite_completion():
    report=readiness(True)
    assert report['rehearsal_ready'] and not report['onsite_submission_ready']
    assert 'live_authority_contract' in report['remaining'] and 'camera_calibration' in report['remaining']


def test_interrupted_receipt_cannot_retry_a_task():
    actuator=CountingActuator(); orch=PhysicalAIOrchestrator(actuator=actuator)
    task=InspectionTask(orch,observation); seal=orch.receipts.seal
    def fail_last(kind,payload):
        if kind=='TASK_VERIFICATION': raise OSError('disk unavailable')
        return seal(kind,payload)
    orch.receipts.seal=fail_last
    with pytest.raises(OSError): task.run()
    orch.receipts.seal=seal
    with pytest.raises(RuntimeError,match='NO_AUTOMATIC_RETRY'): task.run()
    assert actuator.calls==1


def test_verifier_cannot_corrupt_chain_and_still_complete():
    from oasse_physical_ai.orchestrator import ReceiptIntegrityError
    orch=PhysicalAIOrchestrator()
    def tamper(action):
        orch.receipts.all()[0].payload['bad']=True
        return observation(action)
    task=InspectionTask(orch,tamper)
    with pytest.raises(ReceiptIntegrityError): task.run()
    with pytest.raises(RuntimeError,match='NO_AUTOMATIC_RETRY'): task.run()


def test_forged_empty_or_loopback_probe_cannot_establish_live_readiness():
    report=probe_gatekeeper('https://localhost',expected_policy_version='physical-ai-demo-v1',transport=httpx.MockTransport(responder))
    report['connection_mode']='http-network'
    assert not readiness(True,gatekeeper_probe=report)['checks']['live_authority_contract']
    report.update(endpoint='https://example.test',endpoint_scope='configured-service',checks=[])
    assert not readiness(True,gatekeeper_probe=report)['checks']['live_authority_contract']


def test_echoed_token_is_redacted_even_when_json_escaped():
    token='quoted"secret\\value'
    def echo(request):
        response=responder(request); data=response.json();data['reason_codes']=[token]
        return httpx.Response(200,json=data)
    report=probe_gatekeeper('https://gatekeeper.test',expected_policy_version='physical-ai-demo-v1',token=token,transport=httpx.MockTransport(echo))
    assert report['checks'][0]['reason_codes']==['[REDACTED]']
