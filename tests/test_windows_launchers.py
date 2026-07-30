from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_batch_wrappers_are_ascii_for_legacy_cmd():
    for filename in ("安装环境.bat", "启动程序.bat"):
        content = (PROJECT_ROOT / filename).read_bytes()
        assert all(byte < 128 for byte in content)
        assert b"pause" in content


def test_powershell_scripts_have_utf8_bom():
    for filename in ("install.ps1", "start.ps1"):
        content = (PROJECT_ROOT / "scripts" / filename).read_bytes()
        assert content.startswith(b"\xef\xbb\xbf")
