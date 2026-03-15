import os
import uuid
from typing import Any

import pandas as pd
from django.utils.text import slugify

PATH_DATA ='data/'



# ─── Utilitaires purs ────────────────────────────────────────────────────────
def product_image_path(instance, filename):
    """
    Génère un chemin propre : products/<product_id>/<slug_filename>
    Ex: products/abc123/photo-1.jpg
    """
    ext      = filename.split(".")[-1].lower()
    basename = slugify(os.path.splitext(filename)[0])
    return f"products/{instance.product.product_id}/{basename}.{ext}"

def normalize_uuid(value: Any) -> uuid.UUID | None:
    if value is None:
        return None
    try:
        return uuid.UUID(str(value).strip())
    except (ValueError, AttributeError):
        return None


def to_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    s = str(value).strip()
    return default if s.lower() == "nan" else s


def to_int(value: Any) -> int | None:
    try:
        v = float(value)
        return None if pd.isna(v) else int(v)
    except (TypeError, ValueError):
        return None


def parse_dt(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        ts = pd.to_datetime(value, utc=True)
        return ts.to_pydatetime() if not pd.isna(ts) else None
    except Exception:
        return None


def read_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    df.columns = df.columns.str.strip()
    df = df.fillna("")
    return df
