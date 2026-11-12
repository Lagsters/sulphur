"""Vircon32 toolchain: dev tools, BIOS and the headless runner, pinned and cached in .toolchain/.

    python tools/toolchain.py        prints the tool paths (fetching and building what is missing)

Other scripts import `tools()`.
"""
import hashlib
import io
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / ".toolchain"

DEVTOOLS_VERSION = "26.11.05"
DEVTOOLS = {
    "windows": ("Vircon32-DevTools-26.11.05-windows-x86_64.zip",
                "7590501cc1f945fcb4357241f00ddb2acf4fbde248f6beb7ae652da59ae602a8"),
    "linux": ("Vircon32-DevTools-26.11.05-linux-x86_64.deb",
              "0cd35f177b10b0af4c65e6e820e3b1ff93559a2a5665dbdcbf1da34ee60cddd3"),
}
DEVTOOLS_URL = "https://github.com/vircon32/ComputerSoftware/releases/download/devtools-v{v}/{f}"

# the console's own source: the runner is built on it, and the BIOS comes from it
CONSOLE_COMMIT = "70ed768d88de15c3682b9e518b1430f806e97134"
CONSOLE_URL = "https://codeload.github.com/vircon32/ComputerSoftware/tar.gz/" + CONSOLE_COMMIT
BIOS_SHA256 = "848aa2423f6755f44a6503302b0afc8a469e37378ea88de4e039846fcab779a1"
CONSOLE_PARTS = ("DesktopEmulator/ConsoleLogic/", "VirconDefinitions/",
                 "DesktopEmulator/Data/Bios/StandardBios.v32")

EXE = ".exe" if os.name == "nt" else ""
TOOL_NAMES = ("compile", "assemble", "packrom", "png2vircon", "wav2vircon")


def _download(url, sha256=None):
    with urllib.request.urlopen(url, timeout=300) as r:
        data = r.read()
    if sha256 and hashlib.sha256(data).hexdigest() != sha256:
        sys.exit(f"toolchain: checksum mismatch for {url}")
    return data


def _devtools_dir():
    system = "windows" if os.name == "nt" else "linux"
    if platform.machine().lower() not in ("amd64", "x86_64"):
        sys.exit("toolchain: only x86_64 Windows and Linux are pinned")
    target = CACHE / f"devtools-{DEVTOOLS_VERSION}"
    if not target.exists():
        name, sha = DEVTOOLS[system]
        data = _download(DEVTOOLS_URL.format(v=DEVTOOLS_VERSION, f=name), sha)
        tmp = CACHE / "devtools-tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        tmp.mkdir(parents=True)
        if system == "windows":
            zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
        else:
            deb = tmp / name
            deb.write_bytes(data)
            subprocess.run(["dpkg-deb", "-x", str(deb), str(tmp / "x")], check=True)
        tmp.rename(target)
    found = {}
    for path in target.rglob("*"):
        if path.is_file() and path.stem in TOOL_NAMES and path.suffix in ("", ".exe"):
            found[path.stem] = path
            if EXE == "":
                path.chmod(0o755)
    missing = [t for t in TOOL_NAMES if t not in found]
    if missing:
        sys.exit(f"toolchain: dev tools without {missing}")
    return found


def _console_dir():
    target = CACHE / f"console-{CONSOLE_COMMIT[:12]}"
    if not target.exists():
        data = _download(CONSOLE_URL)
        tmp = CACHE / "console-tmp"
        shutil.rmtree(tmp, ignore_errors=True)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
            for m in tar.getmembers():
                rel = m.name.split("/", 1)[1] if "/" in m.name else ""
                if m.isfile() and rel.startswith(CONSOLE_PARTS):
                    out = tmp / rel
                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_bytes(tar.extractfile(m).read())
        bios = tmp / "DesktopEmulator/Data/Bios/StandardBios.v32"
        if hashlib.sha256(bios.read_bytes()).hexdigest() != BIOS_SHA256:
            sys.exit("toolchain: BIOS checksum mismatch")
        tmp.rename(target)
    return target


def _gpp():
    found = shutil.which("g++")
    if found:
        return found
    # WinLibs from winget does not put g++ on PATH for every shell
    packages = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Packages"
    for path in packages.glob("BrechtSanders.WinLibs*/mingw64/bin/g++.exe"):
        return str(path)
    sys.exit("toolchain: no g++ (Windows: winget install BrechtSanders.WinLibs.POSIX.UCRT)")


def _runner(console):
    source = ROOT / "tools/runner/runner.cpp"
    stamp = hashlib.sha256(source.read_bytes() + CONSOLE_COMMIT.encode()).hexdigest()[:12]
    runner = CACHE / f"runner-{stamp}{EXE}"
    if not runner.exists():
        gpp = _gpp()
        logic = sorted(str(p) for p in (console / "DesktopEmulator/ConsoleLogic").glob("*.cpp"))
        cmd = [gpp, "-O2", "-std=c++14", "-I", str(console / "DesktopEmulator"), str(source),
               *logic, "-o", str(runner)]
        if os.name == "nt":
            cmd.append("-static")  # the runner then starts without WinLibs' DLLs on PATH
        subprocess.run(cmd, check=True)
    return runner


def tools():
    CACHE.mkdir(exist_ok=True)
    found = _devtools_dir()
    console = _console_dir()
    found["runner"] = _runner(console)
    found["bios"] = console / "DesktopEmulator/Data/Bios/StandardBios.v32"
    return found


if __name__ == "__main__":
    for name, path in tools().items():
        print(f"{name}: {path}")
