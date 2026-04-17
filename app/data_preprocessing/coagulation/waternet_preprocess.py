"""Preprocess raw data.""" #as it is in GitHub repository, provided by KWR: 
import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from datetime import datetime, timezone

from data_processing.config import (
    AGGREGATION_PERIOD_PRD,
    AGGREGATION_PERIOD_TRAIN,
    INPUT_COLUMNS,
    LAST_DREDGING_DATE,
    TARGET_COLUMN,
)

def clean_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Clean up column names: Replace spaces and slashes with underscores, removed brackets, letters to lowercase.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features

    Returns:
        df (pd.DataFrame): The DataFrame with cleaned up column names
    """
    df.columns = (
        df.columns.str.replace(" ", "_", regex=False)
        .str.replace("/", "_", regex=False)
        .str.replace("(", "", regex=False)
        .str.replace(")", "", regex=False)
    )
    df.columns = df.columns.str.lower()

    return df


def calculate_days_after_dredging(df: pd.DataFrame, train: bool = False) -> pd.DataFrame:
    """Finds periods where dredging took place and calculates how many days have passed.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features
        train (bool): If this function is called for training or for in production

    Returns:
        df (pd.DataFrame): The DataFrame with added after_dredging columns
    """
    if train:
        df["date"] = pd.to_datetime(df["date"])

        for lane in [1, 2, 3]:
            other_lanes = [f"flow_coagulation_{i}" for i in {1, 2, 3} - {lane}]

            # Calculate dredging for lanes
            df[f"dredging_{lane}"] = df[f"flow_coagulation_{lane}"].between(
                2000, df[other_lanes].max(axis=1) * 0.9, inclusive="neither"
            ) & df["date"].dt.month.between(4, 8, inclusive="neither")

        # for 2024 the wrong lane got half flow we switch dredging from lane 3 to lane 1
        # as lane 1 is dredged (and a part of lane 2)
        dredging_3_in_2024 = (df["date"].dt.year == 2024) & df["dredging_3"]
        df.loc[dredging_3_in_2024, "dredging_1"] = True
        df.loc[dredging_3_in_2024, "dredging_3"] = False

        for lane in [1, 2, 3]:
            dredging = df[f"dredging_{lane}"]

            # If there is a gap of at most 2 hours between two periods of dredging, count this as dredging
            groups = (dredging != dredging.shift()).cumsum()
            # Calculate the size of each group
            group_sizes = dredging.groupby(groups).transform("size")
            max_gap_samples = (2 * 60) / 5  # 2 houds
            # Fill gaps
            dredging = pd.Series(np.where((~dredging) & (group_sizes <= max_gap_samples), True, dredging))

            # If there is less than a day of dredging detected, do not count this as dredging
            groups = (dredging != dredging.shift()).cumsum()
            # Calculate the size of each group
            group_sizes = dredging.groupby(groups).transform("size")
            min_samples = (24 * 60) / 5  # 1 day
            # Filter short events
            dredging = pd.Series(np.where(dredging & (group_sizes <= min_samples), False, dredging))

            # Calculate the days after dredging for each lane
            samples_per_day = 12 * 24
            df[f"after_dredging_{lane}"] = (df.groupby(dredging.cumsum()).cumcount() + 1) // samples_per_day
    else:
        time_diffs_in_days = {
            lane: (datetime.now(timezone.utc) - datetime.strptime(dredging_date, "%Y-%m-%d %H:%M:%S%z")).days
            for lane, dredging_date in LAST_DREDGING_DATE.items()
        }
        df["after_dredging"] = df["lane"].map(time_diffs_in_days).astype(float)

    return df


def calculate_fecl_concentration(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate FeCl3 concentrations.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features

    Returns:
        df (pd.DataFrame): The DataFrame with fecl3_concentrations calculated
    """
    # Add up dosages of pumps to calculate total dosage
    df["fecl3_dosage_lane_1"] = df["fecl3_dosage_lane_1_09_10"] + df["fecl3_dosage_lane_1_11_12"]
    df["fecl3_dosage_lane_2"] = df["fecl3_dosage_lane_2_05_06"] + df["fecl3_dosage_lane_2_07_08"]
    df["fecl3_dosage_lane_3"] = df["fecl3_dosage_lane_3_01_02"] + df["fecl3_dosage_lane_3_03_04"]

    # Calculate FeCl3 concentration for the different lanes
    df["fecl3_concentration_1"] = df["fecl3_dosage_lane_1"] * 192 / df["flow_coagulation_1"]
    df["fecl3_concentration_2"] = df["fecl3_dosage_lane_2"] * 192 / df["flow_coagulation_2"]
    df["fecl3_concentration_3"] = df["fecl3_dosage_lane_3"] * 192 / df["flow_coagulation_3"]

    return df


def reshape_dataframe(df: pd.DataFrame, train: bool = False) -> pd.DataFrame:
    """Pivot the data frame such that each row corresponds to an observation for a specific lane.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features
        train (bool): If this function is called for training or for in production

    Returns:
        df (pd.DataFrame): The DataFrame reshaped
    """
    value_vars = [
        "flow_coagulation_1",
        "flow_coagulation_2",
        "flow_coagulation_3",
        "ftu_section_1",
        "ftu_section_2",
        "ftu_section_3",
        "fecl3_concentration_1",
        "fecl3_concentration_2",
        "fecl3_concentration_3",
    ]

    if train:
        value_vars.extend(f"after_dredging_{lane}" for lane in [1, 2, 3])

    df = df.melt(
        id_vars=["date", "flow_raw_water", "temperature_raw_water", "ph_raw_water", "ftu_raw_water"],
        value_vars=value_vars,
        var_name="variable",
        value_name="value",
    )

    # Extracting information from the variabble column
    df[["variable", "lane"]] = df["variable"].str.extract(r"(.+)_(.)")

    # Pivot the DataFrame to get the desired structure
    df = (
        df.pivot(
            index=[
                "date",
                "flow_raw_water",
                "temperature_raw_water",
                "ph_raw_water",
                "ftu_raw_water",
                "lane",
            ],
            columns="variable",
            values="value",
        )
        .reset_index()
        .rename_axis(columns=None)
    )

    # df.lane = df.lane.astype(int)

    return df


def aggregate_data(df: pd.DataFrame, train: bool = False) -> pd.DataFrame:
    """Aggregate data over hours.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features
        train (bool): Whether to prepare the data for training (True) or for running in production (False)

    Returns:
        df (pd.DataFrame): The DataFrame aggregated
    """
    df["date"] = pd.to_datetime(df["date"])
    # Count NaNs
    df["nans"] = df.isna().max(axis=1)
    resample_period = pd.Timedelta(**AGGREGATION_PERIOD_TRAIN) if train else pd.Timedelta(**AGGREGATION_PERIOD_PRD)
    origin = "start_day" if train else "end"  # In production, we want the most recent complete aggregated observation
    df = df.groupby("lane").resample(resample_period, on="date", origin=origin).mean(numeric_only=True).reset_index()
    df = df.sort_values("date", ascending=True)

    if train:
        # Add the ftu_section with a delay of 2x2=4 hours to the current row for training purposes
        df["ftu_section"] = df.groupby("lane")["ftu_section"].shift(-2)
        # Remove rows with more than 30% NaNs
        df = df.dropna()
        df = df[df["nans"] <= 0.3]

    return df


def keep_periods(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only selected periods for given lanes.

    Args:
        df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features.

    Returns:
        df: The DataFrame with only kept periods
    """
    periods = [
        ("2021-01-28", "2021-02-15", ["1", "2", "3"]),
        ("2021-02-25", "2021-03-11", ["1", "2", "3"]),
        ("2021-06-13", "2021-06-21", ["2"]),
        ("2021-06-24", "2021-06-28", ["2"]),
        ("2021-07-13", "2021-08-03", ["1", "2", "3"]),
        ("2021-09-15", "2021-09-22", ["1", "2", "3"]),
        ("2021-09-15", "2021-09-22", ["1", "2", "3"]),
        ("2022-01-03", "2022-02-18", ["1", "2", "3"]),
        ("2022-05-19", "2022-05-31", ["2", "3"]),
        ("2023-02-18", "2023-03-01", ["1", "2", "3"]),
        ("2023-02-18", "2023-03-01", ["1", "2", "3"]),
        ("2023-09-17", "2023-12-04", ["1", "2", "3"]),
        ("2023-12-04", "2023-12-14", ["2", "3"]),
        ("2023-12-14", "2024-01-31", ["1", "2", "3"]),
        ("2024-01-31", "2024-02-06", ["1", "3"]),
        ("2024-02-27", "2024-03-09", ["3"]),
        ("2024-05-23", "2024-06-15", ["1", "2", "3"]),
    ]

    df_parts = []
    for start_datetime, end_datetime, lanes_to_keep in periods:
        mask = (df["date"] >= start_datetime) & (df["date"] <= end_datetime) & (df["lane"].isin(lanes_to_keep))
        df_parts.append(df[mask])

    return pd.concat(df_parts, axis=0, ignore_index=True)


def add_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add date features for the model.

    Args:
        df (pd.DataFrame): Input DataFrame with a dates as index and relevant features.

    Returns:
        df: The DataFrame with date features
    """
    df["year"] = df.index.year
    df["day_of_week"] = df.index.dayofweek
    df["hour"] = df.index.hour

    return df


def train_test_split(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split the data into train and test sets.

    The first 3 weeks of a month are taken for the train set and the last week of the month for the test set.

    Args:
        df (pd.DataFrame): A DataFrame with a 'date' column as index and relevant features

    Returns:
        Tuple[pd.DataFrame,pd.DataFrame,pd.DataFrame]: x_train, y_train, test
    """
    # Get the indices of the dates that are the first 3 weeks in the month
    train_mask = ((df.index.day - 1) // 7 + 1) <= 3

    # Split the DataFrame based on the masks
    x_train = df[train_mask][INPUT_COLUMNS]
    y_train = df[train_mask][TARGET_COLUMN]
    x_test = df[~train_mask][INPUT_COLUMNS]
    y_test = df[~train_mask][TARGET_COLUMN]

    return x_train, y_train, x_test, y_test


# def clean_outliers(df):
#     """Replace strange values with nan."""
#     # There is a difference between the sum of the flow rates and the total flow rate
#     sum_flow_rates = df[["flow_coagulation_1", "flow_coagulation_2", "flow_coagulation_3"]].sum(axis=1)
#     flow_rate_mismatch = (df["flow_raw_water"] - sum_flow_rates).abs() > 1000
#     df["flow_coagulation_1"] = np.where(flow_rate_mismatch, np.nan, df["flow_coagulation_1"])
#     df["flow_coagulation_2"] = np.where(flow_rate_mismatch, np.nan, df["flow_coagulation_2"])
#     df["flow_coagulation_3"] = np.where(flow_rate_mismatch, np.nan, df["flow_coagulation_3"])
#     df["flow_raw_water"] = np.where(flow_rate_mismatch, np.nan, df["flow_raw_water"])
#     # Flow rates are too small
#     df["flow_coagulation_1"] = np.where(df["flow_coagulation_1"] < 1000, np.nan, df["flow_coagulation_1"])
#     df["flow_coagulation_2"] = np.where(df["flow_coagulation_2"] < 1000, np.nan, df["flow_coagulation_2"])
#     df["flow_coagulation_3"] = np.where(df["flow_coagulation_3"] < 1000, np.nan, df["flow_coagulation_3"])
#     # FTU in is too small
#     df["ftu_raw_water"] = np.where(df["ftu_raw_water"] <= 3, np.nan, df["ftu_raw_water"])
#     # Temperature is out of bounds
#     df["temperature_raw_water"] = np.where(df["temperature_raw_water"] < 3, np.nan, df["temperature_raw_water"])
#     df["temperature_raw_water"] = np.where(df["temperature_raw_water"] > 27, np.nan, df["temperature_raw_water"])
#     # Ph is out of bounds
#     df["ph_raw_water"] = np.where(df["ph_raw_water"] < 7.5, np.nan, df["ph_raw_water"])
#     df["ph_raw_water"] = np.where(df["ph_raw_water"] > 8.6, np.nan, df["ph_raw_water"])
#     # FeCl dosages are out of bounds
#     fecl_dosage_columns = [col for col in df.columns if col.startswith("fecl3_dosage_lane_")]
#     for fecl_dosage_column in fecl_dosage_columns:
#         df[fecl_dosage_column] = np.where(df[fecl_dosage_column] == 120, np.nan, df[fecl_dosage_column])

#     return df


# def remove_outliers_per_lane(df):
#     """Remove outliers for `ftu_section` and `FeCL3`."""
#     df["ftu_section"] = np.where(round(df["ftu_section"], 2) >= 15.8, np.nan, df["ftu_section"])
#     df["ftu_section"] = np.where(df["ftu_section"] == 0.0, np.nan, df["ftu_section"])
#     ftu_section_greater_than_raw = df["ftu_section"] > df["ftu_raw_water"]
#     df["ftu_section"] = np.where(ftu_section_greater_than_raw, np.nan, df["ftu_section"])
#     df["ftu_raw_water"] = np.where(ftu_section_greater_than_raw, np.nan, df["ftu_raw_water"])
#     df["fecl3_concentration"] = np.where(round(df["fecl3_concentration"], 2) == 0, np.nan, df["fecl3_concentration"])

#     return df


# def remove_period_out_data(df, start_datetime, end_datetime, lanes_to_remove=["1", "2", "3"]):
#     """Remove period oud of data."""
#     mask = (df["date"] >= start_datetime) & (df["date"] <= end_datetime) & (df["lane"].isin(lanes_to_remove))
#     df = df[~mask]

#     return df


# def scale_data(df: pd.DataFrame, experiment_name: str):
#     """Scale the input data and separate it into training and scenario sets.

#     Args:
#     - df (pd.DataFrame): Input DataFrame with a 'date' column and relevant features.
#     - experiment_name (str): Name of the experiment.
#     - scenario_period (str): Date for scenario separation.

#     Returns:
#     - Tuple[pd.DataFrame, pd.DataFrame, np.ndarray]: Scaled training data, scenario data (x), and scenario labels (y).
#     """
#     # Set 'date' as the index
#     df = df.dropna()
#     df = df.set_index("date")

#     # Set x and y values based on the experiment
#     if experiment_name == "ftu_section":
#         feature_cols = [
#             "ftu_raw_water",
#             "temperature_raw_water",
#             "ph_raw_water",
#             "flow_coagulation",
#             "fecl3_concentration",
#             "lane",
#         ]
#         target_col = "ftu_section"
#     else:
#         feature_cols = [
#             "ftu_raw_water",
#             "temperature_raw_water",
#             "ph_raw_water",
#             "flow_coagulation",
#             "ftu_section",
#             "lane",
#         ]
#         target_col = "fecl3_concentration"

#     x = df[feature_cols]
#     y = df[target_col]

#     # Scale the training data
#     scaler = InvertableColumnTransformer(
#         [("scaler", StandardScaler(), feature_cols[:-1]), ("dummy", OneHotEncoder(drop="first"), ["lane"])],
#         verbose_feature_names_out=False,
#     )

#     scaled_x = scaler.fit_transform(x)
#     scaled_x_df = pd.DataFrame(scaled_x, columns=scaler.get_feature_names_out(), index=x.index)

#     return scaled_x_df, y, scaler


# def preprocess_data(df, experiment_name):
#     """Run pre-processing pipeline for the data frame `df`."""
#     df = (
#         df.pipe(clean_column_names)
#         .pipe(clean_outliers)
#         .pipe(calculate_fecl_concentration)
#         .pipe(reshape_dataframe)
#         .pipe(remove_outliers_per_lane)
#         .pipe(aggregate_data, period="6H")
#         # removed period because a shaft of an 'agitator' has broken
#         .pipe(remove_period_out_data, start_datetime="2024-01-26", end_datetime="2024-02-01")
#         # sludge was pumped into the basin of lane 1
#         .pipe(remove_period_out_data, start_datetime="2023-12-05", end_datetime="2023-12-07", lanes_to_remove=["1"])
#         # tag 1N615ID01FIT008 (NWG GeCl3-Dosering - Coagulatiestraat 3 Pomp 01/02) does not work well
#         .pipe(remove_period_out_data, start_datetime="2022-03-01", end_datetime="2023-02-11", lanes_to_remove=["1"])
#         .pipe(remove_period_out_data, start_datetime="2023-06-30", end_datetime="2023-12-03", lanes_to_remove=["2"])
#         # start from 02_2023
#         # .pipe(remove_period_out_data, start_datetime="2020-01-01", end_datetime="2023-01-31", lanes_to_remove=["1","2","3"])
#         .pipe(scale_data, experiment_name)
#     )

#     return df