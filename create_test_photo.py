#!/usr/bin/env python3
"""
Скрипт для создания простого тестового изображения лица,
которое может пройти все проверки валидации.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

def create_simple_face_photo(width=600, height=800, filename="test_approved_photo.jpg"):
    """
    Создает простое изображение лица, которое должно пройти большинство проверок.
    
    Args:
        width: Ширина изображения
        height: Высота изображения  
        filename: Имя файла для сохранения
    """
    
    # Создаем изображение с белым фоном
    img = np.ones((height, width, 3), dtype=np.uint8) * 240  # Светло-серый фон
    
    # Параметры лица
    face_center_x = width // 2
    face_center_y = height // 2 - 50
    face_width = 200
    face_height = 250
    
    # Рисуем овал лица (телесный цвет)
    face_color = (220, 180, 140)  # Телесный цвет
    cv2.ellipse(img, (face_center_x, face_center_y), (face_width//2, face_height//2), 0, 0, 360, face_color, -1)
    
    # Рисуем глаза
    eye_y = face_center_y - 30
    left_eye_x = face_center_x - 40
    right_eye_x = face_center_x + 40
    
    # Белки глаз
    cv2.ellipse(img, (left_eye_x, eye_y), (20, 12), 0, 0, 360, (255, 255, 255), -1)
    cv2.ellipse(img, (right_eye_x, eye_y), (20, 12), 0, 0, 360, (255, 255, 255), -1)
    
    # Зрачки (коричневые)
    cv2.circle(img, (left_eye_x, eye_y), 8, (101, 67, 33), -1)
    cv2.circle(img, (right_eye_x, eye_y), 8, (101, 67, 33), -1)
    
    # Центры зрачков (черные)
    cv2.circle(img, (left_eye_x, eye_y), 4, (0, 0, 0), -1)
    cv2.circle(img, (right_eye_x, eye_y), 4, (0, 0, 0), -1)
    
    # Нос
    nose_points = np.array([
        [face_center_x, face_center_y - 10],
        [face_center_x - 8, face_center_y + 15],
        [face_center_x + 8, face_center_y + 15]
    ], np.int32)
    cv2.fillPoly(img, [nose_points], (200, 160, 120))
    
    # Рот
    mouth_y = face_center_y + 40
    cv2.ellipse(img, (face_center_x, mouth_y), (25, 8), 0, 0, 180, (150, 100, 100), 3)
    
    # Брови
    brow_y = eye_y - 25
    cv2.ellipse(img, (left_eye_x, brow_y), (25, 5), 0, 0, 180, (101, 67, 33), 3)
    cv2.ellipse(img, (right_eye_x, brow_y), (25, 5), 0, 0, 180, (101, 67, 33), 3)
    
    # Волосы (простая шапка)
    hair_points = np.array([
        [face_center_x - face_width//2 - 20, face_center_y - face_height//2 - 20],
        [face_center_x + face_width//2 + 20, face_center_y - face_height//2 - 20],
        [face_center_x + face_width//2, face_center_y - face_height//2 + 30],
        [face_center_x - face_width//2, face_center_y - face_height//2 + 30]
    ], np.int32)
    cv2.fillPoly(img, [hair_points], (101, 67, 33))
    
    # Добавляем немного шума для реалистичности
    noise = np.random.normal(0, 5, img.shape).astype(np.int16)
    img = np.clip(img.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    
    # Сохраняем изображение
    cv2.imwrite(filename, img)
    print(f"Создано тестовое изображение: {filename}")
    
    return filename

def create_high_quality_face_photo(filename="test_approved_photo_hq.jpg"):
    """
    Создает более качественное изображение лица с использованием PIL.
    """
    # Создаем изображение
    width, height = 600, 800
    img = Image.new('RGB', (width, height), color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    
    # Параметры лица
    face_center_x = width // 2
    face_center_y = height // 2 - 50
    face_width = 200
    face_height = 250
    
    # Рисуем овал лица
    face_bbox = [
        face_center_x - face_width//2,
        face_center_y - face_height//2,
        face_center_x + face_width//2,
        face_center_y + face_height//2
    ]
    draw.ellipse(face_bbox, fill=(220, 180, 140))
    
    # Глаза
    eye_y = face_center_y - 30
    left_eye_x = face_center_x - 40
    right_eye_x = face_center_x + 40
    
    # Белки глаз
    draw.ellipse([left_eye_x-20, eye_y-12, left_eye_x+20, eye_y+12], fill=(255, 255, 255))
    draw.ellipse([right_eye_x-20, eye_y-12, right_eye_x+20, eye_y+12], fill=(255, 255, 255))
    
    # Зрачки
    draw.ellipse([left_eye_x-8, eye_y-8, left_eye_x+8, eye_y+8], fill=(101, 67, 33))
    draw.ellipse([right_eye_x-8, eye_y-8, right_eye_x+8, eye_y+8], fill=(101, 67, 33))
    
    # Центры зрачков
    draw.ellipse([left_eye_x-4, eye_y-4, left_eye_x+4, eye_y+4], fill=(0, 0, 0))
    draw.ellipse([right_eye_x-4, eye_y-4, right_eye_x+4, eye_y+4], fill=(0, 0, 0))
    
    # Нос (треугольник)
    nose_points = [
        (face_center_x, face_center_y - 10),
        (face_center_x - 8, face_center_y + 15),
        (face_center_x + 8, face_center_y + 15)
    ]
    draw.polygon(nose_points, fill=(200, 160, 120))
    
    # Рот
    mouth_y = face_center_y + 40
    draw.arc([face_center_x-25, mouth_y-8, face_center_x+25, mouth_y+8], 0, 180, fill=(150, 100, 100), width=3)
    
    # Брови
    brow_y = eye_y - 25
    draw.arc([left_eye_x-25, brow_y-5, left_eye_x+25, brow_y+5], 0, 180, fill=(101, 67, 33), width=3)
    draw.arc([right_eye_x-25, brow_y-5, right_eye_x+25, brow_y+5], 0, 180, fill=(101, 67, 33), width=3)
    
    # Волосы
    hair_bbox = [
        face_center_x - face_width//2 - 20,
        face_center_y - face_height//2 - 40,
        face_center_x + face_width//2 + 20,
        face_center_y - face_height//2 + 30
    ]
    draw.ellipse(hair_bbox, fill=(101, 67, 33))
    
    # Сохраняем
    img.save(filename, 'JPEG', quality=95)
    print(f"Создано высококачественное изображение: {filename}")
    
    return filename

def create_colorful_face_photo(filename="test_approved_colorful.jpg"):
    """
    Создает цветное изображение лица, которое должно пройти все проверки.
    """
    # Создаем изображение
    width, height = 600, 800
    img = Image.new('RGB', (width, height), color=(200, 220, 240))  # Светло-голубой фон
    draw = ImageDraw.Draw(img)
    
    # Параметры лица
    face_center_x = width // 2
    face_center_y = height // 2 - 50
    face_width = 180
    face_height = 220
    
    # Рисуем овал лица (более розовый телесный цвет)
    face_bbox = [
        face_center_x - face_width//2,
        face_center_y - face_height//2,
        face_center_x + face_width//2,
        face_center_y + face_height//2
    ]
    draw.ellipse(face_bbox, fill=(255, 200, 180))  # Более розовый
    
    # Глаза
    eye_y = face_center_y - 25
    left_eye_x = face_center_x - 35
    right_eye_x = face_center_x + 35
    
    # Белки глаз
    draw.ellipse([left_eye_x-18, eye_y-10, left_eye_x+18, eye_y+10], fill=(255, 255, 255))
    draw.ellipse([right_eye_x-18, eye_y-10, right_eye_x+18, eye_y+10], fill=(255, 255, 255))
    
    # Радужки (голубые)
    draw.ellipse([left_eye_x-7, eye_y-7, left_eye_x+7, eye_y+7], fill=(70, 130, 180))
    draw.ellipse([right_eye_x-7, eye_y-7, right_eye_x+7, eye_y+7], fill=(70, 130, 180))
    
    # Зрачки
    draw.ellipse([left_eye_x-3, eye_y-3, left_eye_x+3, eye_y+3], fill=(0, 0, 0))
    draw.ellipse([right_eye_x-3, eye_y-3, right_eye_x+3, eye_y+3], fill=(0, 0, 0))
    
    # Нос (более мягкий)
    nose_points = [
        (face_center_x, face_center_y - 5),
        (face_center_x - 6, face_center_y + 10),
        (face_center_x + 6, face_center_y + 10)
    ]
    draw.polygon(nose_points, fill=(240, 180, 160))
    
    # Рот (красные губы)
    mouth_y = face_center_y + 35
    draw.ellipse([face_center_x-20, mouth_y-5, face_center_x+20, mouth_y+5], fill=(200, 100, 120))
    
    # Брови (коричневые)
    brow_y = eye_y - 20
    draw.ellipse([left_eye_x-20, brow_y-3, left_eye_x+20, brow_y+3], fill=(139, 69, 19))
    draw.ellipse([right_eye_x-20, brow_y-3, right_eye_x+20, brow_y+3], fill=(139, 69, 19))
    
    # Волосы (темно-коричневые, более естественная форма)
    hair_bbox = [
        face_center_x - face_width//2 - 15,
        face_center_y - face_height//2 - 30,
        face_center_x + face_width//2 + 15,
        face_center_y - face_height//2 + 40
    ]
    draw.ellipse(hair_bbox, fill=(101, 67, 33))
    
    # Добавляем румянец
    draw.ellipse([left_eye_x-10, face_center_y+10, left_eye_x+10, face_center_y+30], fill=(255, 180, 180))
    draw.ellipse([right_eye_x-10, face_center_y+10, right_eye_x+10, face_center_y+30], fill=(255, 180, 180))
    
    # Сохраняем с высоким качеством
    img.save(filename, 'JPEG', quality=95)
    print(f"Создано цветное изображение: {filename}")
    
    return filename

if __name__ == "__main__":
    # Создаем все варианты
    cv_photo = create_simple_face_photo()
    pil_photo = create_high_quality_face_photo()
    colorful_photo = create_colorful_face_photo()
    
    print(f"Созданы тестовые изображения:")
    print(f"1. {cv_photo}")
    print(f"2. {pil_photo}")
    print(f"3. {colorful_photo}")
    print(f"Размеры файлов:")
    print(f"1. {os.path.getsize(cv_photo)} байт")
    print(f"2. {os.path.getsize(pil_photo)} байт")
    print(f"3. {os.path.getsize(colorful_photo)} байт") 