#!/usr/bin/env python3
"""Download pinned Chinese font subsets into an ignored local cache."""

import argparse
import base64
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.error import URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONT_DIR = PROJECT_ROOT / "assets/vendor/noto-sans-sc"


def _verify_font(data, face):
    if len(data) != face["bytes"] or hashlib.sha256(data).hexdigest() != face["sha256"]:
        raise ValueError(f"Font checksum mismatch: {face['source']}")
    if not data.startswith(b"wOF2"):
        raise ValueError(f"Not a WOFF2 font: {face['source']}")
    return data


def _read_font(face, base_url, source_dir):
    name = face["source"]
    if Path(name).name != name or not name.endswith(".woff2"):
        raise ValueError(f"Invalid font filename: {name}")
    if source_dir is not None:
        folder = Path(source_dir).resolve()
        path = folder / name if (folder / name).is_file() else folder / "files" / name
        with path.open("rb") as handle:
            data = handle.read(face["bytes"] + 1)
    else:
        request = Request(base_url + name, headers={"User-Agent": "rednote-skill/font-cache"})
        with urlopen(request, timeout=30) as response:
            data = response.read(face["bytes"] + 1)
    return _verify_font(data, face)


def _cache_matches(destination, manifest):
    if not destination.is_file():
        return False
    try:
        bundle = json.loads(destination.read_text(encoding="utf-8"))
        for key in ("family", "weight", "fontsource_version"):
            if bundle[key] != manifest[key]:
                return False
        if len(bundle["faces"]) != len(manifest["faces"]):
            return False
        for cached, expected in zip(bundle["faces"], manifest["faces"]):
            if any(cached[key] != expected[key] for key in ("source", "unicode_range")):
                return False
            _verify_font(base64.b64decode(cached["data"], validate=True), expected)
        return True
    except (ValueError, KeyError, TypeError):
        return False


def download_content_fonts(*, source_dir=None, manifest_path=None, output=None):
    manifest = json.loads(Path(manifest_path or FONT_DIR / "font-manifest.json").read_text(encoding="utf-8"))
    destination = Path(output or FONT_DIR / "font-bundle.json").resolve()
    if _cache_matches(destination, manifest):
        return {"output": str(destination), "faces": len(manifest["faces"]), "cached": True}

    def load_face(face):
        data = _read_font(face, manifest["base_url"], source_dir)
        return {"unicode_range": face["unicode_range"], "data": base64.b64encode(data).decode("ascii"), "source": face["source"]}

    # Keep source order and finish verification before touching an existing cache.
    with ThreadPoolExecutor(max_workers=8) as executor:
        faces = list(executor.map(load_face, manifest["faces"]))
    bundle = {key: manifest[key] for key in ("family", "weight", "fontsource_version")}
    bundle["faces"] = faces
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, suffix=".tmp", delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(bundle, handle, ensure_ascii=False, separators=(",", ":"))
            handle.write("\n")
        os.replace(temporary, destination)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
    return {"output": str(destination), "faces": len(faces), "cached": False, "bytes": destination.stat().st_size}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", help="Reuse a downloaded @fontsource/noto-sans-sc package or its files directory instead of fetching")
    args = parser.parse_args(argv)
    try:
        print(json.dumps(download_content_fonts(source_dir=args.source_dir), ensure_ascii=False))
    except (OSError, ValueError, URLError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
