import plotly.graph_objects as go
import streamlit as st


def group_conditions_by_type(conditions):
    grouped = {}
    for condition in conditions:
        grouped.setdefault(condition.condition_type.value, []).append(condition)
    return grouped


def condition_interval(condition, domain_max):
    threshold = float(condition.threshold)
    direction = condition.direction.value

    if direction in (">", ">="):
        return (threshold, domain_max)
    if direction in ("<", "<="):
        return (0.0, threshold)
    return (threshold, threshold)


def merge_intervals(intervals):
    if not intervals:
        return []

    ordered = sorted(intervals, key=lambda item: item[0])
    merged = [ordered[0]]

    for start, end in ordered[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))

    return merged


def highlight_intervals(conditions, operator, domain_max):
    if operator == "or":
        intervals = [condition_interval(condition, domain_max) for condition in conditions]
        return merge_intervals(intervals)

    lower = 0.0
    upper = domain_max
    equals = None

    for condition in conditions:
        threshold = float(condition.threshold)
        direction = condition.direction.value
        if direction in (">", ">="):
            lower = max(lower, threshold)
        elif direction in ("<", "<="):
            upper = min(upper, threshold)
        else:
            equals = threshold

    if equals is not None:
        return [(equals, equals)]
    if lower > upper:
        return []
    return [(lower, upper)]


def render_condition_number_line(condition_type, conditions, actual, operator):
    thresholds = [float(condition.threshold) for condition in conditions]
    max_value = max(thresholds + ([float(actual)] if actual is not None else [0.0]) + [1.0])
    domain_max = max_value * 1.15

    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=[0, domain_max],
            y=[0, 0],
            mode="lines",
            line={"color": "#cbd5e1", "width": 8},
            hoverinfo="skip",
            showlegend=False,
        )
    )

    for start, end in highlight_intervals(conditions, operator, domain_max):
        if start == end:
            figure.add_trace(
                go.Scatter(
                    x=[start, end],
                    y=[0, 0],
                    mode="markers",
                    marker={"color": "#10b981", "size": 12},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )
        else:
            figure.add_trace(
                go.Scatter(
                    x=[start, end],
                    y=[0, 0],
                    mode="lines",
                    line={"color": "#86efac", "width": 14},
                    hoverinfo="skip",
                    showlegend=False,
                )
            )

    for condition in conditions:
        threshold = float(condition.threshold)
        figure.add_trace(
            go.Scatter(
                x=[threshold, threshold],
                y=[-0.1, 0.1],
                mode="lines+text",
                line={"color": "#2563eb", "width": 3},
                text=[None, f"{condition.direction.value} {threshold:g}"],
                textposition="top center",
                hoverinfo="skip",
                showlegend=False,
            )
        )

    if actual is not None:
        figure.add_trace(
            go.Scatter(
                x=[float(actual)],
                y=[0],
                mode="markers+text",
                marker={"color": "#111827", "size": 10},
                text=[f"{actual:g}"],
                textposition="bottom center",
                hoverinfo="skip",
                showlegend=False,
            )
        )

    figure.update_xaxes(range=[0, domain_max], visible=False)
    figure.update_yaxes(range=[-0.35, 0.35], visible=False)
    figure.update_layout(
        height=120,
        margin={"l": 0, "r": 0, "t": 8, "b": 8},
        plot_bgcolor="white",
        paper_bgcolor="white",
    )

    st.caption(condition_type)
    st.plotly_chart(figure, use_container_width=True, config={"displayModeBar": False})
