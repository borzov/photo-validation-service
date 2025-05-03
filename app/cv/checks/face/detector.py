"""
Модуль детекции лиц на фотографиях.
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

# --- Определяем путь к директории с моделями относительно текущего файла ---
SCRIPT_DIR = Path(__file__).parent.resolve()
MODELS_DIR = Path(os.getenv("MODELS_DIR", str(SCRIPT_DIR.parent.parent.parent.parent / "models")))
logger.info(f"Looking for face detection models in: {MODELS_DIR}")

# --- Автоматическая загрузка lbfmodel.yaml ---
lbfmodel_path = os.path.join(MODELS_DIR, "lbfmodel.yaml")
if not os.path.exists(lbfmodel_path):
    import urllib.request
    logger.info(f"Downloading LBF facemark model to {lbfmodel_path}")
    url = "https://github.com/kurnianggoro/GSOC2017/raw/master/data/lbfmodel.yaml"
    urllib.request.urlretrieve(url, lbfmodel_path)

# --- Автоматическая загрузка YuNet ONNX ---
yunet_path = os.path.join(MODELS_DIR, "face_detection_yunet_2023mar.onnx")
if not os.path.exists(yunet_path):
    import urllib.request
    logger.info(f"Downloading YuNet ONNX model to {yunet_path}")
    url = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    urllib.request.urlretrieve(url, yunet_path)

# --- Инициализация моделей ---

# Модель для детекции лиц (OpenCV DNN - YuNet)
face_detector_path = str(MODELS_DIR / "face_detection_yunet_2023mar.onnx")
try:
    # Проверяем существование файла перед загрузкой
    if not Path(face_detector_path).is_file():
        raise FileNotFoundError(f"Model file not found: {face_detector_path}")
    # Инициализируем с правильными параметрами
    face_detector = cv2.FaceDetectorYN.create(
        face_detector_path,
        "",
        (320, 320),  # Минимальный размер входного изображения
        0.6,         # Порог уверенности
        0.3,         # Порог NMS
        5000         # Максимальное количество лиц
    )
    logger.info("YuNet face detector loaded successfully.")
except Exception as e:
    logger.error(f"Failed to load YuNet face detector from {face_detector_path}: {e}. Using Haar cascade as fallback.")
    # Fallback на Haar Cascade
    haar_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    if Path(haar_path).is_file():
        face_detector = cv2.CascadeClassifier(haar_path)
        logger.info("Using Haar cascade as fallback face detector.")
    else:
        face_detector = None
        logger.error("Fallback Haar cascade file not found. Face detection disabled.")

# Инициализация DNN детектора лиц
dnn_face_detector = None
try:
    # Проверяем наличие файлов модели
    model_path = os.path.join(MODELS_DIR, "dnn", "deploy.prototxt")
    weights_path = os.path.join(MODELS_DIR, "dnn", "res10_300x300_ssd_iter_140000.caffemodel")
    
    # Создаем директорию для DNN моделей, если не существует
    os.makedirs(os.path.join(MODELS_DIR, "dnn"), exist_ok=True)
    
    # Проверяем наличие файлов или загружаем их
    if not os.path.exists(model_path):
        import urllib.request
        logger.info(f"Downloading DNN model prototxt to {model_path}")
        url = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
        urllib.request.urlretrieve(url, model_path)
    
    if not os.path.exists(weights_path):
        import urllib.request
        logger.info(f"Downloading DNN model weights to {weights_path}")
        url = "https://raw.githubusercontent.com/opencv/opencv_3rdparty/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"
        urllib.request.urlretrieve(url, weights_path)
    
    # Загружаем модель
    if os.path.exists(model_path) and os.path.exists(weights_path):
        dnn_face_detector = cv2.dnn.readNetFromCaffe(model_path, weights_path)
        logger.info("DNN face detector loaded successfully")
    else:
        logger.warning("DNN model files not found or couldn't be downloaded")
except Exception as e:
    logger.error(f"Failed to initialize DNN face detector: {e}")
    dnn_face_detector = None

# Модель для определения лицевых точек (OpenCV Facemark LBF)
facemark_path = str(MODELS_DIR / "lbfmodel.yaml")
facemark = None

try:
    # Проверяем версию OpenCV
    logger.info(f"OpenCV version: {cv2.__version__}")
    if version.parse(cv2.__version__) >= version.parse("4.5.0"):
        # Проверяем существование файла перед загрузкой
        if not Path(facemark_path).is_file():
            raise FileNotFoundError(f"Model file not found: {facemark_path}")
        logger.info(f"Creating FacemarkLBF instance...")
        facemark = cv2.face.createFacemarkLBF()
        logger.info(f"Loading model from {facemark_path}...")
        facemark.loadModel(facemark_path)
        logger.info("LBF Facemark model loaded successfully.")
    else:
        logger.warning("OpenCV version < 4.5.0, landmark detection will be disabled.")
except Exception as e:
    logger.error(f"Failed to load Facemark model from {facemark_path}: {e}. Landmark detection will be disabled.", exc_info=True)
    facemark = None # Убедимся, что он None в случае ошибки

# Модель для детекции очков (Haar Cascade)
glasses_cascade_path = cv2.data.haarcascades + 'haarcascade_eye_tree_eyeglasses.xml'
glasses_cascade = None
if Path(glasses_cascade_path).is_file():
    glasses_cascade = cv2.CascadeClassifier(glasses_cascade_path)
    logger.info("Glasses Haar cascade loaded successfully.")
else:
    logger.error("Glasses Haar cascade file not found. Glasses detection might be affected.")

# HOG детектор для людей
hog = cv2.HOGDescriptor()
hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
logger.info("HOG person detector initialized.")


def detect_faces_with_dnn(image: np.ndarray, confidence_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Детекция лиц с использованием DNN.
    """
    if dnn_face_detector is None:
        logger.warning("DNN face detector not available.")
        return []
        
    h, w = image.shape[:2]
    faces_data = []
    
    # Создаем blob из изображения
    blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 1.0,
                                (300, 300), (104.0, 177.0, 123.0))
    
    # Прогоняем через сеть
    dnn_face_detector.setInput(blob)
    detections = dnn_face_detector.forward()
    
    # Обрабатываем результаты
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        
        if confidence > confidence_threshold:
            # Координаты обнаруженного лица (нормализованы от 0 до 1)
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            
            # Убедимся, что координаты находятся в пределах изображения
            startX = max(0, startX)
            startY = max(0, startY)
            endX = min(w, endX)
            endY = min(h, endY)
            
            # Преобразуем в формат (x, y, width, height)
            x, y = startX, startY
            width, height = endX - startX, endY - startY
            
            # Проверяем, что размеры корректны
            if width > 0 and height > 0:
                faces_data.append({
                    "bbox": (x, y, width, height),
                    "landmarks": None,  # DNN не предоставляет лицевые точки
                    "confidence": float(confidence)
                })
    
    logger.info(f"DNN detector found {len(faces_data)} faces.")
    return faces_data


def detect_large_face(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Специализированный метод для обнаружения очень крупных лиц в кадре.
    Использует подход с масштабированием изображения вниз.
    """
    h, w = image.shape[:2]
    faces_data = []
    
    # Создаем серию уменьшенных изображений
    scale_factors = [0.8, 0.7, 0.6, 0.5, 0.4]
    
    for scale in scale_factors:
        # Масштабируем изображение вниз
        scaled_w, scaled_h = int(w * scale), int(h * scale)
        scaled_img = cv2.resize(image, (scaled_w, scaled_h))
        
        # Пробуем обнаружить лицо на уменьшенном изображении
        if isinstance(face_detector, cv2.FaceDetectorYN):
            face_detector.setInputSize((scaled_w, scaled_h))
            _, faces_yunet = face_detector.detect(scaled_img)
            
            if faces_yunet is not None and len(faces_yunet) > 0:
                # Масштабируем результаты обратно
                for face_info in faces_yunet:
                    confidence = float(face_info[-1])
                    if confidence > 0.4:  # Пониженный порог
                        x, y, w_face, h_face = face_info[0:4]
                        # Масштабируем обратно к исходному размеру
                        x, y, w_face, h_face = int(x/scale), int(y/scale), int(w_face/scale), int(h_face/scale)
                        
                        faces_data.append({
                            "bbox": (x, y, w_face, h_face),
                            "landmarks": None,
                            "confidence": confidence
                        })
        
        # Если нашли лица, прекращаем поиск
        if faces_data:
            break
    
    return faces_data


def detect_faces_by_quadrants(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Разделяет изображение на квадранты и ищет лица в каждом.
    Полезно когда лицо занимает большую часть изображения.
    """
    h, w = image.shape[:2]
    faces_data = []
    
    # Определяем квадранты с перекрытием
    quadrants = [
        # Левый верхний
        (0, 0, w//2 + w//4, h//2 + h//4),
        # Правый верхний
        (w//4, 0, w, h//2 + h//4),
        # Левый нижний
        (0, h//4, w//2 + w//4, h),
        # Правый нижний
        (w//4, h//4, w, h),
        # Центральный (с запасом)
        (w//6, h//6, 5*w//6, 5*h//6)
    ]
    
    for quad in quadrants:
        x1, y1, x2, y2 = quad
        # Вырезаем квадрант
        quad_img = image[y1:y2, x1:x2]
        
        if quad_img.size == 0:  # Пропускаем пустые квадранты
            continue
        
        # Ищем лица в квадранте
        if isinstance(face_detector, cv2.FaceDetectorYN):
            quad_h, quad_w = quad_img.shape[:2]
            face_detector.setInputSize((quad_w, quad_h))
            _, faces_yunet = face_detector.detect(quad_img)
            
            if faces_yunet is not None and len(faces_yunet) > 0:
                for face_info in faces_yunet:
                    confidence = float(face_info[-1])
                    if confidence > 0.4:  # Пониженный порог
                        # Получаем координаты относительно квадранта
                        fx, fy, fw, fh = face_info[0:4]
                        # Корректируем координаты к исходному изображению
                        fx, fy = int(fx + x1), int(fy + y1)
                        
                        # Проверяем что лицо не выходит за границы изображения
                        fx = max(0, fx)
                        fy = max(0, fy)
                        fw = min(fw, w - fx)
                        fh = min(fh, h - fy)
                        
                        if fw > 0 and fh > 0:
                            faces_data.append({
                                "bbox": (fx, fy, int(fw), int(fh)),
                                "landmarks": None,
                                "confidence": confidence
                            })
    
    return faces_data


def detect_skin_regions(image: np.ndarray) -> np.ndarray:
    """
    Создает маску областей кожи для улучшения детекции лиц.
    """
    # Конвертируем в YCrCb цветовое пространство
    ycrcb = cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    
    # Определяем диапазоны цвета кожи в YCrCb
    min_YCrCb = np.array([0, 135, 85], np.uint8)
    max_YCrCb = np.array([255, 180, 135], np.uint8)
    
    # Создаем маску кожи
    skin_mask = cv2.inRange(ycrcb, min_YCrCb, max_YCrCb)
    
    # Применяем морфологические операции для улучшения маски
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_OPEN, kernel)
    skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)
    
    # Находим самую большую область (предположительно лицо)
    contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return skin_mask
    
    # Находим контур с максимальной площадью
    max_contour = max(contours, key=cv2.contourArea)
    
    # Создаем пустую маску
    face_region_mask = np.zeros_like(skin_mask)
    
    # Заполняем контур на маске
    cv2.drawContours(face_region_mask, [max_contour], 0, 255, -1)
    
    return face_region_mask


def emergency_face_detection(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Последний рубеж защиты - эвристический подход, когда все остальные методы не сработали.
    Особенно полезно для идеальных портретных изображений, где лицо занимает большую часть кадра.
    """
    h, w = image.shape[:2]
    
    # Для портретных изображений с лицом в центре,
    # часто хорошим приближением будет считать центральную область лицом
    center_x, center_y = w // 2, h // 2
    
    # Для лица, которое занимает большую часть изображения
    face_width = int(w * 0.7)  # Примерно 70% ширины
    face_height = int(h * 0.7)  # Примерно 70% высоты
    
    # Центрируем bbox
    x = center_x - face_width // 2
    y = center_y - face_height // 2
    
    # Убедимся, что bbox лежит внутри изображения
    x = max(0, x)
    y = max(0, y)
    face_width = min(face_width, w - x)
    face_height = min(face_height, h - y)
    
    # Создаем результат с низким confidence
    face = {
        "bbox": (x, y, face_width, face_height),
        "landmarks": None,
        "confidence": 0.6  # Низкая уверенность, т.к. это эвристика
    }
    
    logger.warning("Using emergency face detection as last resort!")
    return [face]


def detect_faces(image: np.ndarray) -> List[Dict[str, Any]]:
    """
    Комплексная многоуровневая стратегия детекции лиц,
    учитывающая различные сценарии, включая крупные лица.
    """
    if face_detector is None:
        logger.error("Face detector not available. Skipping face detection.")
        return []

    h, w = image.shape[:2]
    faces_data = []
    
    # 1. ПОПЫТКА: Стандартная детекция YuNet
    if isinstance(face_detector, cv2.FaceDetectorYN):
        face_detector.setInputSize((w, h))
        _, faces_yunet = face_detector.detect(image)
        
        if faces_yunet is not None and len(faces_yunet) > 0:
            for face_info in faces_yunet:
                confidence = float(face_info[-1])
                if confidence > 0.4:  # Порог из настроек
                    bbox = tuple(map(int, face_info[0:4]))
                    faces_data.append({
                        "bbox": bbox,
                        "landmarks": None,
                        "confidence": confidence
                    })
    elif isinstance(face_detector, cv2.CascadeClassifier):
        # Используем Haar как fallback
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        faces_haar = face_detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))
        for face_rect in faces_haar:
            faces_data.append({
                "bbox": tuple(face_rect),
                "landmarks": None,
                "confidence": 0.9  # Условная уверенность для Haar
            })
    
    # 2. ПОПЫТКА: Если лица не обнаружены, пробуем с разными масштабами
    if not faces_data:
        scales = [0.8, 0.6, 1.5, 2.0]
        for scale in scales:
            scaled_w, scaled_h = int(w * scale), int(h * scale)
            if min(scaled_w, scaled_h) < 32:  # Пропускаем слишком маленькие
                continue
                
            scaled_img = cv2.resize(image, (scaled_w, scaled_h))
            
            if isinstance(face_detector, cv2.FaceDetectorYN):
                face_detector.setInputSize((scaled_w, scaled_h))
                _, faces_yunet = face_detector.detect(scaled_img)
                
                if faces_yunet is not None and len(faces_yunet) > 0:
                    for face_info in faces_yunet:
                        confidence = float(face_info[-1])
                        if confidence > 0.4:  # Пониженный порог
                            x, y, w_face, h_face = face_info[0:4]
                            # Масштабируем обратно
                            x, y, w_face, h_face = int(x/scale), int(y/scale), int(w_face/scale), int(h_face/scale)
                            faces_data.append({
                                "bbox": (x, y, w_face, h_face),
                                "landmarks": None,
                                "confidence": confidence
                            })
                    # Если нашли лица, прекращаем поиск
                    if faces_data:
                        break
    
    # 3. ПОПЫТКА: Если все еще не обнаружены, пробуем поиск по квадрантам
    if not faces_data:
        quadrant_faces = detect_faces_by_quadrants(image)
        if quadrant_faces:
            faces_data.extend(quadrant_faces)
    
    # 4. ПОПЫТКА: Если все еще нет лиц, пробуем специальный метод для крупных лиц
    if not faces_data:
        large_faces = detect_large_face(image)
        if large_faces:
            faces_data.extend(large_faces)
    
    # 5. ПОПЫТКА: Если все еще нет, пробуем DNN детектор
    if not faces_data and dnn_face_detector is not None:
        dnn_faces = detect_faces_with_dnn(image)
        if dnn_faces:
            faces_data.extend(dnn_faces)
    
    # 6. ПОПЫТКА: Улучшаем контраст и пробуем снова
    if not faces_data:
        try:
            # Улучшаем контраст
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            
            # Конвертируем в LAB и применяем CLAHE к L-каналу
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            cl = clahe.apply(l)
            enhanced_lab = cv2.merge((cl, a, b))
            enhanced_img = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
            
            # Пробуем YuNet снова с улучшенным изображением
            if isinstance(face_detector, cv2.FaceDetectorYN):
                face_detector.setInputSize((w, h))
                _, faces_yunet = face_detector.detect(enhanced_img)
                
                if faces_yunet is not None and len(faces_yunet) > 0:
                    for face_info in faces_yunet:
                        confidence = float(face_info[-1])
                        if confidence > 0.3:  # Снижаем порог для улучшенного изображения
                            bbox = tuple(map(int, face_info[0:4]))
                            faces_data.append({
                                "bbox": bbox,
                                "landmarks": None,
                                "confidence": confidence
                            })
        except Exception as e:
            logger.error(f"Error enhancing image contrast: {e}")
    
    # 7. ПОПЫТКА: Экспериментальная техника: использование маски кожи
    if not faces_data:
        try:
            skin_mask = detect_skin_regions(image)
            
            # Найти наибольший контур на маске кожи
            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if contours:
                # Находим самый большой контур
                max_contour = max(contours, key=cv2.contourArea)
                area = cv2.contourArea(max_contour)
                
                # Если контур достаточно большой
                if area > 0.05 * w * h:  # Мин. 5% от площади изображения
                    x, y, w_rect, h_rect = cv2.boundingRect(max_contour)
                    
                    # Проверяем пропорции (лицо обычно выше, чем шире)
                    aspect_ratio = w_rect / h_rect
                    if 0.5 <= aspect_ratio <= 1.2:
                        # Добавляем как потенциальное лицо
                        faces_data.append({
                            "bbox": (x, y, w_rect, h_rect),
                            "landmarks": None,
                            "confidence": 0.7  # Предполагаемая уверенность
                        })
        except Exception as e:
            logger.warning(f"Error in skin detection: {e}")
    
    # 8. ПОСЛЕДНЯЯ ПОПЫТКА: Эвристическое обнаружение лица
    if not faces_data:
        emergency_faces = emergency_face_detection(image)
        if emergency_faces:
            faces_data.extend(emergency_faces)
    
    # Определение лицевых точек, если возможно
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
                
                # Обновляем данные лиц с лицевыми точками
                for i in range(min(len(faces_data), len(landmarks_list))):
                    faces_data[i]["landmarks"] = landmarks_list[i]
        except Exception as e:
            logger.error(f"Error during facemark fitting: {e}")
    
    logger.info(f"Detected {len(faces_data)} faces.")
    return faces_data


def estimate_pose(image_shape: Tuple[int, int], landmarks: List[Tuple[int, int]]) -> Dict[str, float]:
    """
    Оценка углов позы лица (yaw, pitch, roll) по лицевым точкам.
    Использует solvePnP.
    """
    h, w = image_shape
    focal_length = w # Приближенное значение
    center = (w / 2, h / 2)
    camera_matrix = np.array(
        [[focal_length, 0, center[0]],
         [0, focal_length, center[1]],
         [0, 0, 1]], dtype="double"
    )
    dist_coeffs = np.zeros((4, 1)) # Без искажений

    # Стандартная 3D модель лица (ключевые точки)
    model_points = np.array([
        (0.0, 0.0, 0.0),             # Нос (Nose tip - 30)
        (0.0, -330.0, -65.0),        # Подбородок (Chin - 8)
        (-225.0, 170.0, -135.0),     # Лев. угол глаза (Left eye left corner - 36)
        (225.0, 170.0, -135.0),      # Прав. угол глаза (Right eye right corner - 45)
        (-150.0, -150.0, -125.0),    # Лев. угол рта (Left Mouth corner - 48)
        (150.0, -150.0, -125.0)     # Прав. угол рта (Right mouth corner - 54)
    ])

    # 2D точки изображения, соответствующие 3D модели
    # Проверяем, что нужные индексы существуют
    required_indices = [30, 8, 36, 45, 48, 54]
    if any(idx >= len(landmarks) for idx in required_indices):
        logger.warning("Insufficient landmarks for solvePnP.")
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

    image_points = np.array([
        landmarks[30], # Нос
        landmarks[8],  # Подбородок
        landmarks[36], # Лев. угол глаза
        landmarks[45], # Прав. угол глаза
        landmarks[48], # Лев. угол рта
        landmarks[54]  # Прав. угол рта
    ], dtype="double")

    try:
        (success, rotation_vector, translation_vector) = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs, flags=cv2.SOLVEPNP_ITERATIVE
        )

        if not success:
             logger.warning("solvePnP failed to estimate pose.")
             return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

        # Получаем матрицу поворота
        rotation_matrix, _ = cv2.Rodrigues(rotation_vector)
        
        # Вычисляем углы Эйлера (порядок: ZYX)
        # Порядок: сначала вокруг Z (roll), потом Y (yaw), потом X (pitch)
        pitch = math.degrees(math.atan2(-rotation_matrix[2, 0], 
                                      math.sqrt(rotation_matrix[2, 1]**2 + rotation_matrix[2, 2]**2)))
        yaw = math.degrees(math.atan2(rotation_matrix[1, 0], rotation_matrix[0, 0]))
        roll = math.degrees(math.atan2(rotation_matrix[2, 1], rotation_matrix[2, 2]))

        # Нормализуем углы в диапазон [-180, 180]
        # Корректируем pitch для соответствия ожидаемому диапазону
        if abs(pitch) > 90:
            pitch = 180 - abs(pitch) if pitch > 0 else -(180 - abs(pitch))

        yaw = (yaw + 180) % 360 - 180
        pitch = (pitch + 180) % 360 - 180
        roll = (roll + 180) % 360 - 180

        return {"yaw": yaw, "pitch": pitch, "roll": roll}

    except Exception as e:
        logger.error(f"Error estimating pose with solvePnP: {e}")
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}