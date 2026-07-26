"""
The stage vocabulary guard — issue #68.

One value per journey stage, named after the nav stage it belongs to. Every
producer and consumer of a `stage` value in the repo has to draw from
app.stages.Stage; these tests fail when one of them drifts, which is how a
workflow item written by the Academic Risk page came to be invisible to it.
"""

import json
import re
from pathlib import Path

import pytest
import yaml

from app.stages import LEGACY_STAGES, LEGACY_STATUSES, STAGES, WORKFLOW_STATUSES

REPO_ROOT = Path(__file__).parent.parent.parent
BACKEND_APP = Path(__file__).parent.parent / "app"
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
FRONTEND_SRC = REPO_ROOT / "frontend" / "src"
WRITE_TOOLS_PATH = REPO_ROOT / "orchestrate" / "tools" / "write_tools.yaml"
FRONTEND_STAGES_PATH = FRONTEND_SRC / "lib" / "stages.ts"
FRONTEND_STATUS_PATH = FRONTEND_SRC / "lib" / "status.ts"

# Every way a stage value is spelled in this repo: a SQL filter, a column
# alias in a SELECT, a dict/object literal, a Python keyword argument.
STAGE_LITERAL_PATTERNS = [
    re.compile(r"""\bstage\s*(?:=|==|!=)\s*['"]([a-z_]+)['"]"""),
    re.compile(r"""['"]([a-z_]+)['"]\s+AS\s+stage\b""", re.IGNORECASE),
    re.compile(r"""['"]stage['"]\s*:\s*['"]([a-z_]+)['"]"""),
    re.compile(r"""\bstage:\s*['"]([a-z_]+)['"]"""),
]


def write_tools_schema(name: str) -> dict:
    spec = yaml.safe_load(WRITE_TOOLS_PATH.read_text())
    return spec["components"]["schemas"][name]


def stage_literals(path: Path) -> set[str]:
    text = path.read_text()
    return {
        match
        for pattern in STAGE_LITERAL_PATTERNS
        for match in pattern.findall(text)
    }


def source_files() -> list[Path]:
    """Everything that reads or writes a stage: backend app code, frontend code."""
    return [
        *sorted(BACKEND_APP.rglob("*.py")),
        *sorted(FRONTEND_SRC.rglob("*.ts")),
        *sorted(FRONTEND_SRC.rglob("*.tsx")),
    ]


def ts_string_array(source: str, name: str) -> list[str]:
    """The string entries of an exported `const NAME = [...]` in a .ts file."""
    body = re.search(rf"export const {name} = \[(.*?)\]", source, re.DOTALL)
    assert body, f"{name} not found"
    return re.findall(r'"([a-z_]+)"', body.group(1))


def test_fixture_workflow_items_use_canonical_stages():
    items = json.loads((FIXTURES_DIR / "workflow_items.json").read_text())
    off_vocabulary = sorted(
        {item["stage"] for item in items if item["stage"] not in STAGES}
    )
    assert not off_vocabulary, (
        f"workflow_items.json uses stages outside the vocabulary: {off_vocabulary}"
    )


def test_fixture_workflow_items_use_canonical_statuses():
    items = json.loads((FIXTURES_DIR / "workflow_items.json").read_text())
    off_vocabulary = sorted(
        {item["status"] for item in items if item["status"] not in WORKFLOW_STATUSES}
    )
    assert not off_vocabulary, (
        f"workflow_items.json uses statuses outside the vocabulary: {off_vocabulary}"
    )


def test_write_tool_spec_offers_agents_exactly_the_canonical_stages():
    """The stage an agent may write is constrained by the spec, not by prose."""
    stage = write_tools_schema("WorkflowItemCreate")["properties"]["stage"]
    assert set(stage.get("enum", [])) == STAGES


def test_write_tool_spec_offers_agents_exactly_the_canonical_statuses():
    create = write_tools_schema("WorkflowItemCreate")["properties"]["status"]
    patch = write_tools_schema("WorkflowItemPatch")["properties"]["status"]
    assert set(create.get("enum", [])) == WORKFLOW_STATUSES
    assert set(patch.get("enum", [])) == WORKFLOW_STATUSES


@pytest.mark.parametrize("retired", sorted(LEGACY_STAGES))
def test_the_stage_the_spec_describes_names_no_retired_value(retired):
    """
    The spec teaches agents by prose as well as by schema, so a retired stage
    left in the description keeps producing rows no page reads. Scoped to the
    stage property: `career` is also a legitimate word elsewhere in the spec,
    in the "career advisor" owner role.
    """
    stage = write_tools_schema("WorkflowItemCreate")["properties"]["stage"]
    words = re.findall(r"[a-z_]+", stage["description"])
    assert retired not in words, (
        f"the spec's stage description still names the retired stage {retired!r}"
    )


@pytest.mark.parametrize("retired", sorted(LEGACY_STATUSES))
def test_the_spec_never_names_a_retired_status(retired):
    """
    Any description an agent reads — the status property, the operation summary
    it appears under — must not offer a status the frontend cannot badge.
    """
    words = re.findall(r"[a-z_]+", WRITE_TOOLS_PATH.read_text())
    assert retired not in words, (
        f"write_tools.yaml still names the retired status {retired!r}"
    )


@pytest.mark.parametrize(
    "path", source_files(), ids=lambda p: str(p.relative_to(REPO_ROOT))
)
def test_no_source_file_names_a_stage_outside_the_vocabulary(path):
    """
    Catches the shape of the original bug: a query filtering on a stage no
    writer produces, or a writer producing one no query reads.
    """
    off_vocabulary = sorted(stage_literals(path) - STAGES)
    assert not off_vocabulary, (
        f"{path.relative_to(REPO_ROOT)} names stages outside the vocabulary: "
        f"{off_vocabulary}"
    )


def test_the_frontend_draws_stages_from_the_same_vocabulary():
    """The two halves of the vocabulary are declared separately; they must agree."""
    source = FRONTEND_STAGES_PATH.read_text()
    assert set(ts_string_array(source, "STAGES")) == STAGES


def test_the_frontend_labels_and_routes_every_stage():
    """An unlabelled stage renders as a raw id; an unrouted one links to `/`."""
    source = FRONTEND_STAGES_PATH.read_text()
    for const in ("STAGE_LABELS", "STAGE_ROUTES"):
        body = re.search(rf"export const {const}[^=]*= \{{(.*?)\n\}};", source, re.DOTALL)
        assert body, f"{const} not found"
        assert set(re.findall(r"^\s{2}([a-z_]+):", body.group(1), re.MULTILINE)) == STAGES


def test_the_frontend_badges_every_workflow_status():
    """
    A status the map does not know renders as an empty badge — the visible half
    of the `complete` / `completed` split (#68).
    """
    source = FRONTEND_STATUS_PATH.read_text()
    body = re.search(
        r"export const WORKFLOW_STATUS_MAP[^=]*= \{(.*?)\n\};", source, re.DOTALL
    )
    assert body, "WORKFLOW_STATUS_MAP not found"
    mapped = set(re.findall(r"^\s{2}([a-z_]+):", body.group(1), re.MULTILINE))
    assert mapped == WORKFLOW_STATUSES


@pytest.mark.parametrize("retired,replacement", sorted(LEGACY_STAGES.items()))
def test_every_retired_stage_has_a_replacement_in_the_vocabulary(retired, replacement):
    """The migration's mapping is only useful if its target is a real stage."""
    assert retired not in STAGES
    assert replacement in STAGES
