"""Data management and processing for Labquake Explorer"""
from pathlib import Path
from typing import Dict, Any, Optional, List
import numpy as np
import h5py
from labquake_explorer.data.event_processor import EventProcessor


class DataManager:
    def __init__(self):
        self.data: Optional[Dict[str, Any]] = None
        self.data_path: Optional[Path] = None
        self.data: Optional[Dict[str, Any]] = None
        self.event_processor = EventProcessor()

    def load_file(self, path: Path) -> None:
        """Load data from a file"""
        self.data_path = path
        self.event_processor.set_data_path(path)  # Set the data path in EventProcessor

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
        with h5py.File(path, 'r') as h5data:
            def load_dataset(item):
                try:
                    data = np.array(item)
                    if data.dtype.kind == 'S' or data.dtype.kind == 'O':
                        if isinstance(data.flat[0], bytes):
                            if data.size == 1:
                                return data.flat[0].decode('utf-8')
                            return [x.decode('utf-8') for x in data.flat]
                    if data.size == 1:  # Convert length-1 arrays to numbers
                        return data.item()
                    return data
                except Exception as exc:
                    print(f"Dataset loading error: {str(exc)}")
                    return None
                
            def load_group(group):
                result = {}
                
                keys = list(group.keys())
                if all(k.isdigit() for k in keys):  # Check if all keys are integers
                    try:
                        num_keys = max(int(k) for k in keys) + 1
                        return np.array([load_group(group[str(i)]) for i in range(num_keys)])
                    except ValueError:
                        pass  # Fall back to dictionary if an error occurs
                    
                for key in keys:
                    try:
                        item = group[key]
                        if isinstance(item, h5py.Group):
                            result[key] = load_group(item)
                        else:
                            result[key] = load_dataset(item)
                    except Exception as exc:
                        print(f"Error loading {key}: {str(exc)}")
                
                return result

    def save_file(self, path: Path) -> None:
        if not self.data:
            raise ValueError("No data to save")
    
        if path.suffix.lower() == '.npz':
            np.savez(path, experiment=self.data)
        elif path.suffix.lower() in ['.h5', '.hdf5']:
            with h5py.File(path, 'w') as f:
                def save_item(group, key, value):
                    if isinstance(value, dict):
                        subgroup = group.create_group(key)
                        for k, v in value.items():
                            save_item(subgroup, k, v)
                    elif isinstance(value, np.ndarray):
                        # Ensure 2D arrays are stored as matrices
                        if value.ndim == 2:  # This ensures any 2D array (e.g., (16, n)) is stored correctly
                            group.create_dataset(key, data=value, compression="gzip")
                        else:
                            arr = np.array(value)
                            if arr.dtype == object:
                                if all(isinstance(x, (int, np.integer)) for x in arr.flat):
                                    arr = arr.astype(np.int64)
                                elif all(isinstance(x, (float, np.floating)) for x in arr.flat):
                                    arr = arr.astype(np.float64)
                                elif all(isinstance(x, bool) for x in arr.flat):
                                    arr = arr.astype(np.int8)
                                else:
                                    arr = np.array([str(x).encode() for x in arr.flat]).reshape(arr.shape)
                            elif arr.dtype.kind == 'U':  # Convert Unicode strings to byte strings
                                arr = np.array([x.encode() for x in arr.flat]).reshape(arr.shape)
                
                            group.create_dataset(key, data=arr, compression="gzip")
                    elif isinstance(value, (list, tuple)):
                        # Convert list/tuple to NumPy array and save if it's 2D
                        arr = np.array(value)
                        if arr.ndim == 2:  # Save lists that are actually 2D arrays
                            group.create_dataset(key, data=arr, compression="gzip")
                        else:
                            subgroup = group.create_group(key)
                            for i, item in enumerate(value):
                                save_item(subgroup, str(i), item)
                    elif isinstance(value, str):
                        group.create_dataset(key, data=value.encode())
                    elif isinstance(value, (int, float, bool, np.number)):
                        group.create_dataset(key, data=value)
                    else:
                        try:
                            group.create_dataset(key, data=np.array(value), compression="gzip")
                        except (ValueError, TypeError) as e:
                            print(f"Warning: Could not save {key}: {e}")
    
                for k, v in self.data.items():
                    save_item(f, k, v)

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
        if not path:  # Handle empty path
            return current
        if not self.data:
            raise ValueError("No data loaded")
        parts = [p for p in path.split('/') if p]  # Split and filter out empty parts
        current = self.data
        for key in parts:
            if key.startswith('[') and key.endswith(']'):
                key = int(key[1:-1])  # Convert list index to integer
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
            current = current[part]
            
        last_key = parts[-1]
        if last_key[0] == '[' and last_key[-1] == ']':
            last_key = int(last_key[1:-1])
        current[last_key] = value

    def delete_data(self, path: str) -> None:
        """Delete data at specified path
        
        Args:
            path: Path to the data to delete (e.g. 'runs/[0]/events')
            
        Raises:
            ValueError: If no data is loaded or path is invalid
            KeyError: If path does not exist
        """
        if not self.data:
            raise ValueError("No data loaded")
            
        # Handle root deletion
        if path == "":
            self.data = None
            return
            
        parts = path.split('/')
        current = self.data
        
        # Navigate to parent of item to delete
        for part in parts[:-1]:
            if part[0] == '[' and part[-1] == ']':
                # Handle array index
                idx = int(part[1:-1])
                if not isinstance(current, (list, tuple)):
                    raise ValueError(f"Cannot index non-sequence with {part}")
                if idx >= len(current):
                    raise IndexError(f"Index {idx} out of range for sequence of length {len(current)}")
                current = current[idx]
            else:
                # Handle dictionary key
                if not isinstance(current, dict):
                    raise ValueError(f"Cannot get key '{part}' from non-dictionary")
                if part not in current:
                    raise KeyError(f"Key '{part}' not found")
                current = current[part]
        
        # Delete the item
        last_part = parts[-1]
        if last_part[0] == '[' and last_part[-1] == ']':
            # Handle array index deletion
            idx = int(last_part[1:-1])
            if not isinstance(current, (list, tuple)):
                raise ValueError(f"Cannot delete index from non-sequence")
            if idx >= len(current):
                raise IndexError(f"Index {idx} out of range")
            current.pop(idx)
        else:
            # Handle dictionary key deletion
            if not isinstance(current, dict):
                raise ValueError(f"Cannot delete key from non-dictionary")
            if last_part not in current:
                raise KeyError(f"Key '{last_part}' not found")
            current.pop(last_part)