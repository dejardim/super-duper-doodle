#!/usr/bin/env python3
import os

from aws_cdk import App, Stack
from constructs import Construct

from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction


class APILambdaStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, f"{id}", **kwargs)

        PythonFunction(
            self, f"AliveAPI",
            entry=os.path.join(os.path.dirname(__file__), "src"),
            runtime=Runtime.PYTHON_3_12,
            index='main.py',
            function_name=f"AliveAPI"
        )


app = App()
APILambdaStack(app, "AliveAPI")

app.synth()
