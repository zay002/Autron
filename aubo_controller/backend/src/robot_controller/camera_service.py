"""
Camera Service Module - Abstraction layer for camera integration.

This module provides a vendor-agnostic interface for camera operations.
Vendor-specific implementations should be isolated in adapter classes.
"""

from __future__ import annotations

import time
import numpy as np
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum
from abc import ABC, abstractmethod


class CameraConnectionState(Enum):
    """Camera connection states."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    STREAMING = "streaming"
    ERROR = "error"


@dataclass
class CameraFrame:
    """Represents a single camera frame."""
    timestamp: float
    width: int
    height: int
    channels: int
    data: Optional[np.ndarray] = None
    is_mock: bool = True


@dataclass
class CameraInfo:
    """Camera device information."""
    name: str
    serial: str
    resolution: str
    firmware_version: str
    is_mock: bool = True


class CameraAdapter(ABC):
    """Abstract base class for camera adapters."""

    @abstractmethod
    def connect(self) -> bool:
        """Connect to the camera."""
        pass

    @abstractmethod
    def disconnect(self) -> bool:
        """Disconnect from the camera."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if camera is connected."""
        pass

    @abstractmethod
    def get_frame(self) -> Optional[CameraFrame]:
        """Get a single frame from the camera."""
        pass

    @abstractmethod
    def get_info(self) -> CameraInfo:
        """Get camera information."""
        pass


class MockCameraAdapter(CameraAdapter):
    """
    Mock camera adapter for testing and development.

    This adapter generates synthetic frames when no real camera is available.
    It always returns valid data to allow development without hardware.
    """

    def __init__(self):
        self._connected = False
        self._frame_count = 0
        self._width = 640
        self._height = 480
        self._channels = 3

    def connect(self) -> bool:
        """Connect to mock camera."""
        self._connected = True
        self._frame_count = 0
        return True

    def disconnect(self) -> bool:
        """Disconnect from mock camera."""
        self._connected = False
        return True

    def is_connected(self) -> bool:
        """Check if mock camera is connected."""
        return self._connected

    def get_frame(self) -> Optional[CameraFrame]:
        """Get a mock frame."""
        if not self._connected:
            return None

        # Generate a synthetic RGB frame with a gradient
        self._frame_count += 1
        frame = np.zeros((self._height, self._width, self._channels), dtype=np.uint8)

        # Create a gradient pattern
        for y in range(self._height):
            for x in range(self._width):
                frame[y, x, 0] = int((x / self._width) * 255)  # R
                frame[y, x, 1] = int((y / self._height) * 255)  # G
                frame[y, x, 2] = 128  # B

        # Add frame counter indicator (top-left corner)
        frame[0:30, 0:200] = [50, 50, 50]

        return CameraFrame(
            timestamp=time.time(),
            width=self._width,
            height=self._height,
            channels=self._channels,
            data=frame,
            is_mock=True,
        )

    def get_info(self) -> CameraInfo:
        """Get mock camera information."""
        return CameraInfo(
            name="Mock Camera",
            serial="MOCK-00000",
            resolution=f"{self._width}x{self._height}",
            firmware_version="1.0.0-mock",
            is_mock=True,
        )


class CameraService:
    """
    Central camera service managing the camera adapter.

    This service provides a stable interface for camera operations
    and manages the lifecycle of the camera adapter.
    """

    def __init__(self, adapter: Optional[CameraAdapter] = None):
        """
        Initialize camera service.

        Args:
            adapter: Camera adapter instance. If None, uses MockCameraAdapter.
        """
        self._adapter = adapter or MockCameraAdapter()
        self._connection_state = CameraConnectionState.DISCONNECTED
        self._last_frame: Optional[CameraFrame] = None
        self._error_message: Optional[str] = None

    def connect(self) -> Dict[str, Any]:
        """
        Connect to the camera.

        Returns:
            Dictionary with connection result and camera info.
        """
        try:
            if self._connection_state == CameraConnectionState.CONNECTED:
                return {
                    "success": True,
                    "message": "Already connected",
                    "state": self._connection_state.value,
                }

            self._connection_state = CameraConnectionState.CONNECTING
            self._error_message = None

            success = self._adapter.connect()

            if success:
                self._connection_state = CameraConnectionState.CONNECTED
                info = self._adapter.get_info()
                return {
                    "success": True,
                    "message": "Connected successfully",
                    "state": self._connection_state.value,
                    "camera_info": {
                        "name": info.name,
                        "serial": info.serial,
                        "resolution": info.resolution,
                        "firmware_version": info.firmware_version,
                        "is_mock": info.is_mock,
                    },
                }
            else:
                self._connection_state = CameraConnectionState.ERROR
                self._error_message = "Connection failed"
                return {
                    "success": False,
                    "message": self._error_message,
                    "state": self._connection_state.value,
                }

        except Exception as e:
            self._connection_state = CameraConnectionState.ERROR
            self._error_message = str(e)
            return {
                "success": False,
                "message": f"Connection error: {e}",
                "state": self._connection_state.value,
            }

    def disconnect(self) -> Dict[str, Any]:
        """
        Disconnect from the camera.

        Returns:
            Dictionary with disconnection result.
        """
        try:
            self._adapter.disconnect()
            self._connection_state = CameraConnectionState.DISCONNECTED
            self._last_frame = None
            return {
                "success": True,
                "message": "Disconnected successfully",
                "state": self._connection_state.value,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Disconnect error: {e}",
                "state": self._connection_state.value,
            }

    def get_status(self) -> Dict[str, Any]:
        """
        Get current camera status.

        Returns:
            Dictionary with camera status information.
        """
        info = self._adapter.get_info()
        return {
            "connected": self._adapter.is_connected(),
            "state": self._connection_state.value,
            "error_message": self._error_message,
            "camera_info": {
                "name": info.name,
                "serial": info.serial,
                "resolution": info.resolution,
                "firmware_version": info.firmware_version,
                "is_mock": info.is_mock,
            },
            "last_frame_timestamp": self._last_frame.timestamp if self._last_frame else None,
        }

    def get_frame(self) -> Optional[Dict[str, Any]]:
        """
        Get a frame from the camera.

        Returns:
            Dictionary with frame data (as base64) or None if unavailable.
        """
        if not self._adapter.is_connected():
            return None

        try:
            frame = self._adapter.get_frame()
            if frame is None:
                return None

            self._last_frame = frame

            # Encode frame as JPEG for transport
            import base64
            import cv2

            if frame.data is not None:
                _, buffer = cv2.imencode('.jpg', frame.data)
                frame_base64 = base64.b64encode(buffer).decode('utf-8')
            else:
                frame_base64 = None

            return {
                "timestamp": frame.timestamp,
                "width": frame.width,
                "height": frame.height,
                "channels": frame.channels,
                "frame": frame_base64,
                "is_mock": frame.is_mock,
            }

        except Exception as e:
            self._error_message = str(e)
            return None

    @property
    def connection_state(self) -> CameraConnectionState:
        """Get current connection state."""
        return self._connection_state

    @property
    def is_connected(self) -> bool:
        """Check if camera is connected."""
        return self._adapter.is_connected()


# Factory function
def create_camera_service(use_mock: bool = True) -> CameraService:
    """
    Create a camera service.

    Args:
        use_mock: If True, uses mock adapter. If False, would use real adapter.

    Returns:
        CameraService instance.
    """
    if use_mock:
        return CameraService(MockCameraAdapter())
    # Future: Real camera adapter would be instantiated here
    # return CameraService(RealCameraAdapter())
