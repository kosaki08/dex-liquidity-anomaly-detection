import bentoml


@bentoml.service(resources={"cpu": "1"}, traffic={"timeout": 60})
class SimpleService:
    def __init__(self):
        # MLflowへの依存なしで起動
        pass

    @bentoml.api
    def health(self):
        return {"status": "ok"}

    @bentoml.api
    def predict(self, input_data: list[dict]) -> list[float]:
        # ダミー予測を返す
        return [1.0] * len(input_data)
