"""Tests: the image & data suites' LIVE branches (R51 wave 1).

Every operation runs on a REAL generated PNG; error paths use genuinely
missing files. No mock of the suite itself.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from universal_mind.data_suite import DataSuite

from pathlib import Path

from PIL import Image


def _png(tmp_path: Path, name: str = "in.png", size: tuple[int, int] = (60, 40)) -> Path:
    p = tmp_path / name
    Image.new("RGB", size, (200, 30, 30)).save(p)
    return p


class TestImageOps:
    def test_convert_to_jpeg_makes_a_real_file(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        p = _png(tmp_path)
        r = ImageSuite().convert(str(p), "JPEG")
        assert r["ok"] is True
        assert Path(r["path"]).exists()
        assert r["bytes"] > 0

    def test_convert_missing_file_names_it(self) -> None:
        from universal_mind.image_suite import ImageSuite

        r = ImageSuite().convert("Z:/no.png", "PNG")
        assert r["ok"] is False
        assert "file not found" in r["error"]

    def test_convert_a_broken_image_names_the_error(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        bad = tmp_path / "bad.png"
        bad.write_bytes(b"not an image")
        r = ImageSuite().convert(str(bad), "PNG")
        assert r["ok"] is False
        assert r["error"]

    def test_resize_makes_exact_dimensions(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        p = _png(tmp_path)
        r = ImageSuite().resize(str(p), 30, 20)
        assert r["ok"] is True
        with Image.open(r["path"]) as im:
            assert im.size == (30, 20)

    def test_resize_missing_file_names_it(self) -> None:
        from universal_mind.image_suite import ImageSuite

        assert "file not found" in ImageSuite().resize("Z:/no.png", 1, 1)["error"]

    def test_crop_makes_a_real_region(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        p = _png(tmp_path)
        r = ImageSuite().crop(str(p), (0, 0, 10, 10))
        assert r["ok"] is True
        with Image.open(r["path"]) as im:
            assert im.size == (10, 10)

    def test_crop_missing_file_names_it(self) -> None:
        from universal_mind.image_suite import ImageSuite

        assert "file not found" in ImageSuite().crop("Z:/no.png", (0, 0, 1, 1))["error"]

    def test_rotate_expands_the_canvas(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        p = _png(tmp_path, size=(40, 10))
        r = ImageSuite().rotate(str(p), 90)
        assert r["ok"] is True
        with Image.open(r["path"]) as im:
            assert im.size == (10, 40)  # expand=True on a 90° turn

    def test_rotate_missing_file_names_it(self) -> None:
        from universal_mind.image_suite import ImageSuite

        assert "file not found" in ImageSuite().rotate("Z:/no.png", 45)["error"]

    def test_filter_blur_makes_a_real_file(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        p = _png(tmp_path)
        for kind in ("blur", "sharpen", "contour", "edge_enhance", "grayscale"):
            r = ImageSuite().filter(str(p), kind)
            assert r["ok"] is True, kind
            assert Path(r["path"]).exists()

    def test_filter_missing_file_names_it(self) -> None:
        from universal_mind.image_suite import ImageSuite

        assert "file not found" in ImageSuite().filter("Z:/no.png", "blur")["error"]

    def test_split_channels_makes_three_files(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        p = _png(tmp_path)
        r = ImageSuite().split_channels(str(p))
        assert r["ok"] is True
        assert len(r["paths"]) == 3
        for q in r["paths"]:
            assert Path(q).exists()

    def test_split_missing_file_names_it(self) -> None:
        from universal_mind.image_suite import ImageSuite

        assert "file not found" in ImageSuite().split_channels("Z:/no.png")["error"]

    def test_blend_makes_a_real_mix(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        a = _png(tmp_path, "a.png", (50, 50))
        b = _png(tmp_path, "b.png", (30, 30))  # different size on purpose
        r = ImageSuite().blend(str(a), str(b), 0.5)
        assert r["ok"] is True
        with Image.open(r["path"]) as im:
            assert im.size == (50, 50)  # the second resizes to the first

    def test_blend_missing_second_names_it(self, tmp_path: Path) -> None:
        from universal_mind.image_suite import ImageSuite

        a = _png(tmp_path)
        r = ImageSuite().blend(str(a), "Z:/other.png")
        assert r["ok"] is False
        assert "file not found" in r["error"]


class TestDataSuite:
    """data_suite: شاخههای خطای عددی واقعی — DataSuite() بدون آرگو."""

    def _s(self) -> "DataSuite":
        from universal_mind.data_suite import DataSuite

        return DataSuite()

    def test_negative_sqrt_is_named(self) -> None:
        r = self._s().scalar_op(-4.0, 0.0, "sqrt")
        assert r["ok"] is False
        assert "جذر" in r["error"]

    def test_unknown_operation_is_named(self) -> None:
        r = self._s().scalar_op(1.0, 2.0, "dance")
        assert r["ok"] is False
        assert "ناشناخته" in r["error"]

    def test_empty_series_is_named(self) -> None:
        assert "empty series" in self._s().stats([])["error"]
        assert "empty series" in self._s().variance([])["error"]

    def test_shape_mismatch_is_named(self) -> None:
        r = self._s().matrix_multiply([[1, 2], [3, 4]], [[1, 2, 3]])
        assert r["ok"] is False
        assert "shape mismatch" in r["error"]

    def test_a_singular_matrix_is_named(self) -> None:
        singular = [[1.0, 2.0], [2.0, 4.0]]  # det = 0
        s = self._s().solve(singular, [1.0, 1.0])
        assert s["ok"] is False
        inv = self._s().inverse(singular)
        assert inv["ok"] is False
        assert inv["error"]  # the honest failure, named

    def test_normalize_of_a_constant_series_is_honest(self) -> None:
        r = self._s().normalize([5.0, 5.0, 5.0])
        assert r["ok"] is True
        assert r["normalized"] == [0.5, 0.5, 0.5]  # honest: no spread

    def test_correlate_of_unequal_series_is_named(self) -> None:
        r = self._s().correlate([1.0, 2.0], [1.0, 2.0, 3.0])
        assert r["ok"] is False
        assert "same non-zero length" in r["error"]
