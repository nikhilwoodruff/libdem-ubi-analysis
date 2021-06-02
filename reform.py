from openfisca_uk.api import *

from openfisca_uk import Microsimulation
from openfisca_uk.api import *

def child_WA_adult_UBI(revenue: float, sim: Microsimulation, child_split: float) -> Reform:
    adult_ubi = revenue * (1 - child_split) / sim.calc("is_WA_adult").sum()
    child_ubi = revenue * child_split / sim.calc("is_child").sum()
    class UBI(Variable):
        value_type = float
        entity = Person
        definition_period = YEAR
        
        def formula(person, period, parameters):
            return person("is_WA_adult", period) * adult_ubi + person("is_child", period) * child_ubi
    
    class gross_income(Variable):
        value_type = float
        entity = Person
        label = u"Gross income, including benefits"
        definition_period = YEAR

        def formula(person, period, parameters):
            COMPONENTS = [
                "employment_income",
                "pension_income",
                "self_employment_income",
                "property_income",
                "savings_interest_income",
                "dividend_income",
                "miscellaneous_income",
                "benefits",
                "UBI"
            ]
            return add(person, period, COMPONENTS)

    class reform(Reform):
        def apply(self):
            self.add_variable(UBI)
            self.update_variable(gross_income)
    
    return reform

def WA_adult_UBI(value: float) -> Reform:
    class UBI(Variable):
        value_type = float
        entity = Person
        definition_period = YEAR
        
        def formula(person, period, parameters):
            return person("is_WA_adult", period) * value
    
    class gross_income(Variable):
        value_type = float
        entity = Person
        label = u"Gross income, including benefits"
        definition_period = YEAR

        def formula(person, period, parameters):
            COMPONENTS = [
                "employment_income",
                "pension_income",
                "self_employment_income",
                "property_income",
                "savings_interest_income",
                "dividend_income",
                "miscellaneous_income",
                "benefits",
                "UBI"
            ]
            return add(person, period, COMPONENTS)

    class reform(Reform):
        def apply(self):
            self.add_variable(UBI)
            self.update_variable(gross_income)
    
    return reform

def include_UBI_in_means_tests() -> Reform:

    class universal_credit_income_reduction(Variable):
        value_type = float
        entity = BenUnit
        label = u"Reduction from income for Universal Credit"
        definition_period = MONTH

        def formula(benunit, period, parameters):
            UC = parameters(period).benefit.universal_credit
            INCOME_COMPONENTS = ["employment_income", "trading_income", "UBI"]
            earned_income = aggr(
                benunit, period, INCOME_COMPONENTS, options=[DIVIDE]
            )
            unearned_income = aggr(
                benunit,
                period,
                ["carers_allowance", "JSA_contrib", "state_pension"],
                options=[ADD],
            )
            unearned_income += aggr(
                benunit, period, ["pension_income"], options=[DIVIDE]
            )
            earned_income = max_(
                0,
                earned_income
                - aggr(
                    benunit,
                    period,
                    ["income_tax", "national_insurance"],
                    options=[DIVIDE],
                ),
            )
            housing_element = benunit("UC_eligible_rent", period)
            earnings_disregard = (
                housing_element > 0
            ) * UC.means_test.earn_disregard_with_housing + (
                housing_element == 0
            ) * UC.means_test.earn_disregard
            earnings_reduction = max_(0, earned_income - earnings_disregard)
            reduction = max_(
                0,
                unearned_income
                + UC.means_test.reduction_rate * earnings_reduction,
            )
            return reduction

    class tax_credits_applicable_income(Variable):
        value_type = float
        entity = BenUnit
        label = u"Applicable income for Tax Credits"
        definition_period = YEAR
        reference = "The Tax Credits (Definition and Calculation of Income) Regulations 2002 s. 3"

        def formula(benunit, period, parameters):
            TC = parameters(period).benefit.tax_credits
            STEP_1_COMPONENTS = [
                "taxable_pension_income",
                "taxable_savings_interest_income",
                "taxable_dividend_income",
                "taxable_property_income",
                "UBI"
            ]
            income = aggr(benunit, period, STEP_1_COMPONENTS)
            income = amount_over(income, TC.means_test.non_earned_disregard)
            STEP_2_COMPONENTS = [
                "taxable_employment_income",
                "taxable_trading_income",
                "taxable_social_security_income",
                "taxable_miscellaneous_income",
            ]
            income += aggr(benunit, period, STEP_2_COMPONENTS)
            EXEMPT_BENEFITS = ["income_support", "ESA_income", "JSA_income"]
            on_exempt_benefits = (
                add(benunit, period, EXEMPT_BENEFITS, options=[ADD]) > 0
            )
            return income * not_(on_exempt_benefits)
    
    class housing_benefit_applicable_income(Variable):
        value_type = float
        entity = BenUnit
        label = u"Relevant income for Housing Benefit means test"
        definition_period = WEEK

        def formula(benunit, period, parameters):
            WTC = parameters(period).benefit.tax_credits.working_tax_credit
            means_test = parameters(period).benefit.housing_benefit.means_test
            BENUNIT_MEANS_TESTED_BENEFITS = [
                "child_benefit",
                "income_support",
                "JSA_income",
                "ESA_income",
            ]
            INCOME_COMPONENTS = [
                "employment_income",
                "trading_income",
                "property_income",
                "pension_income",
                "UBI"
            ]
            benefits = add(benunit, period, BENUNIT_MEANS_TESTED_BENEFITS)
            income = aggr(benunit, period, INCOME_COMPONENTS, options=[DIVIDE])
            tax = aggr(
                benunit,
                period,
                ["income_tax", "national_insurance"],
                options=[DIVIDE],
            )
            income += aggr(benunit, period, ["personal_benefits"])
            income += add(benunit, period, ["tax_credits"], options=[DIVIDE])
            income -= tax
            income -= (
                aggr(benunit, period, ["pension_contributions"], options=[DIVIDE])
                * 0.5
            )
            income += benefits
            num_children = benunit.nb_persons(BenUnit.CHILD)
            max_childcare_amount = (
                num_children == 1
            ) * WTC.elements.childcare_1 + (
                num_children > 1
            ) * WTC.elements.childcare_2
            childcare_element = min_(
                max_childcare_amount,
                benunit.sum(
                    benunit.members("childcare_cost", period, options=[ADD])
                ),
            )
            applicable_income = max_(
                0,
                income
                - benunit("is_single_person", period)
                * means_test.income_disregard_single
                - benunit("is_couple", period) * means_test.income_disregard_couple
                - benunit("is_lone_parent", period)
                * means_test.income_disregard_lone_parent
                - (
                    (
                        benunit.sum(benunit.members("hours_worked", period))
                        > means_test.worker_hours
                    )
                    + (
                        benunit("is_lone_parent", period)
                        * benunit.sum(benunit.members("hours_worked", period))
                        > WTC.min_hours.lower
                    )
                )
                * means_test.worker_income_disregard
                - childcare_element,
            )
            return applicable_income
    
    class income_support_applicable_income(Variable):
        value_type = float
        entity = BenUnit
        label = u"Relevant income for Income Support means test"
        definition_period = WEEK

        def formula(benunit, period, parameters):
            IS = parameters(period).benefit.income_support
            INCOME_COMPONENTS = [
                "employment_income",
                "trading_income",
                "property_income",
                "pension_income",
                "UBI"
            ]
            income = aggr(benunit, period, INCOME_COMPONENTS, options=[DIVIDE])
            tax = aggr(
                benunit,
                period,
                ["income_tax", "national_insurance"],
                options=[DIVIDE],
            )
            income += aggr(benunit, period, ["personal_benefits"])
            income += add(benunit, period, ["child_benefit"])
            income -= tax
            income -= (
                aggr(benunit, period, ["pension_contributions"], options=[DIVIDE])
                * 0.5
            )
            family_type = benunit("family_type")
            families = family_type.possible_values
            income = max_(
                0,
                income
                - (family_type == families.SINGLE)
                * IS.means_test.income_disregard_single
                - benunit("is_couple") * IS.means_test.income_disregard_couple
                - (family_type == families.LONE_PARENT)
                * IS.means_test.income_disregard_lone_parent,
            )
            return income

    class reform(Reform):
        def apply(self):
            self.update_variable(universal_credit_income_reduction)
            self.update_variable(tax_credits_applicable_income)
            self.update_variable(housing_benefit_applicable_income)
            self.update_variable(income_support_applicable_income)
    
    return reform

def set_parameter(param: str, value: float, period="year:2018:5") -> Reform:
    def modifier(params):
        node = params
        for name in param.split("."):
            node = node.children[name]
        node.update(period=periods.period(period), value=value)
        return params
    
    class reform(Reform):
        def apply(self):
            self.modify_parameters(modifier)
            
    return reform

def set_PA(value: float):
    return set_parameter("tax.income_tax.allowances.personal_allowance.amount", value)

def set_PA_for_WA_adults(value: float):
    class personal_allowance(Variable):
        value_type = float
        entity = Person
        label = u"Personal Allowance for the year"
        definition_period = YEAR
        reference = "Income Tax Act 2007 s. 35"

        def formula(person, period, parameters):
            PA = parameters(period).tax.income_tax.allowances.personal_allowance
            ANI = person("adjusted_net_income", period)
            excess = max_(0, ANI - PA.maximum_ANI)
            reduction = excess * PA.reduction_rate
            amount = where(person("is_SP_age", period), PA.amount, value)
            amount = max_(0, amount - reduction)
            return amount
    
    class reform(Reform):
        def apply(self):
            self.update_variable(personal_allowance)

    return reform

def set_PT(value: float):
    return set_parameter("tax.national_insurance.class_1.thresholds.primary_threshold", value)

def net_cost(baseline, simulation):
    return simulation.calc("net_income").sum() - baseline.calc("net_income").sum()