import pandas as pd

PATH_DATA ='data/'


def parse_datetime_column(df, column, tz="UTC"):
    df[column] = pd.to_datetime(df[column], errors="coerce")
    df[column] = df[column].dt.tz_localize(tz)
    return df
