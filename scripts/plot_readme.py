"""Regenerate README charts from the committed model evidence; needs the ops extras."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
bundle = ROOT / "demo-bundle"
version = json.loads((bundle / "registry.json").read_text())["champion"]
folder = bundle / "models" / version
metadata = json.loads((folder / "metadata.json").read_text())
evaluation = json.loads((folder / "evaluation.json").read_text())
hybrid = metadata.get("model_kind") == "lgb-xgb-residual"
if hybrid:
    previous = json.loads((bundle / "registry.json").read_text())["previous"]
    evaluation["baseline"] = json.loads((bundle / "models" / previous / "evaluation.json").read_text())["final_test"]
comparison_labels = ["Earlier LightGBM", "Residual hybrid"] if hybrid else ["Logistic baseline", "LightGBM"]
out = ROOT / "docs" / "charts"
out.mkdir(exist_ok=True)

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "svg.fonttype": "none"})
colors = ["#6970ab", "#087869"]
fig, axes = plt.subplots(1, 2, figsize=(12, 4.9))
for ax, names, labels in zip(
    axes,
    [["pr_auc", "roc_auc"], ["recall", "false_positive_rate"]],
    [
        ["Average precision\nHigher is better", "ROC-AUC\nHigher is better"],
        ["Recall\nHigher is better", "False-positive rate\nLower is better"],
    ],
    strict=True,
):
    positions = np.arange(len(names))
    for offset, key, label, color in zip(
        [-0.18, 0.18], ["baseline", "final_test"], comparison_labels, colors, strict=True
    ):
        values = [evaluation[key][name] for name in names]
        assert all(0 <= value <= 1 for value in values)
        bars = ax.bar(positions + offset, values, width=0.31, label=label, color=color, zorder=3)
        ax.bar_label(bars, labels=[f"{value:.3f}" for value in values], padding=5, fontsize=10)
    ax.set_xticks(positions, labels)
    ax.set_ylim(0, 1.13)
    ax.set_yticks([0, 0.25, 0.5, 0.75, 1])
    ax.grid(axis="y", color="#e4e9ed", zorder=0)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#ccd5d9")
    ax.tick_params(axis="both", length=0, pad=8)
    ax.set_axisbelow(True)
axes[0].set_title("Ranking quality", loc="left", pad=17, fontweight="bold")
axes[1].set_title("Review-threshold trade-off", loc="left", pad=17, fontweight="bold")
fig.suptitle(
    f"IEEE-CIS: {evaluation['final_test']['rows']:,} later research transactions (previously inspected)",
    x=0.07,
    ha="left",
    fontsize=16,
    fontweight="bold",
)
handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.065), ncol=2, frameon=False)
fig.text(
    0.5,
    0.018,
    "Each model chooses its own thresholds on calibration data. Point estimates; no confidence intervals computed.",
    ha="center",
    color="#53616c",
    fontsize=9,
)
fig.tight_layout(rect=(0.025, 0.16, 0.99, 0.9))
fig.savefig(out / ("hybrid-comparison.svg" if hybrid else "model-comparison.svg"), facecolor="white")
plt.close(fig)

fig, ax = plt.subplots(figsize=(12, 2.8))
split_colors = ["#17665a", "#4c678c", "#956c2a", "#763e70"]
left = 0
assert sum(part["rows"] for part in metadata["splits"].values()) == metadata["rows"]
for (name, part), color in zip(metadata["splits"].items(), split_colors, strict=True):
    ax.barh(0, part["rows"], left=left, height=0.65, color=color, edgecolor="white", linewidth=2)
    ax.text(
        left + part["rows"] / 2,
        0,
        f"{name.replace('_', ' ').title()}\n{part['rows']:,} rows",
        ha="center",
        va="center",
        color="white",
        fontsize=10,
    )
    left += part["rows"]
ax.set_xlim(0, metadata["rows"])
ax.set_ylim(-0.6, 0.6)
ax.axis("off")
fig.text(0.035, 0.85, "Chronological split: earlier events → later events", fontsize=16, fontweight="bold")
fig.text(
    0.035,
    0.72,
    f"All {metadata['rows']:,} labeled rows are used across separate intervals; only the first interval fits the trees.",
    fontsize=10,
    color="#53616c",
)
fig.text(
    0.035,
    0.10,
    "Split on distinct timestamps. History uses strictly earlier events only; final test labels never fit the model.",
    fontsize=10,
    color="#53616c",
)
fig.subplots_adjust(left=0.035, right=0.98, bottom=0.20, top=0.68)
fig.savefig(out / "chronological-split.svg", facecolor="white")
plt.close(fig)
print(f"Generated two charts for {version} in {out}")
