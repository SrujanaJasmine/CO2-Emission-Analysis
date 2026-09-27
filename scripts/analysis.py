"""
analysis.py
Exploratory analysis of cleaned OWID CO2 data.
Produces summary stats + charts saved into reports/.

Usage:
    python scripts/analysis.py
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

DATA_PATH = Path("data/processed/co2_cleaned.csv")
WORLD_PATH = Path("data/processed/co2_world_aggregates.csv")
REPORTS_DIR = Path("reports")

sns.set_theme(style="whitegrid")


def load_data():
    df = pd.read_csv(DATA_PATH)
    world = pd.read_csv(WORLD_PATH)
    return df, world


# ---------------------------------------------------------------------------
# 1. Global emissions trend over time
# ---------------------------------------------------------------------------
def global_trend(world: pd.DataFrame):
    world_only = world[world["country"] == "World"]
    plt.figure(figsize=(10, 5))
    plt.plot(world_only["year"], world_only["co2"], color="firebrick", linewidth=2)
    plt.title("Global CO2 Emissions Over Time")
    plt.xlabel("Year")
    plt.ylabel("CO2 Emissions (million tonnes)")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "01_global_trend.png", dpi=150)
    plt.close()

    latest = world_only.sort_values("year").iloc[-1]
    print(f"Latest global emissions ({int(latest['year'])}): {latest['co2']:,.0f} Mt")


# ---------------------------------------------------------------------------
# 2. Top 10 emitting countries (latest year)
# ---------------------------------------------------------------------------
def top_emitters(df: pd.DataFrame, n: int = 10):
    latest_year = df["year"].max()
    latest = df[df["year"] == latest_year]
    top = latest.nlargest(n, "co2")[["country", "co2", "co2_per_capita"]]

    plt.figure(figsize=(9, 6))
    sns.barplot(data=top, y="country", x="co2", hue="country", legend=False, palette="Reds_r")
    plt.title(f"Top {n} CO2 Emitters ({latest_year})")
    plt.xlabel("CO2 Emissions (million tonnes)")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "02_top_emitters.png", dpi=150)
    plt.close()

    print(f"\nTop {n} emitters in {latest_year}:")
    print(top.to_string(index=False))
    return top


# ---------------------------------------------------------------------------
# 3. Emissions vs GDP per capita (are richer countries always higher emitters
#    per person? classic decoupling question)
# ---------------------------------------------------------------------------
def emissions_vs_gdp(df: pd.DataFrame):
    # GDP reporting lags emissions data by a few years in this dataset,
    # so use the latest year that actually has GDP coverage, not the
    # latest year overall.
    has_gdp = df.dropna(subset=["gdp_per_capita"])
    latest_year = has_gdp["year"].max()
    latest = df[(df["year"] == latest_year) & (df["population"] > 1_000_000)].dropna(
        subset=["gdp_per_capita", "co2_per_capita"]
    )

    plt.figure(figsize=(9, 6))
    sns.scatterplot(
        data=latest, x="gdp_per_capita", y="co2_per_capita",
        size="population", sizes=(20, 400), alpha=0.6, legend=False,
    )
    plt.xscale("log")
    plt.title(f"GDP per Capita vs CO2 per Capita ({latest_year})")
    plt.xlabel("GDP per Capita (log scale, USD)")
    plt.ylabel("CO2 per Capita (tonnes)")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "03_gdp_vs_emissions.png", dpi=150)
    plt.close()

    corr = latest["gdp_per_capita"].corr(latest["co2_per_capita"])
    print(f"\nCorrelation between GDP per capita and CO2 per capita: {corr:.2f}")


# ---------------------------------------------------------------------------
# 4. Fuel source breakdown for top emitters
# ---------------------------------------------------------------------------
def fuel_mix(df: pd.DataFrame, countries=("China", "United States", "India", "Russia", "Japan")):
    latest_year = df["year"].max()
    subset = df[(df["year"] == latest_year) & (df["country"].isin(countries))]
    fuel_cols = ["coal_co2", "oil_co2", "gas_co2", "cement_co2"]
    melted = subset.melt(id_vars="country", value_vars=fuel_cols,
                          var_name="source", value_name="emissions")

    plt.figure(figsize=(10, 6))
    sns.barplot(data=melted, x="country", y="emissions", hue="source")
    plt.title(f"CO2 Emissions by Fuel Source, Top Economies ({latest_year})")
    plt.ylabel("CO2 Emissions (million tonnes)")
    plt.xlabel("")
    plt.legend(title="Source")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "04_fuel_mix.png", dpi=150)
    plt.close()


# ---------------------------------------------------------------------------
# 5. Historical cumulative responsibility (who has emitted the most since 1900?)
# ---------------------------------------------------------------------------
def cumulative_responsibility(df: pd.DataFrame, n: int = 10):
    latest_year = df["year"].max()
    latest = df[df["year"] == latest_year]
    top_cumulative = latest.nlargest(n, "cumulative_co2")[["country", "cumulative_co2"]]

    plt.figure(figsize=(9, 6))
    sns.barplot(data=top_cumulative, y="country", x="cumulative_co2",
                hue="country", legend=False, palette="Oranges_r")
    plt.title(f"Top {n} Countries by Cumulative CO2 Emissions (1900–{latest_year})")
    plt.xlabel("Cumulative CO2 (million tonnes)")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(REPORTS_DIR / "05_cumulative_emissions.png", dpi=150)
    plt.close()

    print(f"\nTop {n} cumulative emitters (1900–{latest_year}):")
    print(top_cumulative.to_string(index=False))


def main():
    REPORTS_DIR.mkdir(exist_ok=True)
    df, world = load_data()

    global_trend(world)
    top_emitters(df)
    emissions_vs_gdp(df)
    fuel_mix(df)
    cumulative_responsibility(df)

    print(f"\nAll charts saved to {REPORTS_DIR}/")


if __name__ == "__main__":
    main()
