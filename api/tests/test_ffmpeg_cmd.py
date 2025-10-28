from pathlib import Path

from app.utils.media import build_mux_command


def test_build_mux_command_maps():
    cmd = build_mux_command(Path("v.mp4"), Path("a.mp3"), Path("o.mp4"))
    joined = " ".join(cmd)
    assert "-map 0:v:0" in joined
    assert "-map 1:a:0" in joined
