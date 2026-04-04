import sagemaker
from sagemaker.model import Model

role = "YOUR_SAGEMAKER_ROLE"
image_uri = "ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/anomaly-model"

model = Model(
    image_uri=image_uri,
    role=role
)

predictor = model.deploy(
    initial_instance_count=1,
    instance_type="ml.m5.large"
)

print("Endpoint:", predictor.endpoint_name)
