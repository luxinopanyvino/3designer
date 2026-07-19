import pytest
import trimesh

from app.services.mesh_service import (
    DegenerateMeshError,
    analyze_stl,
    convert_stl_to_glb,
    supported_export_formats,
)


@pytest.fixture(scope="module")
def box_stl(tmp_path_factory):
    out = tmp_path_factory.mktemp("box")
    stl = out / "model.stl"
    box = trimesh.creation.box(extents=(30, 20, 10))
    box.apply_translation([0, 0, 5])  # rest on the bed (z >= 0)
    box.export(stl)
    return stl


def test_analyze_box(box_stl):
    info = analyze_stl(box_stl)
    assert info.dimensions_mm == {"x": 30.0, "y": 20.0, "z": 10.0}
    assert info.watertight
    assert info.volume_mm3 == pytest.approx(6000.0, rel=0.01)
    assert info.warnings == []


def test_bed_overflow_warning(box_stl):
    info = analyze_stl(box_stl, bed_size_mm=25.0)
    assert any("build plate" in w for w in info.warnings)


def test_overhang_warning(tmp_path):
    # 60mm horizontal bar on top of a thin column: big flat overhangs
    column = trimesh.creation.box(extents=(6, 6, 30))
    column.apply_translation([0, 0, 15])
    bar = trimesh.creation.box(extents=(60, 20, 6))
    bar.apply_translation([0, 0, 33])
    stl = tmp_path / "t_shape.stl"
    trimesh.util.concatenate([column, bar]).export(stl)

    info = analyze_stl(stl)
    assert any("overhang" in w for w in info.warnings)


def test_degenerate_flat_mesh(tmp_path):
    stl = tmp_path / "flat.stl"
    trimesh.Trimesh(
        vertices=[[0, 0, 0], [10, 0, 0], [0, 10, 0]], faces=[[0, 1, 2]]
    ).export(stl)
    with pytest.raises(DegenerateMeshError):
        analyze_stl(stl)


def test_glb_conversion(box_stl, tmp_path):
    glb = tmp_path / "model.glb"
    convert_stl_to_glb(box_stl, glb)
    assert glb.stat().st_size > 0
    reloaded = trimesh.load(glb, force="mesh")
    extents = reloaded.bounds[1] - reloaded.bounds[0]
    assert extents[0] == pytest.approx(30.0, abs=0.1)  # still millimeters


def test_supported_formats_contract():
    formats = supported_export_formats()
    assert "stl" in formats
    assert "step" not in formats
