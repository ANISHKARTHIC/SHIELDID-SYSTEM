import logging
import os
import cv2
import numpy as np
from typing import Dict, Any
from numpy.linalg import norm
from app.services.providers.base_providers import BaseFaceRecognition

logger = logging.getLogger("insightface_provider")

# Defaults to the host's ~/.insightface cache (InsightFace's own default) for
# local dev; the Docker image sets this to a baked-in in-image path so
# weights don't re-download on every container start.
MODEL_CACHE_ROOT = os.getenv("INSIGHTFACE_MODEL_ROOT", os.path.expanduser("~/.insightface"))

# buffalo_l (~600MB, higher accuracy) is the right default on a real
# instance (t3.medium+). buffalo_s (~160MB, still real RetinaFace+ArcFace
# inference, lower accuracy) is what fits alongside EasyOCR+torch in the
# ~1GB a t3.micro free-tier demo actually has. Same for det_size: 640x640
# is InsightFace's own default and costs more peak memory/compute per
# inference than a demo needs — 320x320 is still enough to detect one
# reasonably-framed face in a phone-camera ID photo.
INSIGHTFACE_MODEL_PACK = os.getenv("INSIGHTFACE_MODEL_PACK", "buffalo_l")
INSIGHTFACE_DET_SIZE = int(os.getenv("INSIGHTFACE_DET_SIZE", "640"))

# Below this RetinaFace detection confidence, a "face" is more likely a
# false-positive (a face-shaped blob in glare/moiré/background clutter)
# than a real one — embedding it anyway silently produces a garbage
# 512D vector that won't cosine-match the same real person, surfacing
# downstream only as an unexplained "face mismatch" / CHECK decision.
MIN_FACE_DET_SCORE = float(os.getenv("INSIGHTFACE_MIN_DET_SCORE", "0.55"))

# Below this fraction of the image's shorter side, a detected face is too
# small to yield a reliable ArcFace embedding (common when the crop step
# upstream failed and the real face occupies a small corner of a much
# larger scene) — reject rather than embed a low-fidelity crop.
MIN_FACE_SIZE_RATIO = float(os.getenv("INSIGHTFACE_MIN_FACE_SIZE_RATIO", "0.08"))


def select_best_face(faces, img_shape):
    """
    Picks the highest-quality detected face — by detection confidence,
    tie-broken by bbox area — instead of blindly trusting `faces[0]`
    (RetinaFace's own default ordering, which is a reasonable but not
    guaranteed proxy for "the real subject's face"). Returns None if no
    face clears the confidence/size bar, so callers can fail with a clear
    "retake" message instead of comparing against a garbage embedding.
    """
    if not faces:
        return None

    h, w = img_shape[:2]
    min_dim = min(h, w)

    def bbox_area(face):
        x1, y1, x2, y2 = face.bbox
        return max(0.0, x2 - x1) * max(0.0, y2 - y1)

    candidates = []
    for face in faces:
        det_score = float(getattr(face, "det_score", 0.0) or 0.0)
        if det_score < MIN_FACE_DET_SCORE:
            continue
        x1, y1, x2, y2 = face.bbox
        face_size = min(x2 - x1, y2 - y1)
        if min_dim <= 0 or face_size < MIN_FACE_SIZE_RATIO * min_dim:
            continue
        candidates.append(face)

    if not candidates:
        return None

    candidates.sort(key=lambda f: (float(f.det_score), bbox_area(f)), reverse=True)
    return candidates[0]


class InsightFaceProvider(BaseFaceRecognition):
    def __init__(self):
        self.app = None

    def load_model(self) -> None:
        """Loads InsightFace (RetinaFace + ArcFace) into memory."""
        try:
            from insightface.app import FaceAnalysis
            # Support GPU execution falling back to CPU
            self.app = FaceAnalysis(
                name=INSIGHTFACE_MODEL_PACK,
                root=MODEL_CACHE_ROOT,
                providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
            )
            # ctx_id=0 for GPU. If CUDA is missing, providers list will safely fallback to CPU.
            self.app.prepare(ctx_id=0, det_size=(INSIGHTFACE_DET_SIZE, INSIGHTFACE_DET_SIZE))
            logger.info(
                f"InsightFace model loaded successfully "
                f"(pack={INSIGHTFACE_MODEL_PACK}, det_size={INSIGHTFACE_DET_SIZE})."
            )
        except ImportError:
            logger.error("insightface module not installed. Run `pip install insightface onnxruntime`")
            raise
        except Exception as e:
            logger.error(f"Failed to load InsightFace model: {e}")
            raise

    def extract_embedding(self, image_path: str) -> np.ndarray:
        if not self.app:
            self.load_model()
            
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not read image from {image_path}")
            
        faces = self.app.get(img)
        if len(faces) == 0:
            raise ValueError("No face detected in the image.")

        best = select_best_face(faces, img.shape)
        if best is None:
            raise ValueError(
                "Face was not clear enough to verify. Please retake the photo "
                "with better lighting and the face closer to the camera."
            )

        return best.embedding
        
    def compare(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute Cosine Similarity between two 512D embeddings.
        Result is between -1.0 and 1.0. We normalize it to 0.0 - 1.0.
        """
        if embedding1 is None or embedding2 is None:
            return 0.0
            
        sim = np.dot(embedding1, embedding2) / (norm(embedding1) * norm(embedding2))
        # Convert from [-1, 1] to [0, 1] for easier thresholding
        normalized_sim = (sim + 1.0) / 2.0
        return float(normalized_sim)
