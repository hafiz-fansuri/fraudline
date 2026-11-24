"""Export a verified model and aggregate evidence; never export training rows or references."""

import json
import shutil
from pathlib import Path

from fraudline.model import Model
from fraudline.pipeline import ART, registry

state = registry()
folder = ART / "models" / state["champion"]
model = Model(folder)
out = Path("demo-bundle")
model_root = (out / "models").resolve()
if model_root.exists():
    for stale in model_root.iterdir():
        if stale.is_dir() and stale.name != state["champion"]:
            if stale.resolve().parent != model_root:
                raise ValueError("Refusing to remove a model outside the demo export directory")
            shutil.rmtree(stale)
target = out / "models" / state["champion"]
target.mkdir(parents=True, exist_ok=True)
for name in ["model.txt", "metadata.json", "evaluation.json"] + (
    ["residual.ubj"] if model.residual is not None else []
):
    shutil.copy2(folder / name, target / name)
(out / "reports").mkdir(exist_ok=True)
for name in ["demo-drift.json", "synthetic-tests.json"]:
    source = ART / "reports" / name
    if source.exists():
        shutil.copy2(source, out / "reports" / name)
    elif (out / "reports" / name).exists():
        (out / "reports" / name).unlink()
(out / "registry.json").write_text(
    json.dumps(
        {
            "champion": state["champion"],
            "previous": None,
            "history": [h for h in state["history"] if h["version"] == state["champion"]],
        },
        indent=2,
    )
)
print(f"Exported verified {model.meta['data_source']} bundle {state['champion']}; no dataset rows")
