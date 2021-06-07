from ubicenter import format_fig
from openfisca_uk import Microsimulation
import numpy as np
import pandas as pd
import plotly.express as px
from reform import (
    WA_adult_UBI,
    all_UBI,
    adult_UBI,
    non_pensioner_UBI,
    set_PA,
    set_PT,
    set_PA_for_WA_adults,
    include_UBI_in_means_tests,
    net_cost,
)

reform_df = pd.DataFrame(
    {
        "Adult PA (£/year)": [2500, 0, 2500, 2500, 2500, 0],
        "Pensioner PA (£/year)": [12500, 12500, 2500, 12500, 12500, 0],
        "NI Primary Threshold (£/week)": [50, 0, 50, 50, 50, 0],
        "UBI for children": [False, False, False, True, False, True],
        "UBI for pensioners": [False, False, True, False, False, True],
        "UBI in means tests": [True, True, True, True, False, False],
    }
)

baseline = Microsimulation(year=2020)


def create_reform(params: dict):
    reform = []
    reform += [set_PA(float(params["Pensioner PA (£/year)"]))]
    reform += [set_PA_for_WA_adults(float(params["Adult PA (£/year)"]))]
    reform += [set_PT(float(params["NI Primary Threshold (£/week)"]))]
    tax_reform_sim = Microsimulation(*reform, year=2020)
    revenue = net_cost(tax_reform_sim, baseline)
    if params["UBI for children"]:  # doesn't handle non-adult UBIs
        if params["UBI for pensioners"]:
            ubi_reform_func = all_UBI
            population = baseline.calc("people").sum()
        else:
            ubi_reform_func = non_pensioner_UBI
            population = (
                baseline.calc("is_child").sum()
                + baseline.calc("is_WA_adult").sum()
            )
    else:
        if params["UBI for pensioners"]:
            ubi_reform_func = adult_UBI
            population = baseline.calc("is_adult").sum()
        else:
            ubi_reform_func = WA_adult_UBI
            population = baseline.calc("is_WA_adult").sum()
    if params["UBI in means tests"]:
        ubi_amount = int(revenue / population / 52) * 52
        net_revenue = -net_cost(
            baseline,
            Microsimulation(
                (
                    reform,
                    ubi_reform_func(ubi_amount),
                    include_UBI_in_means_tests(),
                ),
                year=2020,
            ),
        )
        prev_amounts = []
        while (
            net_revenue > 1e9 or net_revenue < -1e9
        ) and ubi_amount not in prev_amounts:
            old_ubi_amount = ubi_amount
            prev_amounts += [old_ubi_amount]
            ubi_amount += 1 * 52 * (2 * (net_revenue > 0) - 1)
            net_revenue = -net_cost(
                baseline,
                Microsimulation(
                    (
                        reform,
                        ubi_reform_func(ubi_amount),
                        include_UBI_in_means_tests(),
                    ),
                    year=2020,
                ),
            )
        reform += [ubi_reform_func(ubi_amount), include_UBI_in_means_tests()]
    else:
        ubi_amount = int(revenue / population / 52) * 52
        reform += [ubi_reform_func(ubi_amount)]
    return tuple(reform)


def rel(x, y):
    return (y - x) / x


UBI_amounts = []
poverty_changes = []
deep_poverty_changes = []
costs = []
winners = []
losers = []
gini_changes = []

from tqdm import tqdm

for i in tqdm(range(len(reform_df))):
    reform = create_reform(reform_df.iloc[i])
    reform_sim = Microsimulation(reform, year=2020)
    UBI_amounts += [reform_sim.calc("UBI").max()]
    poverty_changes += [
        rel(
            baseline.calc("in_poverty_bhc", map_to="person").mean(),
            reform_sim.calc("in_poverty_bhc", map_to="person").mean(),
        )
    ]
    deep_poverty_changes += [
        rel(
            baseline.calc("in_deep_poverty_bhc", map_to="person").mean(),
            reform_sim.calc("in_deep_poverty_bhc", map_to="person").mean(),
        )
    ]
    gini_changes += [
        rel(
            baseline.calc("household_net_income", map_to="person").gini(),
            reform_sim.calc("household_net_income", map_to="person").gini(),
        )
    ]
    winners += [
        (
            reform_sim.calc("household_net_income", map_to="person")
            > baseline.calc("household_net_income", map_to="person") + 1
        ).mean()
    ]
    losers += [
        (
            reform_sim.calc("household_net_income", map_to="person")
            < baseline.calc("household_net_income", map_to="person") - 1
        ).mean()
    ]
    costs += [net_cost(baseline, reform_sim)]

results_df = pd.DataFrame(
    {
        "UBI amount": pd.Series(UBI_amounts).astype(int),
        "Poverty change (%)": pd.Series(poverty_changes).apply(
            lambda x: round(x * 100, 1)
        ),
        "Deep poverty change (%)": pd.Series(deep_poverty_changes).apply(
            lambda x: round(x * 100, 1)
        ),
        "Winners (%)": pd.Series(winners).apply(lambda x: round(x * 100, 1)),
        "Losers (%)": pd.Series(losers).apply(lambda x: round(x * 100, 1)),
        "Inequality change (%)": pd.Series(gini_changes).apply(
            lambda x: round(x * 100, 1)
        ),
        "Net cost (£bn/year)": pd.Series(costs).apply(
            lambda x: round(x / 1e9, 1)
        ),
    }
)

output = pd.concat([reform_df, results_df], axis=1)
output.index = [
    "Baseline",
    "Full PA/PT elimination",
    "Include pensioners",
    "Include children",
    "Exclude from means tests",
    "All",
]
output
