"""Builds the browser version: the game ROM plus the official Vircon32 web emulator.

    python tools/web/build.py       build/web/ (index.html, vircon32.js/.wasm/.data, sulphur.v32)

The emulator is vircon32/WebEmulator (BSD-3) compiled with Emscripten. Its own entry point and
menus (Main.cpp, GUI.cpp, Settings.cpp) need Dear ImGui, which upstream already removed, and run a
blocking loop that would freeze a browser tab, so tools/web/main.cpp replaces just those three files;
video, audio and keyboard input are upstream's. The console itself is the ConsoleLogic pinned in
tools/toolchain.py (the one the headless tests run), not WebEmulator's older copy, so the browser
plays the game exactly as the tests do.

emsdk and the WebEmulator source are pinned below and cached in .toolchain/.
"""
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
# tools/, not tools/web/: `import build` must find the ROM build, not this file
sys.path[0] = str(HERE.parent)
import build as rom_build  # noqa: E402
from toolchain import CACHE, ROOT, tools  # noqa: E402

EMSDK_VERSION = "6.0.13"
EMSDK_URL = "https://github.com/emscripten-core/emsdk.git"

WEBEMULATOR_COMMIT = "9714fe4e114e3f12e7ce6ad6df62b145de3a5c7f"
WEBEMULATOR_URL = "https://codeload.github.com/vircon32/WebEmulator/tar.gz/" + WEBEMULATOR_COMMIT
WEBEMULATOR_PARTS = ("WebEmulator/Emulator/", "WebEmulator/DesktopInfrastructure/",
                     "WebEmulator/Data/Readme.txt", "License.md")
# upstream sources used as they are; Main.cpp, GUI.cpp, Settings.cpp and Languages.cpp are replaced
UPSTREAM_SOURCES = ("Emulator/AudioOutput.cpp", "Emulator/EmulatorControl.cpp",
                    "Emulator/GamepadsInput.cpp", "Emulator/Globals.cpp", "Emulator/StopWatch.cpp",
                    "Emulator/VideoOutput.cpp", "DesktopInfrastructure/FilePaths.cpp",
                    "DesktopInfrastructure/Logger.cpp", "DesktopInfrastructure/StringFunctions.cpp")

OUT = ROOT / "build" / "web"
OBJ = ROOT / "build" / "obj" / "web"


def emsdk():
    """emcc of the pinned emsdk, installed on first use."""
    target = CACHE / f"emsdk-{EMSDK_VERSION}"
    emscripten = target / "upstream" / "emscripten"
    if not (emscripten / "emcc.py").exists():
        if not (target / "emsdk.py").exists():
            shutil.rmtree(target, ignore_errors=True)
            subprocess.run(["git", "clone", "--depth", "1", "--branch", EMSDK_VERSION, EMSDK_URL,
                            str(target)], check=True)
        for step in ("install", "activate"):
            subprocess.run([sys.executable, str(target / "emsdk.py"), step, EMSDK_VERSION],
                           check=True, cwd=target)
    os.environ["EM_CONFIG"] = str(target / ".emscripten")
    # Windows has emcc.exe (or emcc.bat in older releases), Linux the emcc script
    return next(emscripten / n for n in ("emcc.exe", "emcc.bat", "emcc") if (emscripten / n).exists())


def webemulator():
    target = CACHE / f"webemulator-{WEBEMULATOR_COMMIT[:12]}"
    if not target.exists():
        with urllib.request.urlopen(WEBEMULATOR_URL, timeout=300) as r:
            data = r.read()
        tmp = CACHE / "webemulator-tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for m in tar.getmembers():
                rel = m.name.split("/", 1)[1] if "/" in m.name else ""
                if m.isfile() and rel.startswith(WEBEMULATOR_PARTS):
                    out = tmp / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(tar.extractfile(m).read())
        tmp.rename(target)
    return target


def compile_emulator(emcc, web, console, bios):
    """vircon32.js/.wasm/.data in build/web; the BIOS is preloaded into the .data file."""
    logic = sorted((console / "DesktopEmulator/ConsoleLogic").glob("*.cpp"))
    sources = [*(web / "WebEmulator" / s for s in UPSTREAM_SOURCES), HERE / "main.cpp", *logic]
    flags = ["-O2", "-std=c++14", "-fwasm-exceptions", "-sUSE_SDL=2",
             # console headers first: WebEmulator/ConsoleLogic is an older copy we do not use
             "-I", console / "DesktopEmulator", "-I", web / "WebEmulator", "-I", web / "WebEmulator/Emulator"]
    OBJ.mkdir(parents=True, exist_ok=True)
    objects = []
    for src in sources:
        obj = OBJ / (src.stem + ".o")
        stamp = OBJ / (src.stem + ".stamp")
        key = hashlib.sha256(src.read_bytes() + " ".join(map(str, flags)).encode()).hexdigest()
        if not obj.exists() or not stamp.exists() or stamp.read_text() != key:
            run([emcc, *flags, "-Wno-unused-parameter", "-c", src, "-o", obj])
            stamp.write_text(key)
        objects.append(obj)
    run([emcc, *flags, *objects, "-o", OUT / "vircon32.js",
         "-sENVIRONMENT=web", "-sALLOW_MEMORY_GROWTH=1", "-sINITIAL_MEMORY=64MB",
         "-lidbfs.js", "-sEXPORTED_RUNTIME_METHODS=FS,addRunDependency,removeRunDependency",
         "--preload-file", f"{bios}@/Bios/StandardBios.v32"])


def run(cmd):
    result = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit((result.stdout + result.stderr).strip() or f"failed: {cmd}")


def licences(web, emcc):
    """Notices of everything shipped in build/web besides our own code."""
    readme = (web / "WebEmulator/Data/Readme.txt").read_text(encoding="utf-8", errors="replace")
    vircon = readme[readme.index("Copyright"):].split("\n---")[0]
    emscripten = (emcc.parent / "LICENSE").read_text(encoding="utf-8")
    sdl = next((emcc.parent / "cache").rglob("SDL2*/LICENSE.txt"), None)
    parts = [
        "Sulphur in the browser runs on the Vircon32 web emulator and its console logic",
        "(https://github.com/vircon32), 3-Clause BSD License; Vircon32 assets CC BY 4.0.",
        "", vircon.strip(), "", "=" * 72,
        "SDL2 (Emscripten port, https://libsdl.org), zlib License:", "",
        sdl.read_text(encoding="utf-8").strip() if sdl else
        "Simple DirectMedia Layer, Copyright (C) 1997-2025 Sam Lantinga. zlib License.",
        "", "=" * 72, "Emscripten runtime (https://emscripten.org):", "", emscripten.strip(), "",
    ]
    (OUT / "LICENSES.txt").write_text("\n".join(parts), encoding="utf-8")


def build():
    rom = rom_build.build()
    t = tools()
    console = t["bios"].parents[3]
    emcc = emsdk()
    web = webemulator()
    OUT.mkdir(parents=True, exist_ok=True)
    compile_emulator(emcc, web, console, t["bios"])
    shutil.copyfile(rom, OUT / "sulphur.v32")
    shutil.copyfile(ROOT / "web/index.html", OUT / "index.html")
    licences(web, emcc)
    return OUT


if __name__ == "__main__":
    out = build()
    for f in sorted(out.iterdir()):
        print(f"{f.stat().st_size:>10}  {f.relative_to(ROOT).as_posix()}")
