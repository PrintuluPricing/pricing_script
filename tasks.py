from combine import create_combinations
from pricing import pricing_calculation


def calculate_pricing_job(code):
    combinations = create_combinations(code)
    combinations.to_csv(f"{code}_combinations.csv", index=False)
    pricing_calculation([f"{code}_combinations.csv"])
