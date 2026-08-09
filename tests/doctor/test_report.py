"""Report assembly: worst-of summary, red-before-yellow next actions, canonical rendering."""

import json

from cosmos77_cop.doctor.report import (
    GREEN,
    RED,
    YELLOW,
    Stage,
    build_report,
    next_actions,
    render,
    skipped,
    worst,
)


def test_worst_orders_green_yellow_red():
    assert worst([]) == GREEN
    assert worst([GREEN, GREEN]) == GREEN
    assert worst([GREEN, YELLOW]) == YELLOW
    assert worst([YELLOW, RED, GREEN]) == RED


def test_next_actions_red_first_then_yellow_prefers_fix_line():
    stages = [
        Stage("locks", YELLOW, "scent differs", fix_line="run --scent-model"),
        Stage("contract", RED, "missing tool", fix_line="add negotiate"),
        Stage("reach", GREEN, "ready"),
    ]
    actions = next_actions(stages)
    assert actions[0] == "[contract] add negotiate"
    assert actions[1] == "[locks] run --scent-model"
    assert len(actions) == 2


def test_all_green_says_ready():
    assert next_actions([Stage("reach", GREEN, "ok")]) == [
        "ready: no blocking findings — agree a window and play"
    ]


def test_skipped_stage_is_green_and_labeled():
    stage = skipped("uid", "no --their-config given")
    assert stage.status == GREEN
    assert stage.finding.startswith("skipped — ")


def test_build_report_shape_and_canonical_render():
    stages = [
        Stage("reach", GREEN, "ready", detail={"probes": []}),
        Stage("uid", YELLOW, "wrapper differs", fix_line="fix agreed_between"),
    ]
    report = build_report(stages=stages, target={"mode": "offline"}, generated_by="doctor-test")
    assert report["summary"]["status"] == YELLOW
    assert report["stages"]["uid"]["fix_line"] == "fix agreed_between"
    assert "fix_line" not in report["stages"]["reach"]
    line = render(report)
    assert "\n" not in line
    assert line.startswith('{"doctor_version":1,')  # sorted keys, compact separators
    assert json.loads(line) == report
