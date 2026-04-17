"""Config file to declare globals that will be used in multiple modules."""

# Paths
CONFIG_YAML = "src/config.yaml"  # Path to configuration yaml file to use.
DATA_FILE_PATH = "../coagulation_data_2020-01-01_2024-10-01.csv"
MLFLOW_TRACKING_URI = "http://dlabprd_mlflow_dwnwgcoagulation.privatelink.azureci.io:5000/"

# Mlflow model parameters
MLFLOW_NAME = "coagulation"
MODEL_ALIAS = "0_0_8"

# Variables to write to PIMS
SETPOINT_TAGS = {"1": "1N615CG01XS001_DLab_SPI", "2": "1N615CG01XS002_DLab_SPI", "3": "1N615CG01XS003_DLab_SPI"}
ESTIMATION_TAGS = {"1": "1N615KM01QIT006_estim", "2": "1N615KM01QIT005_estim", "3": "1N615KM01QIT004_estim"}

# Choosing setpoint parameters
STEP_SIZE = 0.1  # How many steps between minimum and maximum the algorithm should take
MINIMUM_SP = 1.5  # Minimum fecl3 concentration that the algorithm can set as setpoint
MAXIMUM_SP = 6.5  # Maximum fecl3 concentration that the algorithm can set as setpoint
TARGET_FTU = 6.0  # The target value for ftu where the chosen fecl3 concentration
# should result in a ftu below this threshold.

# Input data parameters
AGGREGATION_PERIOD_TRAIN = {"hours": 2}  # Period the data should be aggregated over
AGGREGATION_PERIOD_PRD = {"hours": 2}  # Period the data should be aggregated over

INPUT_COLUMNS = [
    "ftu_raw_water",
    "fecl3_concentration",
    "temperature_raw_water",
    "ph_raw_water",
    "after_dredging",
    "lane",
    "year",
]  # List of names of the input columns.
TARGET_COLUMN = "ftu_section"  # Name of the target column

# Scenario parameters
SCENARIO_START_DATE = "2024-01-01"  # Start date for scenario period
SCENARIO_END_DATE = "2024-01-31"  # End date for scenario period
SCENARIO_LANE = "1"  # For which lane the scenario is predicted/plotted

LAST_DREDGING_DATE = {"1": "2024-07-15 08:30:00+0000", "2": "2023-06-19 09:45:00+0000", "3": "2023-06-08 06:30:00+0000"}
