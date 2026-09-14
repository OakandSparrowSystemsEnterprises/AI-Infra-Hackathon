from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
pytest.importorskip("openvino")

from oasse_physical_ai.providers.openvino_runtime import (
    RGBSpec, RGBFrame, NativeOpenVINOPerception, ReferenceDifferenceDecoder,
    OpenVINOIRRunner, export_reference_difference,
)


@pytest.fixture(scope="module")
def runner(tmp_path_factory):
    spec = RGBSpec(16,16)
    path = tmp_path_factory.mktemp("hardened-native") / "model.xml"
    digest = export_reference_difference(bytes([200])*(16*16*3), spec, path)
    return OpenVINOIRRunner(path,spec,expected_sha256=digest)


@pytest.mark.parametrize("changes", [
    {"data": 16*16*3}, {"data": [0]*(16*16*3)}, {"data": None},
    {"data": b""}, {"captured_at_ms": True}, {"captured_at_ms": -1},
    {"sequence": True}, {"scene_hash": {}}, {"camera_id": " "}])
def test_bad_frame_rejected_before_native_inference(runner,changes):
    frame = RGBFrame(bytes([200])*(16*16*3),1700000000000,"camera",1,
                     width=16,height=16,workspace_clear=True,context_source="test-context")
    class Source:
        def capture(self): return replace(frame,**changes)
    before=runner.calls
    with pytest.raises((TypeError,ValueError)):
        NativeOpenVINOPerception(Source(),runner,ReferenceDifferenceDecoder()).observe()
    assert runner.calls == before


def test_parallel_inferences_keep_their_own_provenance(runner):
    before=runner.calls
    data=bytes([200])*(16*16*3)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:runner.infer_with_provenance(data),range(16)))
    indexes=[record[1]["native_inference_calls"] for record in results]
    assert sorted(indexes) == list(range(before+1,before+17))
    runner.infer(data)
    assert [record[1]["native_inference_calls"] for record in results] == indexes
    assert all(record[1]["native_inference_ms"]>=0 for record in results)


def test_invalid_model_sources_fail_without_fallback(tmp_path):
    directory=tmp_path / "not-a-file.xml"
    directory.mkdir()
    with pytest.raises(ValueError): OpenVINOIRRunner(directory,RGBSpec())
    empty=tmp_path / "empty.xml"; empty.write_bytes(b""); empty.with_suffix(".bin").write_bytes(b"")
    with pytest.raises(ValueError,match="empty"): OpenVINOIRRunner(empty,RGBSpec())
