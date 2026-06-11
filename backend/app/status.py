from enum import StrEnum


class StatusCode(StrEnum):
    on_track = "on_track"
    watch = "watch"
    needs_attention = "needs_attention"
    urgent = "urgent"
    opportunity = "opportunity"


status_meta: dict[StatusCode, dict] = {
    StatusCode.on_track: {"label": "On Track", "color_key": "green", "severity_rank": 1},
    StatusCode.watch: {"label": "Watch", "color_key": "amber", "severity_rank": 2},
    StatusCode.needs_attention: {"label": "Needs Attention", "color_key": "orange", "severity_rank": 3},
    StatusCode.urgent: {"label": "Urgent", "color_key": "red", "severity_rank": 4},
    StatusCode.opportunity: {"label": "Opportunity", "color_key": "teal", "severity_rank": 0},
}
