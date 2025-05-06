import pickle

import pandas as pd
from mlflow.pyfunc import PythonModel


class RiverModelWrapper(PythonModel):
    """
    River のモデルを MLflow PyFunc 形式でラップするクラス。
    """

    def load_context(self, context) -> None:
        with open(context.artifacts["model_file"], "rb") as f:
            self.model = pickle.load(f)

    def predict(self, model_input: pd.DataFrame) -> pd.Series:
        # 各行に対して River モデルの score_one を呼ぶ
        return model_input.apply(lambda row: self.model.score_one(row.to_dict()), axis=1)
