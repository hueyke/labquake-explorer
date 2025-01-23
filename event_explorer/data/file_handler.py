"""File handling operations for Event Explorer"""
import h5py
import numpy as np
from pathlib import Path
from typing import Dict, Any

class FileHandler:
    def load(self, path: Path) -> Dict[str, Any]:
        """Load data from file"""
        if path.suffix.lower() == '.npz':
            return self._load_npz(path)
        elif path.suffix.lower() in ['.h5', '.hdf5']:
            return self._load_hdf5(path)
        raise ValueError(f"Unsupported file type: {path.suffix}")

    def _load_npz(self, path: Path) -> Dict[str, Any]:
        with np.load(path, allow_pickle=True) as data:
            return data["experiment"][()]

    def _load_hdf5(self, path: Path) -> Dict[str, Any]:
        with h5py.File(path, 'r') as h5data:
            return {
                "name": path.stem.split("_proc")[0].split("l")[0],
                **{key: np.array(h5data[key]) for key in h5data.keys()}
            }

    def save(self, path: Path, data: Dict[str, Any]) -> None:
        """Save data to file"""
        if path.suffix.lower() == '.npz':
            np.savez(path, experiment=data)
        else:
            raise ValueError(f"Unsupported save format: {path.suffix}")