"""Event processing for Labquake Explorer"""
import h5py
import numpy as np
from labquake_explorer.utils import tpc5
from typing import Dict, Any, List, Optional
from pathlib import Path

class EventProcessor:
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path

    def set_data_path(self, data_path: Path) -> None:
        """Set the base path for resolving relative file paths"""
        self.data_path = data_path

    def extract_events(self, run_data: Dict[str, Any], event_indices: List[int], window: float) -> List[Dict]:
        """Extract events from run data using provided indices and time window
        
        Args:
            run_data: Dictionary containing run data including strain data
            event_indices: List of indices marking event locations
            window: Time window size (in seconds) before and after each event
            
        Returns:
            List of extracted event dictionaries
        """
        events = []
        for i, idx in enumerate(event_indices):
            event = {}
            event_time = run_data["time"][idx]
            
            # Extract time window around event
            idx_beg = np.argmin(np.abs(event_time - window - run_data["time"]))
            idx_end = np.argmin(np.abs(event_time + window - run_data["time"]))
            idx_event = range(idx_beg, idx_end + 1)
            
            # Store basic event info
            event['event_time'] = event_time
            event['time'] = run_data['time'][idx_event]

            try:
                # Store mechanical data
                mechanical_fields = [
                    'normal_stress', 'shear_stress', 'friction',
                    'LP_displacement', 'LP_velocity', 'displacement'
                ]
                
                for field in mechanical_fields:
                    if field in run_data:
                        event[field] = run_data[field][idx_event]

                # Handle strain data if available
                if 'strain' in run_data:
                    event['strain'] = self._process_strain_data(
                        run_data, event_time, window, idx_event
                    )

            except Exception as e:
                print(f"Warning: Error processing event {i}: {str(e)}")
                # Fallback: store all available array data for this index
                for key in run_data:
                    if key == "events":
                        continue
                    if isinstance(run_data[key], (np.ndarray, list)):
                        try:
                            event[key] = run_data[key][idx_event]
                        except IndexError:
                            event[key] = run_data[key][idx]
            
            events.append(event)
        
        return events

    def _process_strain_data(self, run_data: Dict[str, Any], event_time: float, 
                           window: float, idx_event: range) -> Dict[str, Any]:
        """Process strain data for a single event"""
        if self.data_path is None:
            raise ValueError("Data path not set. Call set_data_path() first.")
            
        # Resolve the strain file path relative to the data file path
        strain_file = self.data_path.parent / run_data['strain']['filename']
        with h5py.File(strain_file, 'r') as f:
            n_channels = tpc5.getNChannels(f)
            n_samples = tpc5.getNSamples(f, 1)
            trigger_sample = tpc5.getTriggerSample(f, 1, 1)
            sampling_rate = tpc5.getSampleRate(f, 1, 1)
            
            # Calculate time series
            start_time = -trigger_sample / sampling_rate
            end_time = (n_samples - trigger_sample) / sampling_rate
            ts = np.arange(start_time, end_time, 1/sampling_rate)
            ts += run_data['strain']['time_offset'] + run_data['time'][0] - ts[0]

            # Get indices for time window
            time_before = event_time - window
            time_after = event_time + window
            idx_before = np.argmin(np.abs(ts - time_before))
            idx_after = np.argmin(np.abs(ts - time_after))
            tt = ts[idx_before:idx_after]
            
            # Extract strain data
            y = np.zeros((n_channels, len(tt)))
            for j in range(n_channels):
                y[j, :] = tpc5.getVoltageData(f, j + 1)[idx_before:idx_after]
                y[j, :] -= y[j, 0:int(y.shape[1] / 100)].mean()
            
            # Return formatted strain data
            return {
                'filename_downsampled': run_data['strain'].get('filename_downsampled', ''),
                'filename': run_data['strain']['filename'],
                'time': run_data['time'][0] + run_data['strain']['time_offset'] + 
                       run_data['strain']['time'][idx_event],
                'raw': run_data['strain']['raw'][:, idx_event],
                'original': {
                    'time': tt,
                    'raw': y
                }
            }

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