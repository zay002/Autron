"""
Eye 3D Camera Adapter - Vendor-specific implementation for Eye 3D cameras.

This adapter provides the vendor-specific integration for Eye 3D M2-EyePro series cameras
using the Eye3DViewer SDK (Eye3DViewer_API.dll).

PDF Reference: D:\\Autron\\eye-3d-camera-v2.5.4-zh.pdf

Supported Devices:
- M2-EyePro-000: USB3.0 grayscale camera
- M2-EyePro-001: USB3.0 color camera (1280x720)
- M2-EyePro-002: USB3.0 depth camera

SDK API (from PDF):
- Initialize()           - SDK initialization
- Uninit()              - SDK cleanup
- GetDeviceCount()      - Get number of connected devices
- GetDeviceInfoW()      - Get device info (Unicode)
- OpenDevice()          - Open device by index
- CloseDevice()         - Close device
- StartImageAcquire()   - Start image acquisition
- StopImageAcquire()    - Stop image acquisition
- GetColorImage()       - Get color image (RGB)
- GetDepthImage()       - Get depth image
- GetPointCloud()       - Get point cloud data

Python Interface via ctypes:
    camera = cdll.LoadLibrary("Eye3DViewer_API.dll")
    camera.Initialize()
"""

from __future__ import annotations

import ctypes
import time
from pathlib import Path
from typing import Optional

from robot_controller.camera_service import CameraAdapter, CameraFrame, CameraInfo


class Eye3DCameraAdapter(CameraAdapter):
    """
    Eye 3D M2-EyePro camera adapter using the Eye3DViewer SDK.

    This adapter communicates with Eye 3D cameras via the vendor SDK DLL.
    It supports RGB color imaging, depth imaging, and point cloud acquisition.

    Connection Flow:
    1. Initialize SDK (once per process)
    2. Enumerate devices with GetDeviceCount()
    3. Get device info with GetDeviceInfoW()
    4. Open device with OpenDevice()
    5. Start acquisition with StartImageAcquire()
    6. Grab frames with GetColorImage() / GetDepthImage()
    7. Stop and close on disconnect

    Required:
    - Eye3DViewer_API.dll in system PATH or alongside this module
    - USB3.0 connection to M2-EyePro camera
    - M2-EyePro-001 or compatible color camera for RGB mode
    """

    _sdk_initialized = False
    _sdk_refcount = 0

    def __init__(self, device_index: int = 0, dll_path: Optional[str] = None):
        """
        Initialize the Eye 3D camera adapter.

        Args:
            device_index: Index of the camera to open (0 = first device).
            dll_path: Optional path to Eye3DViewer_API.dll. If None, uses system PATH.
        """
        self._device_index = device_index
        self._connected = False
        self._streaming = False
        self._camera = None
        self._width = 1280  # M2-EyePro-001 default width
        self._height = 720  # M2-EyePro-001 default height
        self._camera_model = "M2-EyePro-001"
        self._firmware_version = "unknown"

        # Find DLL
        if dll_path:
            dll_file = Path(dll_path)
        else:
            # Look for DLL in common locations
            possible_paths = [
                Path(__file__).parent / "Eye3DViewer_API.dll",
                Path("C:/Eye3DViewer/Eye3DViewer_API.dll"),
                Path("C:/Program Files/Eye3DViewer/Eye3DViewer_API.dll"),
            ]
            dll_file = None
            for p in possible_paths:
                if p.exists():
                    dll_file = p
                    break

        self._dll_path = dll_file

    def _ensure_sdk_initialized(self) -> bool:
        """Initialize SDK if not already done."""
        if not Eye3DCameraAdapter._sdk_initialized:
            try:
                if self._dll_path:
                    self._camera = ctypes.CDLL(str(self._dll_path))
                else:
                    self._camera = ctypes.CDLL("Eye3DViewer_API.dll")

                # Initialize SDK
                result = self._camera.Initialize()
                if result != 0:
                    print(f"SDK Initialize failed with code: {result}")
                    self._camera = None
                    return False

                Eye3DCameraAdapter._sdk_initialized = True
            except OSError as e:
                print(f"Failed to load Eye3DViewer_API.dll: {e}")
                self._camera = None
                return False

        Eye3DCameraAdapter._sdk_refcount += 1
        return True

    def _cleanup_sdk(self):
        """Decrement SDK reference count and uninit if zero."""
        Eye3DCameraAdapter._sdk_refcount -= 1
        if Eye3DCameraAdapter._sdk_refcount <= 0:
            if self._camera:
                self._camera.Uninit()
                Eye3DCameraAdapter._sdk_initialized = False
                self._sdk_refcount = 0

    def connect(self) -> bool:
        """Connect to the Eye 3D camera device."""
        if self._connected:
            return True

        # Initialize SDK
        if not self._ensure_sdk_initialized():
            return False

        try:
            # Get device count
            device_count = self._camera.GetDeviceCount()
            if device_count <= 0:
                print("No Eye 3D devices found")
                return False

            if self._device_index >= device_count:
                print(f"Device index {self._device_index} out of range (found {device_count} devices)")
                return False

            # Get device info (Unicode version - GetDeviceInfoW)
            # Device info structure:
            # struct DeviceInfo {
            #     wchar_t device_name[64];
            #     wchar_t device_id[64];
            #     wchar_t firmware_version[64];
            #     int width;
            #     int height;
            # }
            class DeviceInfo(ctypes.Structure):
                _fields_ = [
                    ("device_name", ctypes.c_wchar * 64),
                    ("device_id", ctypes.c_wchar * 64),
                    ("firmware_version", ctypes.c_wchar * 64),
                    ("width", ctypes.c_int),
                    ("height", ctypes.c_int),
                ]

            device_info = DeviceInfo()
            result = self._camera.GetDeviceInfoW(self._device_index, ctypes.byref(device_info))
            if result != 0:
                print(f"GetDeviceInfoW failed with code: {result}")
                return False

            self._width = device_info.width
            self._height = device_info.height
            self._camera_model = device_info.device_name
            self._firmware_version = device_info.firmware_version

            # Open device
            result = self._camera.OpenDevice(self._device_index)
            if result != 0:
                print(f"OpenDevice failed with code: {result}")
                return False

            self._connected = True
            return True

        except Exception as e:
            print(f"Failed to connect to Eye 3D camera: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect from the Eye 3D camera device."""
        if not self._connected:
            return True

        try:
            if self._streaming:
                self._camera.StopImageAcquire()
                self._streaming = False

            self._camera.CloseDevice()
            self._connected = False
            self._cleanup_sdk()
            return True

        except Exception as e:
            print(f"Failed to disconnect Eye 3D camera: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if camera is connected."""
        return self._connected

    def get_frame(self) -> Optional[CameraFrame]:
        """
        Get a single RGB frame from the Eye 3D camera.

        Returns:
            CameraFrame with RGB data (1280x720x3), or None on failure.
        """
        if not self._connected:
            return None

        try:
            # Start acquisition if not already streaming
            if not self._streaming:
                result = self._camera.StartImageAcquire()
                if result != 0:
                    print(f"StartImageAcquire failed with code: {result}")
                    return None
                self._streaming = True

            # Get color image
            # Color data is returned as a pointer + size
            # The SDK allocates buffer, we need to free it after use
            buffer_size = self._width * self._height * 3  # RGB24
            color_buffer = ctypes.create_string_buffer(buffer_size)

            result = self._camera.GetColorImage(color_buffer, buffer_size)
            if result != 0:
                print(f"GetColorImage failed with code: {result}")
                return None

            # Convert to numpy array
            import numpy as np
            frame_data = np.frombuffer(color_buffer, dtype=np.uint8).reshape(
                (self._height, self._width, 3)
            ).copy()

            return CameraFrame(
                timestamp=time.time(),
                width=self._width,
                height=self._height,
                channels=3,
                data=frame_data,
                is_mock=False,
            )

        except Exception as e:
            print(f"Failed to get frame from Eye 3D camera: {e}")
            return None

    def get_info(self) -> CameraInfo:
        """Get Eye 3D camera device information."""
        return CameraInfo(
            name=self._camera_model,
            serial="N/A",  # Device ID available via GetDeviceInfoW if needed
            resolution=f"{self._width}x{self._height}",
            firmware_version=self._firmware_version,
            is_mock=False,
        )
