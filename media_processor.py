"""
Модуль с классами для обработки медиафайлов.
Вариант 4: Смешанный (видео + аудио).
"""

import os
import wave
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple

import cv2

from media_exceptions import (
    MediaError,
    FileLoadError,
    InvalidDataError,
    FormatMismatchError,
    MediaSyncError,
)


class MediaProcessor(ABC):
    """Абстрактный класс для обработчиков медиафайлов."""

    @abstractmethod
    def process(self, file_path: str) -> Any:
        """Обрабатывает медиафайл."""
        pass

    @abstractmethod
    def validate(self, file_path: str) -> bool:
        """Валидирует медиафайл."""
        pass


class MixedMediaProcessor(MediaProcessor):
    """
    Класс для совместной обработки видео- и аудиопотоков.
    Вариант 4.
    """

    SUPPORTED_VIDEO_FORMATS = ('.mp4', '.avi', '.mkv')
    SUPPORTED_AUDIO_FORMATS = ('.wav',)

    def __init__(self, sync_tolerance: float = 0.5):
        """
        :param sync_tolerance: допустимая разница длительностей аудио и видео (в секундах)
        """
        self.sync_tolerance = sync_tolerance

    def validate(self, file_path: str) -> bool:
        """
        Проверяет существование файла и допустимость расширения.
        """
        if not os.path.exists(file_path):
            return False

        ext = os.path.splitext(file_path)[1].lower()
        return ext in self.SUPPORTED_VIDEO_FORMATS or ext in self.SUPPORTED_AUDIO_FORMATS

    def load_media(self, video_path: str, audio_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Загружает метаданные видео и аудио, проверяя форматы и целостность.
        """
        # 1. Проверка существования файлов
        if not os.path.exists(video_path):
            raise FileLoadError(video_path, "Видеофайл не найден")
        if not os.path.exists(audio_path):
            raise FileLoadError(audio_path, "Аудиофайл не найден")

        # 2. Проверка поддерживаемых форматов
        video_ext = os.path.splitext(video_path)[1].lower()
        audio_ext = os.path.splitext(audio_path)[1].lower()

        if video_ext not in self.SUPPORTED_VIDEO_FORMATS:
            raise FormatMismatchError(
                video_path,
                expected_format=str(self.SUPPORTED_VIDEO_FORMATS),
                actual_format=video_ext
            )

        if audio_ext not in self.SUPPORTED_AUDIO_FORMATS:
            raise FormatMismatchError(
                audio_path,
                expected_format=str(self.SUPPORTED_AUDIO_FORMATS),
                actual_format=audio_ext
            )

        # 3. Чтение параметров видео (OpenCV)
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise InvalidDataError(video_path, data_type="видеопоток (декодирование не удалось)")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()

        if fps <= 0 or frame_count <= 0:
            raise InvalidDataError(video_path, data_type="поврежденные метаданные кадров")

        video_duration = frame_count / fps

        # 4. Чтение параметров аудио (wave)
        try:
            with wave.open(audio_path, 'rb') as audio_file:
                sample_rate = audio_file.getframerate()
                n_frames = audio_file.getnframes()
                channels = audio_file.getnchannels()

                if sample_rate <= 0:
                    raise InvalidDataError(audio_path, data_type="некорректная частота дискретизации")

                audio_duration = n_frames / float(sample_rate)
        except wave.Error as e:
            raise InvalidDataError(audio_path, data_type=f"поврежденный WAV-заголовок ({e})")
        except Exception as e:
            raise FileLoadError(audio_path, f"Ошибка чтения аудио: {e}")

        video_info = {
            "path": video_path,
            "fps": fps,
            "frames": int(frame_count),
            "duration": video_duration
        }

        audio_info = {
            "path": audio_path,
            "sample_rate": sample_rate,
            "channels": channels,
            "duration": audio_duration
        }

        return video_info, audio_info

    def synchronize_streams(self, video_info: Dict[str, Any], audio_info: Dict[str, Any]) -> bool:
        """
        Проверяет совпадение длительностей видео- и аудиопотоков в пределах допуска.
        """
        v_dur = video_info["duration"]
        a_dur = audio_info["duration"]
        diff = abs(v_dur - a_dur)

        if diff > self.sync_tolerance:
            raise MediaSyncError(
                file_path=f"[{video_info['path']} <-> {audio_info['path']}]",
                time_diff=diff,
                message=f"Длительности видео ({v_dur:.2f}с) и аудио ({a_dur:.2f}с) не совпадают"
            )

        return True

    def process(self, media_pair: Tuple[str, str]) -> Dict[str, Any]:
        """
        Реализация абстрактного метода process.
        Принимает кортеж (video_path, audio_path) и производит сведение.
        """
        video_path, audio_path = media_pair

        # load_media самостоятельно проверяет наличие файлов (вызывая FileLoadError)
        # и соответствие форматов (вызывая FormatMismatchError)
        video_info, audio_info = self.load_media(video_path, audio_path)
        self.synchronize_streams(video_info, audio_info)

        return {
            "status": "synchronized",
            "video_duration": video_info["duration"],
            "audio_duration": audio_info["duration"],
            "fps": video_info["fps"],
            "audio_sample_rate": audio_info["sample_rate"]
        }