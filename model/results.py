import pandas as pd


class OptimisationResults:
    def __init__(self, time_series_result_df: pd.DataFrame, order_result_df: pd.DataFrame) -> None:
        self.sequence_df = time_series_result_df
        self.order_result_df = order_result_df

    # @staticmethod
    # def combine(results: list["OptimisationResults"]) -> "OptimisationResults":
    #     pass
