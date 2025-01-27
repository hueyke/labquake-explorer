"""Configuration settings for Event Explorer"""
from dataclasses import dataclass

@dataclass
class EventExplorerConfig:
    """Configuration settings for the application"""
    WINDOW_GAP: int = 100
    WINDOW_WIDTH: int = 300
    WINDOW_TITLE: str = "Event Explorer"
    MAX_ARRAY_DISPLAY: int = 1000
    DEFAULT_WINDOW_SIZE: float = 5.0
    FILE_TYPES: tuple = (
        ("NPZ files", "*.npz"),
        ("HDF5 files", "*.h5 *.hdf5"),
        ("All files", "*.*")
    )