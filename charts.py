
import plotly.graph_objects as go
import pandas as pd
NAMES = (
        "Gain more than 5%",
        "Gain less than 5%",
        "No change",
        "Lose less than 5%",
        "Lose more than 5%"
    )

def intra_decile_graph_data(baseline, *reform_sims):
    AMOUNTS = [45, 60, 75, 90]
    l = []
    for i, reform_sim in enumerate(reform_sims):
        income = baseline.calc("equiv_household_net_income", map_to="person")
        decile = income.decile_rank()
        gain = reform_sim.calc("household_net_income", map_to="person") - baseline.calc("household_net_income", map_to="person")
        rel_gain = (gain / baseline.calc("household_net_income", map_to="person")).dropna()
        bands = (None, 0.05, 1e-3, -1e-3, -0.05, None)
        for upper, lower, name in zip(bands[:-1], bands[1:], NAMES):
            fractions = []
            for j in range(1, 11):
                subset = rel_gain[decile == j]
                if lower is not None:
                    subset = subset[rel_gain > lower]
                if upper is not None:
                    subset = subset[rel_gain <= upper]
                fractions += [subset.count() / rel_gain[decile == j].count()]
            tmp = pd.DataFrame({"UBI": f"£{AMOUNTS[i]}/week", "fraction": fractions, "decile": list(range(1, 11)), "band": name})
            l.append(tmp)
    return pd.concat(l).reset_index()