"""Data management and processing for Event Explorer"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import h5py

class DataManager:
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
        self.data_path: Optional[Path] = None

    def load_file(self, path: Path) -> None:
        """Load data from a file"""
        self.data_path = path
        if path.suffix.lower() == '.npz':
            self._load_npz(path)
        elif path.suffix.lower() in ['.h5', '.hdf5']:
            self._load_hdf5(path)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

    def _load_npz(self, path: Path) -> None:
        """Load data from NPZ file"""
        with np.load(path, allow_pickle=True) as data:
            self.data = data["experiment"][()]

    def _load_hdf5(self, path: Path) -> None:
        """Load data from HDF5 file"""
        with h5py.File(path, 'r') as h5data:
            self.data = {}
            # Load name from attributes if present, else from filename
            self.data["name"] = h5data.attrs.get('name', path.stem.split("_proc")[0].split("l")[0])
            
            def load_group(group, target_dict):
                for key in group.keys():
                    if isinstance(group[key], h5py.Group):
                        target_dict[key] = {}
                        load_group(group[key], target_dict[key])
                    else:
                        value = np.array(group[key])
                        if value.dtype.kind == 'S':  # Handle string data
                            value = value.astype(str)
                        target_dict[key] = value
                        
            load_group(h5data, self.data)

    def save_file(self, path: Path) -> None:
        """Save data to file"""
        if not self.data:
            raise ValueError("No data to save")
            
        if path.suffix.lower() == '.npz':
            np.savez(path, experiment=self.data)
        elif path.suffix.lower() in ['.h5', '.hdf5']:
            with h5py.File(path, 'w') as f:
                # Save name as attribute since HDF5 doesn't support string datasets well
                f.attrs['name'] = self.data.get('name', '')
                
                for key, value in self.data.items():
                    if key == 'name':
                        continue
                    if isinstance(value, (np.ndarray, list)):
                        f.create_dataset(key, data=np.array(value))
                    elif isinstance(value, (int, float)):
                        f.create_dataset(key, data=value)
                    elif isinstance(value, str):
                        f.create_dataset(key, data=np.string_(value))
                    elif isinstance(value, dict):
                        group = f.create_group(key)
                        for k, v in value.items():
                            if isinstance(v, (np.ndarray, list)):
                                group.create_dataset(k, data=np.array(v))
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

    def extract_events(self, indices: List[int], window_size: float) -> List[Dict]:
        """Extract events using provided indices"""
        if not self.data:
            raise ValueError("No data loaded")
            
        events = []
        for idx in indices:
            event = self._extract_single_event(idx, window_size)
            events.append(event)
        return events

    def _extract_single_event(self, idx: int, window: float) -> Dict:
        """Extract single event data"""
        event_time = self.data["time"][idx]
        
        idx_beg = np.argmin(np.abs(event_time - window - self.data["time"]))
        idx_end = np.argmin(np.abs(event_time + window - self.data["time"]))
        idx_event = range(idx_beg, idx_end + 1)
        
        event = {
            'event_time': event_time,
            'time': self.data['time'][idx_event]
        }
        
        for key, value in self.data.items():
            if key != "events" and isinstance(value, (np.ndarray, list)):
                try:
                    event[key] = value[idx_event]
                except IndexError:
                    event[key] = value[idx]
                    
        if 'strain' in self.data:
            event['strain'] = self._process_strain_data(event_time, window)
            
        return event

    def get_data(self, path: str) -> Any:
        """Get data at specified path"""
        if not self.data:
            raise ValueError("No data loaded")
            
        current = self.data
        for key in path.split('/'):
            if key[0] == '[' and key[-1] == ']':
                key = int(key[1:-1])
            current = current[key]
        return current

    def set_data(self, path: str, value: Any, add_key: bool = False) -> None:
        """Set data at specified path"""
        if not self.data:
            raise ValueError("No data loaded")
            
        parts = path.split('/')
        current = self.data
        
        for i, part in enumerate(parts[:-1]):
            if part[0] == '[' and part[-1] == ']':
                part = int(part[1:-1])
            
            if part not in current and add_key:
                current[part] = {} if i < len(parts) - 2 else None
            current = current[part]
            
        last_key = parts[-1]
        if last_key[0] == '[' and last_key[-1] == ']':
            last_key = int(last_key[1:-1])
        current[last_key] = value