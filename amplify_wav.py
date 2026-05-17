#!/usr/bin/env python3
"""Amplify a WAV file by a given gain, clipping to the format's int range.

Usage: amplify_wav.py <input.wav> <output.wav> [--gain N]

Reads input WAV, multiplies all samples by gain, clips to the sample width's
signed-int range, writes output WAV with the same params. Prints peak-after
and number of clipped samples so you can pick a safe gain.
"""
import argparse
import struct
import sys
import wave


FORMATS = {1: "b", 2: "h", 4: "i"}


def amplify(src: str, dst: str, gain: float) -> None:
    with wave.open(src, "rb") as w:
        params = w.getparams()
        raw = w.readframes(params.nframes)

    sw = params.sampwidth
    if sw not in FORMATS:
        raise SystemExit(f"unsupported sample width: {sw} bytes")
    fmt = FORMATS[sw]

    samples = struct.unpack(f"<{len(raw) // sw}{fmt}", raw)
    maxv = (1 << (sw * 8 - 1)) - 1
    minv = -(1 << (sw * 8 - 1))

    amplified = [max(minv, min(maxv, int(s * gain))) for s in samples]
    peak = max(abs(s) for s in amplified)
    clipped = sum(1 for s in amplified if s == maxv or s == minv)

    out = struct.pack(f"<{len(amplified)}{fmt}", *amplified)
    with wave.open(dst, "wb") as w:
        w.setparams(params)
        w.writeframes(out)

    print(f"wrote {dst}")
    print(
        f"peak_after={peak}/{maxv} ({peak / maxv * 100:.1f}%) "
        f"clipped_samples={clipped}/{len(amplified)}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("src")
    parser.add_argument("dst")
    parser.add_argument("--gain", type=float, default=10.0)
    args = parser.parse_args()
    amplify(args.src, args.dst, args.gain)
    return 0


if __name__ == "__main__":
    sys.exit(main())
