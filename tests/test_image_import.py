import tempfile
from pathlib import Path
import pytest
from PIL import Image, ImageDraw

from sprite_studio.models import Frame, Sprite, Project
from sprite_studio.validation import validate_project
from sprite_studio.io import save_project, load_project
from sprite_studio.image_import import (
    compute_slice_ranges,
    load_image,
    slice_image,
    convert_frame_to_binary,
    import_raster_frames,
    ImageImportError,
)


def create_solid_image(width: int, height: int, color, mode="RGB") -> Image.Image:
    return Image.new(mode, (width, height), color)


class TestSliceRanges:
    def test_even_division(self):
        ranges = compute_slice_ranges(40, 4)
        assert ranges == [(0, 10), (10, 20), (20, 30), (30, 40)]

    def test_uneven_division_remainder(self):
        # 10 pixels divided into 3 parts -> sizes 4, 3, 3
        ranges = compute_slice_ranges(10, 3)
        assert ranges == [(0, 4), (4, 7), (7, 10)]
        sizes = [end - start for start, end in ranges]
        assert sum(sizes) == 10
        assert max(sizes) - min(sizes) <= 1

    def test_invalid_counts(self):
        with pytest.raises(ImageImportError, match="Frame count must be at least 1"):
            compute_slice_ranges(10, 0)
        with pytest.raises(ImageImportError, match="cannot exceed image dimension"):
            compute_slice_ranges(5, 10)


class TestImageImportAcceptance:
    @pytest.fixture
    def tmp_dir(self, tmp_path):
        return tmp_path

    def test_1_single_frame(self, tmp_dir):
        """Test 1 — pojedyncza klatka 8 x 22, tylko znaki '0' i '1'."""
        img_path = tmp_dir / "test1.png"
        img = Image.new("RGB", (32, 88), (255, 255, 255))
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=22,
            threshold=50.0,
        )

        assert len(frames) == 1
        frame = frames[0]
        assert len(frame.pixels) == 22
        for row in frame.pixels:
            assert len(row) == 8
            assert all(c in ("0", "1") for c in row)
        # All white with threshold 50 -> all '1'
        assert all(row == "11111111" for row in frame.pixels)

    def test_2_horizontal_animation(self, tmp_dir):
        """Test 2 — animacja pozioma N=4 od lewej do prawej."""
        img_path = tmp_dir / "test2.png"
        # 4 blocks: 1: black, 2: dark grey, 3: light grey, 4: white
        img = Image.new("RGB", (32, 16), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 7, 15], fill=(0, 0, 0))
        draw.rectangle([8, 0, 15, 15], fill=(60, 60, 60))
        draw.rectangle([16, 0, 23, 15], fill=(180, 180, 180))
        draw.rectangle([24, 0, 31, 15], fill=(255, 255, 255))
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=4,
            direction="horizontal",
            target_height=16,
            threshold=50.0,
        )

        assert len(frames) == 4
        # At threshold 50%:
        # Frame 0 (0% brightness) -> all 0
        assert all(row == "00000000" for row in frames[0].pixels)
        # Frame 1 (60/255 ~= 23.5% brightness) -> all 0
        assert all(row == "00000000" for row in frames[1].pixels)
        # Frame 2 (180/255 ~= 70.6% brightness) -> all 1
        assert all(row == "11111111" for row in frames[2].pixels)
        # Frame 3 (255/255 = 100% brightness) -> all 1
        assert all(row == "11111111" for row in frames[3].pixels)

    def test_3_vertical_animation(self, tmp_dir):
        """Test 3 — animacja pionowa N=3 od góry do dołu."""
        img_path = tmp_dir / "test3.png"
        img = Image.new("RGB", (16, 96), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 15, 31], fill=(255, 255, 255))  # top: white
        draw.rectangle([0, 32, 15, 63], fill=(128, 128, 128)) # mid: ~50%
        draw.rectangle([0, 64, 15, 95], fill=(0, 0, 0))       # bottom: black
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=3,
            direction="vertical",
            target_height=16,
            threshold=50.0,
        )

        assert len(frames) == 3
        # Top frame is white
        assert all(row == "11111111" for row in frames[0].pixels)
        # Bottom frame is black
        assert all(row == "00000000" for row in frames[2].pixels)

    def test_4_threshold_change(self, tmp_dir):
        """Test 4 — zmiana progu (25%, 50%, 75%): monotoniczność liczby pikseli 1."""
        img_path = tmp_dir / "test4.png"
        # Gradient from black to white
        img = Image.new("L", (100, 100))
        for x in range(100):
            for y in range(100):
                img.putpixel((x, y), int(x * 2.55))
        img.save(img_path)

        count_ones = {}
        for th in [25.0, 50.0, 75.0]:
            frames = import_raster_frames(
                path=img_path,
                frame_count=1,
                direction="horizontal",
                target_height=20,
                threshold=th,
            )
            total_ones = sum(row.count("1") for row in frames[0].pixels)
            count_ones[th] = total_ones

        # Increasing threshold MUST NOT increase the number of 1 pixels
        assert count_ones[25.0] >= count_ones[50.0] >= count_ones[75.0]

    @pytest.mark.parametrize("h", [1, 22, 255])
    def test_5_sprite_heights(self, tmp_dir, h):
        """Test 5 — wysokość sprite'a 1, 22, 255."""
        img_path = tmp_dir / f"test5_{h}.png"
        img = Image.new("RGB", (16, 16), (200, 200, 200))
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=h,
            threshold=50.0,
        )

        assert len(frames) == 1
        assert len(frames[0].pixels) == h
        for row in frames[0].pixels:
            assert len(row) == 8
            assert all(c in ("0", "1") for c in row)

    def test_6_aspect_ratio_and_letterboxing(self, tmp_dir):
        """Test 6 — zachowanie proporcji i czarne tło dla nietypowych proporcji."""
        # Very wide image: 80x10. In an 8x24 sprite, it must be letterboxed top & bottom.
        img_path = tmp_dir / "test6.png"
        img = Image.new("RGB", (80, 10), (255, 255, 255))
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=24,
            threshold=50.0,
        )

        assert len(frames) == 1
        pixels = frames[0].pixels
        # Because the image is very wide (80:10 = 8:1), scaled to width 8 gives height 1.
        # Top and bottom rows must be black ("00000000")
        assert pixels[0] == "00000000"
        assert pixels[-1] == "00000000"
        # The middle row(s) contain white pixels
        has_white = any("1" in row for row in pixels)
        assert has_white

    def test_7_cancellation_and_errors(self, tmp_dir):
        """Test 7 — obsługa błędów, nieobsługiwane formaty, nieistniejące pliki."""
        # Non-existent file
        with pytest.raises(ImageImportError, match="File not found"):
            load_image(tmp_dir / "non_existent.png")

        # Unsupported format
        unsupported = tmp_dir / "test.txt"
        unsupported.write_text("hello")
        with pytest.raises(ImageImportError, match="Unsupported file format"):
            load_image(unsupported)

        # Corrupted image file
        corrupt = tmp_dir / "corrupted.png"
        corrupt.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\x00corrupted")
        with pytest.raises(ImageImportError, match="Failed to read/decode"):
            load_image(corrupt)

        # Invalid frame count
        valid_img = tmp_dir / "valid.png"
        Image.new("RGB", (10, 10), (255, 255, 255)).save(valid_img)
        with pytest.raises(ImageImportError, match="Frame count must be at least 1"):
            import_raster_frames(valid_img, frame_count=0)

        with pytest.raises(ImageImportError, match="cannot exceed image dimension"):
            import_raster_frames(valid_img, frame_count=50)

    def test_8_save_and_reopen(self, tmp_dir):
        """Test 8 — dodanie klatek, walidacja, zapis i ponowny odczyt projektu."""
        img_path = tmp_dir / "sprite_sheet.bmp"
        img = Image.new("RGB", (24, 16), (255, 255, 255))
        img.save(img_path)

        imported_frames = import_raster_frames(
            path=img_path,
            frame_count=3,
            direction="horizontal",
            target_height=16,
            threshold=50.0,
        )

        assert len(imported_frames) == 3

        sprite = Sprite(
            id="IMPORTED_SPRITE",
            width=8,
            height=16,
            frames=imported_frames,
        )
        project = Project(version=1, sprites=[sprite])

        # Validate project
        errs = validate_project(project)
        assert len(errs) == 0, f"Validation errors: {errs}"

        # Save project
        proj_file = tmp_dir / "test_proj.sprite.json"
        saved = save_project(proj_file, project)
        assert saved is True

        # Reopen project
        loaded_proj = load_project(proj_file)
        assert len(loaded_proj.sprites) == 1
        loaded_spr = loaded_proj.sprites[0]
        assert loaded_spr.id == "IMPORTED_SPRITE"
        assert loaded_spr.width == 8
        assert loaded_spr.height == 16
        assert len(loaded_spr.frames) == 3
        for f_idx in range(3):
            assert loaded_spr.frames[f_idx].pixels == imported_frames[f_idx].pixels

    def test_9_alpha_compositing(self, tmp_dir):
        """Alpha channel compositing over black."""
        img_path = tmp_dir / "test9_alpha.png"
        # Transparent image with half transparent white
        img = Image.new("RGBA", (16, 32), (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)
        # Fully opaque white box at top
        draw.rectangle([0, 0, 15, 15], fill=(255, 255, 255, 255))
        # 0% alpha at bottom (remains transparent, i.e., black)
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=16,
            threshold=50.0,
        )
        assert len(frames) == 1
        # Top 8 rows should be white ('1'), bottom 8 rows black ('0')
        assert all(row == "11111111" for row in frames[0].pixels[:8])
        assert all(row == "00000000" for row in frames[0].pixels[8:])

    def test_10_jpeg_format(self, tmp_dir):
        """JPEG format support."""
        img_path = tmp_dir / "test10.jpg"
        img = Image.new("RGB", (16, 32), (255, 255, 255))
        img.save(img_path, "JPEG")

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=16,
            threshold=50.0,
        )
        assert len(frames) == 1
        assert len(frames[0].pixels) == 16
        assert all(row == "11111111" for row in frames[0].pixels)

    def test_11_inverse_option(self, tmp_dir):
        """Test import with inverse=True."""
        img_path = tmp_dir / "test11.png"
        img = Image.new("RGB", (16, 32), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, 15, 15], fill=(255, 255, 255))
        img.save(img_path)

        normal_frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=16,
            threshold=50.0,
            inverse=False,
        )
        inverted_frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=16,
            threshold=50.0,
            inverse=True,
        )

        for row_n, row_i in zip(normal_frames[0].pixels, inverted_frames[0].pixels):
            for c_n, c_i in zip(row_n, row_i):
                assert (c_n == "1" and c_i == "0") or (c_n == "0" and c_i == "1")

    def test_12_white_background_padding_not_inverted(self, tmp_dir):
        """Image with white background in fit mode must NOT have solid '11111111' padding lines."""
        img_path = tmp_dir / "walk_scenario.png"
        # 100x113 white image with black figure inside
        img = Image.new("RGB", (100, 113), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.rectangle([30, 30, 70, 80], fill=(0, 0, 0))
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=13,
            threshold=50.0,
            inverse=True,
            fit_mode="fit",
        )
        assert len(frames) == 1
        pixels = frames[0].pixels
        assert len(pixels) == 13
        # Top line and bottom line are padding -> must be '00000000', NOT '11111111'
        assert pixels[0] == "00000000"
        assert pixels[-1] == "00000000"

    def test_13_stretch_fit_mode(self, tmp_dir):
        """Stretch mode fills all 8xH rows without letterbox empty rows."""
        img_path = tmp_dir / "stretch_test.png"
        img = Image.new("RGB", (100, 113), (0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Full content
        draw.rectangle([0, 0, 99, 112], fill=(255, 255, 255))
        img.save(img_path)

        frames = import_raster_frames(
            path=img_path,
            frame_count=1,
            direction="horizontal",
            target_height=13,
            threshold=50.0,
            inverse=False,
            fit_mode="stretch",
        )
        assert len(frames) == 1
        # In stretch mode, all 13 rows are filled with white ('11111111')
        assert all(row == "11111111" for row in frames[0].pixels)


@pytest.fixture(scope="session")
def qapp():
    import sys
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


class TestImageImportDialogUI:
    def test_dialog_lifecycle_and_controls(self, qapp, tmp_path):
        from sprite_studio.widgets.import_dialog import ImageImportDialog
        from PySide6.QtWidgets import QDialog

        img_path = tmp_path / "ui_test.png"
        img = Image.new("RGB", (32, 48), (200, 200, 200))
        img.save(img_path)

        dlg = ImageImportDialog(
            image_path=img_path,
            target_height=24,
        )

        # Initial state
        assert dlg.target_height == 24
        assert dlg.spin_count.value() == 1
        assert dlg.slider_th.value() == 50
        assert dlg.combo_dir.currentData() == "horizontal"
        assert len(dlg.get_imported_frames()) == 1

        # Change frame count to 2
        dlg.spin_count.setValue(2)
        assert len(dlg.get_imported_frames()) == 2
        assert dlg.current_frame_idx == 0

        # Next / Prev buttons
        dlg.btn_next_frame.click()
        assert dlg.current_frame_idx == 1
        dlg.btn_prev_frame.click()
        assert dlg.current_frame_idx == 0

        # Change direction to vertical
        dlg.combo_dir.setCurrentIndex(1)
        assert dlg.combo_dir.currentData() == "vertical"

        # Change threshold
        dlg.slider_th.setValue(75)
        assert dlg.spin_th.value() == 75
        dlg.spin_th.setValue(30)
        assert dlg.slider_th.value() == 30

        # Check frames generated
        frames = dlg.get_imported_frames()
        assert len(frames) == 2
        for f in frames:
            assert len(f.pixels) == 24
            for row in f.pixels:
                assert len(row) == 8

        # Test fit mode change
        dlg.combo_fit.setCurrentIndex(1)  # stretch
        assert dlg.combo_fit.currentData() == "stretch"

        # Toggle inverse
        assert not dlg.chk_inverse.isChecked()
        orig_row = dlg.get_imported_frames()[0].pixels[0]
        dlg.chk_inverse.setChecked(True)
        inv_row = dlg.get_imported_frames()[0].pixels[0]
        for cn, ci in zip(orig_row, inv_row):
            assert (cn == "1" and ci == "0") or (cn == "0" and ci == "1")

        dlg.chk_inverse.setChecked(False)
        assert dlg.get_imported_frames()[0].pixels[0] == orig_row

        # Test Target Height and Auto Height
        dlg.spin_height.setValue(16)
        assert dlg.target_height == 16
        assert len(dlg.get_imported_frames()[0].pixels) == 16
        dlg.btn_auto_height.click()
        assert dlg.target_height == dlg.spin_height.value()

    def test_mainwindow_import_command(self, qapp, tmp_path, monkeypatch):
        from sprite_studio.main import MainWindow
        from PySide6.QtWidgets import QDialog

        win = MainWindow()
        # Add a sprite
        win._on_add_sprite()
        assert win.current_sprite is not None
        assert len(win.current_sprite.frames) == 1

        img_path = tmp_path / "mw_test.png"
        img = Image.new("RGB", (24, 24), (255, 255, 255))
        img.save(img_path)

        # Monkeypatch QFileDialog and ImageImportDialog.exec
        monkeypatch.setattr("sprite_studio.main.QFileDialog.getOpenFileName", lambda *args, **kwargs: (str(img_path), ""))
        monkeypatch.setattr("sprite_studio.main.ImageImportDialog.exec", lambda self: QDialog.Accepted)
        monkeypatch.setattr("sprite_studio.main.QMessageBox.information", lambda *args, **kwargs: None)

        win.action_import_image()

        # Should have imported 1 frame added to the existing frame
        assert len(win.current_sprite.frames) == 2

        # Test Undo
        win._undo()
        assert len(win.current_sprite.frames) == 1

        # Test Redo
        win._redo()
        assert len(win.current_sprite.frames) == 2

