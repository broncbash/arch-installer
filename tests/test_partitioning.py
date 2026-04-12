import sys
import os
import types
from dataclasses import dataclass

# Add the project root to the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Mock gi and its modules to avoid GTK dependencies
class MockGI:
    def require_version(self, name, version):
        pass
sys.modules["gi"] = MockGI()

def create_mock_module(name, **kwargs):
    m = types.ModuleType(name)
    for k, v in kwargs.items():
        setattr(m, k, v)
    return m

# Minimal mocks to allow importing BaseScreen and PartitionScreen
mock_gtk = create_mock_module("Gtk",
    Box=type("Box", (), {}),
    DrawingArea=type("DrawingArea", (), {}),
    Label=type("Label", (), {}),
    Frame=type("Frame", (), {}),
    Separator=type("Separator", (), {}),
    ScrolledWindow=type("ScrolledWindow", (), {}),
    Expander=type("Expander", (), {}),
    ComboBoxText=type("ComboBoxText", (), {}),
    Button=type("Button", (), {}),
    Orientation=type("Orientation", (), {"VERTICAL": 1, "HORIZONTAL": 0}),
    Align=type("Align", (), {"START": 0, "CENTER": 1, "END": 2}),
    Widget=type("Widget", (), {}),
    Window=type("Window", (), {}),
    TreeView=type("TreeView", (), {}),
    ListStore=type("ListStore", (), {}),
    RadioButton=type("RadioButton", (), {}),
    CheckButton=type("CheckButton", (), {}),
    ProgressBar=type("ProgressBar", (), {}),
    TextView=type("TextView", (), {}),
    Stack=type("Stack", (), {}),
)
mock_gdk = create_mock_module("Gdk")
mock_pango = create_mock_module("Pango", WrapMode=type("WrapMode", (), {"WORD_CHAR": 0}))
mock_glib = create_mock_module("GLib", timeout_add=lambda *args: None, idle_add=lambda *args: None)
mock_gdkpixbuf = create_mock_module("GdkPixbuf")

gi_repository = types.ModuleType("gi.repository")
gi_repository.Gtk = mock_gtk
gi_repository.Gdk = mock_gdk
gi_repository.Pango = mock_pango
gi_repository.GLib = mock_glib
gi_repository.GdkPixbuf = mock_gdkpixbuf
sys.modules["gi.repository"] = gi_repository

# Now we can import from the source
from installer.ui.partition import _build_auto_layout

def test_build_auto_layout_includes_boot():
    print("Testing _build_auto_layout from source...")

    # Test UEFI
    partitions_uefi = _build_auto_layout(
        disk_mb=20480,
        boot_mode="uefi",
        swap_type="none",
        swap_mb=0
    )

    mountpoints_uefi = [p.mountpoint for p in partitions_uefi]
    print(f"UEFI Mountpoints: {mountpoints_uefi}")
    assert "/boot" in mountpoints_uefi
    assert "/" in mountpoints_uefi

    # Verify /boot is vfat (ESP)
    boot_part = next(p for p in partitions_uefi if p.mountpoint == "/boot")
    assert boot_part.filesystem == "vfat"
    assert boot_part.size_mb == 512

    # Test BIOS
    partitions_bios = _build_auto_layout(
        disk_mb=20480,
        boot_mode="bios",
        swap_type="none",
        swap_mb=0
    )

    mountpoints_bios = [p.mountpoint for p in partitions_bios]
    print(f"BIOS Mountpoints: {mountpoints_bios}")
    assert "/boot" in mountpoints_bios
    assert "/" in mountpoints_bios
    assert "/boot/efi" not in mountpoints_bios

    print("Test passed!")

if __name__ == "__main__":
    try:
        test_build_auto_layout_includes_boot()
    except AssertionError as e:
        print(f"Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
