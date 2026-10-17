from fastapi import APIRouter

from app.core.config import get_settings
from app.models.schemas import MLFileRequest, MLPredictRequest, MLTrainRequest
from app.services.ml import toolkit
from app.utils.files import resolve_data_file

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("/datasets")
def datasets():
    return [{"name": p.name} for p in sorted(get_settings().uploads_dir.glob("*.csv"))]


@router.post("/profile")
def profile(req: MLFileRequest):
    return toolkit.profile_dataframe(toolkit.load_csv(resolve_data_file(req.filename)))


@router.post("/train")
def train(req: MLTrainRequest):
    df = toolkit.load_csv(resolve_data_file(req.filename))
    return toolkit.train_model(
        df, req.target, task=req.task, algorithm=req.algorithm, test_size=req.test_size,
        model_name=req.model_name, drop_columns=req.drop_columns,
    )


@router.get("/models")
def models():
    return toolkit.list_models()


@router.post("/predict")
def predict(req: MLPredictRequest):
    return toolkit.predict(req.model_name, req.records)
