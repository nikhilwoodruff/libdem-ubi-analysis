
import plotly.graph_objects as go
import pandas as pd


def intra_decile_graph_data(baseline, *reform_sims):
    NAMES = (
        "Gain more than 5%",
        "Gain less than 5%",
        "No change",
        "Lose less than 5%",
        "Lose more than 5%"
    )[::-1]
    l = []
    for i, reform_sim in enumerate(reform_sims):
        income = baseline.calc("equiv_household_net_income", map_to="person")
        decile = income.decile_rank()
        gain = reform_sim.calc("household_net_income", map_to="person") - baseline.calc("household_net_income", map_to="person")
        rel_gain = (gain / baseline.calc("household_net_income", map_to="person")).dropna()
        bands = (None, -0.05, -1e-3, 1e-3, 0.05, None)
        for lower, upper, name in zip(bands[:-1], bands[1:], NAMES):
            fractions = []
            for i in range(1, 11):
                subset = rel_gain[decile == i]
                if lower is not None:
                    subset = subset[rel_gain > lower]
                if upper is not None:
                    subset = subset[rel_gain <= upper]
                fractions += [subset.count() / rel_gain[decile == i].count()]
            tmp = pd.DataFrame({"reform": i, "fraction": fractions, "decile": list(range(1, 11)), "band": name})
            l.append(tmp)
        return pd.concat(l)


def intra_decile_graph(base, reform):
    COLORS = (
        "#9E9E9E",
        "#E0E0E0",
        "#444444",
        "#C5E1A5",
        "#558B2F",
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(x=fractions, y=list(range(1, 11)), name=name, orientation="h", marker_color=color))
    fig.update_layout(barmode="stack", title="Intra-decile outcomes", xaxis_title="Percentage of decile", xaxis_tickformat="%", yaxis_tickvals=list(range(1, 11)), yaxis_title="Decile")