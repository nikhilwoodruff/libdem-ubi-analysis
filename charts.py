
import plotly.graph_objects as go


def intra_decile_graph(baseline, reform_sim):
    COLORS = (
        "#9E9E9E",
        "#E0E0E0",
        "#444444",
        "#C5E1A5",
        "#558B2F",
    )
    NAMES = (
        "Gain more than 5%",
        "Gain less than 5%",
        "No change",
        "Lose less than 5%",
        "Lose more than 5%"
    )[::-1]
    fig = go.Figure()
    income = baseline.calc("equiv_household_net_income", map_to="person")
    decile = income.decile_rank()
    gain = reform_sim.calc("household_net_income", map_to="person") - baseline.calc("household_net_income", map_to="person")
    rel_gain = (gain / baseline.calc("household_net_income", map_to="person")).dropna()
    bands = (None, -0.05, -1e-2, 1e-2, 0.05, None)
    for lower, upper, color, name in zip(bands[:-1], bands[1:], COLORS, NAMES):
        fractions = []
        for i in range(1, 11):
            subset = rel_gain[decile == i]
            if lower is not None:
                subset = subset[rel_gain > lower]
            if upper is not None:
                subset = subset[rel_gain <= upper]
            fractions += [subset.count() / rel_gain[decile == i].count()]
        fig.add_trace(go.Bar(x=fractions, y=list(range(1, 11)), name=name, orientation="h", marker_color=color))
    return fig.update_layout(barmode="stack", title="Intra-decile outcomes", xaxis_title="Percentage of decile", xaxis_tickformat="%", yaxis_tickvals=list(range(1, 11)), yaxis_title="Decile")
