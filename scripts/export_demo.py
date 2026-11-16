"""Export only a synthetic champion and its evidence for an ephemeral hosted demo."""

import json
import shutil
from pathlib import Path

from fraudline.model import Model
from fraudline.pipeline import ART, registry

state = registry()
folder = ART / "models" / state["champion"]
model = Model(folder)
if model.meta["data_source"] != "synthetic":
    raise ValueError("Only synthetic model bundles may be exported to the public demo")
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
for name in ["model.txt", "metadata.json", "evaluation.json"]:
    shutil.copy2(folder / name, target / name)
(out / "reports").mkdir(exist_ok=True)
shutil.copy2(ART / "reports/demo-drift.json", out / "reports/demo-drift.json")
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
print(f"Exported verified synthetic bundle {state['champion']}")
