"""Event processing for Event Explorer"""
import h5py
import numpy as np
import utils.tpc5 as tpc5
from typing import Dict, Any, List
from pathlib import Path

class EventProcessor:
    def extract_events(self, data: Dict[str, Any], indices: List[int], window: float) -> List[Dict]:
        """Extract events from data"""
        events = []
        for idx in indices:
            event = self._extract_single_event(data, idx, window)
            events.append(event)
        return events

    def _extract_single_event(self, data: Dict[str, Any], idx: int, window: float) -> Dict:
        """Extract single event data"""
        event = {}
        event_time = data["time"][idx]
        
        idx_beg = np.argmin(np.abs(event_time - window - data["time"]))
        idx_end = np.argmin(np.abs(event_time + window - data["time"]))
        idx_event = range(idx_beg, idx_end + 1)
        
        event['event_time'] = event_time
        event['time'] = data['time'][idx_event]
        
        # Extract measurements
        for key, value in data.items():
            if key != "events" and isinstance(value, (np.ndarray, list)):
                try:
                    event[key] = value[idx_event]
                except IndexError:
                    event[key] = value[idx]
        
        # Process strain data if available
        if 'strain' in data:
            event['strain'] = self._process_strain_data(data, event_time, window)
            
        return event

    def _process_strain_data(self, data: Dict[str, Any], event_time: float, window: float) -> Dict:
        """Process strain data for event"""
        strain_data = {}
        with h5py.File(data['strain']['filename'], 'r') as f:
            n_channels = tpc5.getNChannels(f)
            sampling_rate = tpc5.getSampleRate(f, 1, 1)
            trigger_sample = tpc5.getTriggerSample(f, 1, 1)
            
            time_range = self._calculate_time_range(f, trigger_sample, sampling_rate)
            strain_data = self._extract_strain_measurements(
                f, time_range, event_time, window, n_channels
            )
            
        return strain_data

    def get_data_at_path(self, data: Dict[str, Any], path: str) -> Any:
        """Get data at specified path"""
        current = data
        for key in path.split('/'):
            if key[0] == '[' and key[-1] == ']':
                key = int(key[1:-1])
            current = current[key]
        return current

    def set_data_at_path(self, data: Dict[str, Any], path: str, value: Any, add_key: bool = False) -> None:
        """Set data at specified path"""
        parts = path.split('/')
        current = data
        
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