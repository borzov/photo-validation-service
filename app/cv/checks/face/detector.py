"""
Face detection module for photo validation.
Uses multiple fallback detection methods for robustness.
"""
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import math
from pathlib import Path
import os
from packaging import version

from app.core.logging import get_logger

logger = get_logger(__name__)

# Define models directory relative to current file
SCRIPT_DIR = Path(__file__).parent.resolve()
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(SCRIPT_DIR.parent.parent.parent.parent / "models")))
logger.info(f"Looking for face detection models in: {MODELS_DIR}")

# Auto-download lbfmodel.yaml
lbfmodel_path = os.path.join(MODELS_DIR, "lbfmodel.yaml")
if not os.path.exists(lbfmodel_path):
    try:
        import urllib.request
        os.makedirs(MODELS_DIR, exist_ok=True)
        logger.info(f"Downloading LBF facemark model to {lbfmodel_path}")
        url = "https://github.com/kurnianggoro/GSOC2017/raw/master/data/lbfmodel.yaml"
        urllib.request.urlretrieve(url, lbfmodel_path)
    except Exception as e:
        logger.warning(f"Failed to download LBF model: {e}")

# Auto-download YuNet ONNX
yunet_path = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
if not os.path.exists(yunet_path):
    try:
        import urllib.request
        os.makedirs(MODELS_DIR, exist_ok=True)
        logger.info(f"Downloading YuNet ONNX model to {yunet_path}")
        url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
        urllib.request.urlretrieve(url, yunet_path)
    except Exception as e:
        logger.warning(f"Failed to download YuNet model: {e}")

# Initialize face detector (YuNet with Haar Cascade fallback)
face_detector_path = str(MODELS_DIR / "face_detection_yunet_2023mar.onnx")
face_detector = None

try:
    if Path(face_detector_path).is_file():
        face_detector = cv2.FaceDetectorYN.create(
            face_detector_path,
            "",
            (120, 120),  # Minimum input size - smaller for better detection
            0.4,         # Confidence threshold - lower for better detection
            0.3,         # NMS threshold
            100          # Max faces - reduced to avoid memory issues
        )
        logger.info("YuNet face detector loaded successfully.")
    else:
        raise FileNotFoundError(f"YuNet model not found: {face_detector_path}")
except Exception as e:
    logger.warning(f"Failed to load YuNet face detector: {e}. Using Haar cascade fallback.")
    try:
        haar_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if Path(haar_path).is_file():
            face_detector = cv2.CascadeClassifier(haar_path)
            logger.info("Using Haar cascade as face detector.")
        else:
            raise FileNotFoundError("Haar cascade file not found")
    except Exception as haar_e:
        logger.error(f"Failed to load Haar cascade: {haar_e}. Face detection disabled.")
        face_detector = None

# Initialize facial landmark detector (OpenCV Facemark LBF)
facemark_path = str(MODELS_DIR / "lbfmodel.yaml")
facemark = None

try:
    logger.info(f"OpenCV version: {cv2.__version__}")
    if version.parse(cv2.__version__) >= version.parse("4.5.0"):
        if Path(facemark_path).is_file():
            logger.info(f"Creating FacemarkLBF instance...")
            facemark = cv2.face.createFacemarkLBF()
            logger.info(f"Loading model from {facemark_path}...")
            facemark.loadModel(facemark_path)
            logger.info("LBF Facemark model loaded successfully.")
        else:
            logger.warning(f"Facemark model not found: {facemark_path}")
    else:
        logger.warning("OpenCV version < 4.5.0, landmark detection disabled.")
except Exception as e:
    logger.warning(f"Failed to load Facemark model: {e}. Landmark detection disabled.")
    facemark = None

# Initialize glasses detector (Haar Cascade)
glasses_cascade_path = cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml'
glasses_cascade = None
try:
    if Path(glasses_cascade_path).is_file():
        glasses_cascade = cv2.CascadeClassifier(glasses_cascade_path)
        logger.info("Glasses Haar cascade loaded successfully.")
    else:
        logger.warning("Glasses Haar cascade file not found.")
except Exception as e:
    logger.warning(f"Failed to load glasses cascade: {e}")

# Initialize HOG person detector
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
logger.info("HOG person detector initialized.")


def detect_faces_yunet(image: np.ndarray, confidence_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Face detection using YuNet detector.
    """
    if not isinstance(face_detector, cv2.FaceDetectorYN):
        return []
        
    try:
        h, w = image.shape[:2]
        face_detector.setInputSize((w, h))
        _, faces_yunet = face_detector.detect(image)
        
        faces_data = []
        if faces_yunet is not None and len(faces_yunet) > 0:
            for face_info in faces_yunet:
                confidence = float(face_info[-1])
                if confidence > confidence_threshold:
                    bbox = tuple(map(int, face_info[0:4]))
                    faces_data.append({
                        "bbox": bbox,
                        "landmarks": None,
                        "confidence": confidence
                    })
        
        logger.debug(f"YuNet detector found {len(faces_data)} faces.")
        return faces_data
    
    except Exception as e:
        logger.warning(f"YuNet detection failed: {e}")
        return []


def detect_faces_haar(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Face detection using Haar Cascade classifier.
    """
    if not isinstance(face_detector, cv2.CascadeClassifier):
        return []
        
    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        # Улучшенные настройки для лучшей детекции лиц
        faces_haar = face_detector.detectMultiScale(
            gray, 
            scaleFactor=1.05,    # Меньший шаг масштабирования для лучшей точности
            minNeighbors=3,      # Меньше соседей для менее строгой фильтрации
            minSize=(30, 30),    # Меньший минимальный размер
            maxSize=(500, 500),  # Максимальный размер для избежания ложных срабатываний
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        faces_data = []
        for face_rect in faces_haar:
            faces_data.append({
                "bbox": tuple(face_rect),
                "landmarks": None,
                "confidence": 0.9  # Default confidence for Haar
            })
        
        logger.debug(f"Haar detector found {len(faces_data)} faces.")
        return faces_data
    
    except Exception as e:
        logger.warning(f"Haar detection failed: {e}")
        return []


def detect_faces_multiscale(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Multi-scale face detection for large faces.
    """
    h, w = image.shape[:2]
    faces_data = []
    
    # Try different scales
    scales = [0.8, 0.6, 1.5, 2.0]
    for scale in scales:
        scaled_w, scaled_h = int(w * scale), int(h * scale)
        if min(scaled_w, scaled_h) < 32:
            continue
            
        try:
            scaled_img = cv2.resize(image, (scaled_w, scaled_h))
            
            if isinstance(face_detector, cv2.FaceDetectorYN):
                face_detector.setInputSize((scaled_w, scaled_h))
                _, faces_yunet = face_detector.detect(scaled_img)
                
                if faces_yunet is not None and len(faces_yunet) > 0:
                    for face_info in faces_yunet:
                        confidence = float(face_info[-1])
                        if confidence > 0.4:
                            x, y, w_face, h_face = face_info[0:4]
                            # Scale back to original size
                            x, y, w_face, h_face = int(x/scale), int(y/scale), int(w_face/scale), int(h_face/scale)
                            faces_data.append({
                                "bbox": (x, y, w_face, h_face),
                                "landmarks": None,
                                "confidence": confidence
                            })
                    if faces_data:
                        break
        except Exception as e:
            logger.debug(f"Multiscale detection failed at scale {scale}: {e}")
            continue
    
    return faces_data


def detect_skin_regions(image: np.ndarray) -> np.ndarray:
    """
    Detect skin regions using HSV color space.
    """
    try:
        # Convert to HSV color space
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # Define skin color range in HSV
        lower_skin = np.array([0, 20, 70], dtype=np.uint8)
        upper_skin = np.array([20, 255, 255], dtype=np.uint8)
        
        # Create skin mask
        skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
        
        # Apply morphological operations to clean the mask
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
        skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
        
        # Apply Gaussian blur to smooth the mask
        skin_mask = cv2.GaussianBlur(skin_mask, (3, 3), 0)
        
        return skin_mask
    
    except Exception as e:
        logger.warning(f"Skin detection failed: {e}")
        return np.zeros(image.shape[:2], dtype=np.uint8)


def emergency_face_detection(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Emergency heuristic face detection based on skin regions.
    """
    try:
        h, w = image.shape[:2]
        skin_mask = detect_skin_regions(image)
        
        # Find contours in skin mask
        contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contours:
            return []
        
        # Find largest contour
        max_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(max_contour)
        
        # Check if contour is large enough (min 5% of image area)
        if area > 0.05 * w * h:
            x, y, w_rect, h_rect = cv2.boundingRect(max_contour)
            
            # Check aspect ratio (faces are usually taller than wide)
            aspect_ratio = w_rect / h_rect
            if 0.5 <= aspect_ratio <= 1.2:
                return [{
                    "bbox": (x, y, w_rect, h_rect),
                    "landmarks": None,
                    "confidence": 0.7  # Estimated confidence
                }]
        
        return []
    
    except Exception as e:
        logger.warning(f"Emergency face detection failed: {e}")
        return []


def detect_faces(image: np.ndarray, confidence_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Comprehensive multi-level face detection strategy.
    Uses multiple fallback methods for robustness.
    """
    if face_detector is None:
        logger.error("Детектор лиц недоступен. Пропуск обнаружения лиц.")
        return []

    h, w = image.shape[:2]
    faces_data = []
    
    try:
        # Method 1: Standard YuNet/Haar detection
        if isinstance(face_detector, cv2.FaceDetectorYN):
            try:
                faces_data = detect_faces_yunet(image, confidence_threshold)
            except Exception as yunet_error:
                logger.warning(f"YuNet failed, trying Haar fallback: {yunet_error}")
                # Если YuNet падает, пробуем через Haar каскад напрямую
                try:
                    haar_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                    if Path(haar_path).is_file():
                        haar_cascade = cv2.CascadeClassifier(haar_path)
                        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                        faces_haar = haar_cascade.detectMultiScale(
                            gray, 
                            scaleFactor=1.05,
                            minNeighbors=3, 
                            minSize=(30, 30),
                            maxSize=(500, 500),
                            flags=cv2.CASCADE_SCALE_IMAGE
                        )
                        faces_data = []
                        for face_rect in faces_haar:
                            faces_data.append({
                                "bbox": tuple(face_rect),
                                "landmarks": None,
                                "confidence": 0.8
                            })
                        logger.debug(f"Haar fallback found {len(faces_data)} faces.")
                except Exception as haar_error:
                    logger.warning(f"Haar fallback also failed: {haar_error}")
        elif isinstance(face_detector, cv2.CascadeClassifier):
            faces_data = detect_faces_haar(image)
        
        # Method 2: Multi-scale detection if no faces found (временно отключено из-за ложных срабатываний)
        # if not faces_data:
        #     faces_data = detect_faces_multiscale(image)
        
        # Method 3: Emergency detection using skin regions (временно отключено из-за ложных срабатываний)
        # if not faces_data:
        #     faces_data = emergency_face_detection(image)
        
        # Detect facial landmarks if facemark is available
        if facemark is not None and faces_data:
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                face_rects = [face["bbox"] for face in faces_data]
                np_faces = np.array(face_rects, dtype=np.int32)
                
                ok, landmarks_fit = facemark.fit(gray, np_faces)
                if ok:
                    landmarks_list = [
                        [tuple(map(int, point)) for point in lm[0]] for lm in landmarks_fit
                    ]
                    
                    # Update face data with landmarks
                    for i in range(min(len(faces_data), len(landmarks_list))):
                        faces_data[i]["landmarks"] = landmarks_list[i]
            except Exception as e:
                logger.warning(f"Landmark detection failed: {e}")
        
        logger.info(f"Обнаружено {len(faces_data)} лиц.")
        return faces_data
    
    except Exception as e:
        logger.error(f"Обнаружение лиц полностью не удалось: {e}")
        return []


def estimate_pose(image_shape: Tuple[int, int], landmarks: List[Tuple[int, int]]) -> Dict[str, float]:
    """
    Estimate face pose angles (yaw, pitch, roll) from facial landmarks.
    Uses solvePnP method.
    """
    try:
        h, w = image_shape
        focal_length = w  # Approximate value
        center = (w / 2, h / 2)
        camera_matrix = np.array(
            [[focal_length, 0, center[0]],
             [0, focal_length, center[1]],
             [0, 0, 1]], dtype="double"
        )
        dist_coeffs = np.zeros((4, 1))  # No distortion

        # 3D model points for key facial features
        model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip (30)
            (0.0, -330.0, -65.0),        # Chin (8)
            (-225.0, 170.0, -135.0),     # Left eye corner (36)
            (225.0, 170.0, -135.0),      # Right eye corner (45)
            (-150.0, -150.0, -125.0),    # Left mouth corner (48)
            (150.0, -150.0, -125.0)     # Right mouth corner (54)
        ])

        # Check if required landmark indices exist
        required_indices = [30, 8, 36, 45, 48, 54]
        if any(idx >= len(landmarks) for idx in required_indices):
            logger.warning("Insufficient landmarks for pose estimation.")
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        # 2D image points corresponding to 3D model
        image_points = np.array([
            landmarks[30],  # Nose
            landmarks[8],   # Chin
            landmarks[36],  # Left eye corner
            landmarks[45],  # Right eye corner
            landmarks[48],  # Left mouth corner
            landmarks[54]   # Right mouth corner
        ], dtype="double")

        # Solve PnP
        (success, rotation_vector, translation_vector) = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs, 
            flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
            logger.warning("solvePnP failed to estimate pose")
            return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        # Get rotation matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

        # Calculate Euler angles (ZYX order)
        pitch = math.degrees(math.atan2(-rotation_matrix[2, 0], 
                                      math.sqrt(rotation_matrix[2, 1]**2 + rotation_matrix[2, 2]**2)))
        yaw = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
        roll = math.degrees(math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))

        # Normalize angles to [-180, 180] range
        if abs(pitch) > 90:
            pitch = 180 - abs(pitch) if pitch > 0 else -(180 - abs(pitch))

        yaw = (yaw + 180) % 360 - 180
        pitch = (pitch + 180) % 360 - 180
        roll = (roll + 180) % 360 - 180

        return {"yaw": yaw, "pitch": pitch, "roll": roll}

    except Exception as e:
        logger.error(f"Error in pose estimation: {e}")
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}