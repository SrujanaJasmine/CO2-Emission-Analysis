"""
cleaning.py
Cleans the raw OWID CO2 dataset and produces an analysis-ready CSV
for use in Python analysis and Power BI.

Usage:
    python scripts/cleaning.py
"""

import pandas as pd
import numpy as np
from pathlib import Path

RAW_PATH = Path("data/raw/owid-co2-data.csv")
PROCESSED_PATH = Path("data/processed/co2_cleaned.csv")

# Columns we actually need for this project.
KEEP_COLS = [
    "country", "year", "iso_code", "population", "gdp",
    "co2", "co2_per_capita", "co2_growth_prct",
    "coal_co2", "oil_co2", "gas_co2", "cement_co2",
    "cumulative_co2", "share_global_co2",
    "temperature_change_from_co2",
    "primary_energy_consumption", "energy_per_capita",
]

# Fuel-source breakdown columns: missing here genuinely means "negligible
# or not produced", so 0 is a real, correct value — not a placeholder.
FUEL_COLS = ["coal_co2", "oil_co2", "gas_co2", "cement_co2"]

# OWID includes aggregate rows (continents, income groups, "World") that
# don't have an iso_code. We keep them in a separate file since they're
# useful for global trend charts but should be excluded from country rankings.
AGGREGATE_NAMES = [
    "World", "Asia", "Africa", "Europe", "North America", "South America",
    "Oceania", "European Union (27)", "European Union (28)",
    "High-income countries", "Low-income countries",
    "Lower-middle-income countries", "Upper-middle-income countries",
    "International transport", "Antarctica",
]


def load_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    print(f"Loaded raw data: {df.shape[0]:,} rows, {df.shape[1]} columns")
    return df


def select_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in KEEP_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Expected columns missing from source data: {missing}")
    return df[KEEP_COLS].copy()


def filter_years(df: pd.DataFrame, start_year: int = 1900) -> pd.DataFrame:
    # Data before 1900 is sparse (mostly just cumulative_co2 estimates).
    # 1900+ gives good coverage while keeping the historical sweep.
    return df[df["year"] >= start_year].copy()


def split_countries_and_aggregates(df: pd.DataFrame):
    is_aggregate = df["country"].isin(AGGREGATE_NAMES) | df["iso_code"].isna()
    countries = df[~is_aggregate].copy()
    aggregates = df[is_aggregate].copy()
    return countries, aggregates


def clean_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Missingness here isn't one problem — each column fails for a different
    reason, so each gets a different fix instead of a blanket dropna/fillna.
    """
    # Rows with no co2 figure at all aren't usable for emissions analysis.
    df = df.dropna(subset=["co2"])

    # --- Fuel-source columns: absence is a real zero, not an unknown ---
    df[FUEL_COLS] = df[FUEL_COLS].fillna(0)

    df["has_gdp"] = df["gdp"].notna()

    df["has_energy_data"] = df["energy_per_capita"].notna()
    min_energy_year = df.loc[df["has_energy_data"], "year"].min()
    print(f"Energy data available from {int(min_energy_year)} onward "
          f"({df['has_energy_data'].mean()*100:.1f}% of rows have it)")

    missing_growth = df[df["co2_growth_prct"].isna()]
    first_year_rows = df.sort_values(["country", "year"]).groupby("country").head(1)
    pct_explained = missing_growth.index.isin(first_year_rows.index).mean() * 100
    print(f"co2_growth_prct: {pct_explained:.1f}% of its missing values are "
          f"each country's first year (expected) — left as NaN, not filled")

    return df


def add_derived_columns(df: pd.DataFrame) -> pd.DataFrame:
    # These will correctly propagate NaN wherever gdp is missing — that's
    # intentional, not a bug. Don't fillna afterward to "fix" it.
    df["gdp_per_capita"] = df["gdp"] / df["population"]
    df["co2_per_gdp_musd"] = df["co2"] / (df["gdp"] / 1_000_000)  # tons CO2 per $M GDP
    df["decade"] = (df["year"] // 10) * 10
    return df


def remove_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["country", "year"])
    after = len(df)
    if before != after:
        print(f"Removed {before - after} duplicate country-year rows")
    return df


def print_data_quality_summary(df: pd.DataFrame) -> None:
    print("\nFinal missing % by column:")
    print((df.isna().mean() * 100).round(1).sort_values(ascending=False).to_string())
    print(f"\nRows with usable GDP data: {df['has_gdp'].sum():,} / {len(df):,}")
    print(f"Rows with usable energy data: {df['has_energy_data'].sum():,} / {len(df):,}")


def main():
    df = load_raw(RAW_PATH)
    df = select_columns(df)
    df = filter_years(df, start_year=1900)

    countries, aggregates = split_countries_and_aggregates(df)
    countries = clean_missing_values(countries)
    countries = remove_duplicates(countries)
    countries = add_derived_columns(countries)

    print_data_quality_summary(countries)

    PROCESSED_PATH.parent.mkdir(parents=True, exist_ok=True)
    countries.to_csv(PROCESSED_PATH, index=False)

    agg_path = PROCESSED_PATH.parent / "co2_world_aggregates.csv"
    aggregates.to_csv(agg_path, index=False)

    print(f"\nSaved cleaned country-level data -> {PROCESSED_PATH}")
    print(f"  {countries.shape[0]:,} rows, {countries.shape[1]} columns")
    print(f"  Years: {countries['year'].min()}–{countries['year'].max()}")
    print(f"  Countries: {countries['country'].nunique()}")
    print(f"Saved aggregate/regional data -> {agg_path}")


if __name__ == "__main__":
    main()