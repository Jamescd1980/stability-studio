from pathlib import Path

em = Path(r"D:\Extra Models") / "Character LoRA's"
print("Extra Models dir", em, "exists", em.exists())
if em.exists():
    for p in sorted(em.glob("*.safetensors")):
        h = p.open("rb").read(8)
        print(" EM", p.name, p.stat().st_size, "nz", sum(h))

sm = Path(r"D:\StabilityMatrix-win-x64\Data\Models\Lora")
print("SM Lora top-level character dirs:")
for n in ("Fern", "Frieren", "Ubel", "Flamme"):
    d = sm / n
    flat = sm / f"{n}.safetensors"
    print(" ", n, "dir", d.exists(), "flat", flat.exists(), flat.stat().st_size if flat.exists() else "-")
    if d.exists():
        for p in d.glob("*.safetensors"):
            h = p.open("rb").read(8)
            print("   ", p.name, p.stat().st_size, "nz", sum(h))
