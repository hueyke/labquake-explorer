"""Data processor for PSU experimental data."""

import numpy as np
import pandas as pd
from labquake_explorer.utils import cohesive_crack as CohesiveCrack

class DataProcessor:
    """
    Handles processing of experimental data from PSU.
    
    Attributes:
        raw_data (pd.DataFrame): Original experimental data
        processed_data (pd.DataFrame): Processed experimental data
    """
    
    def __init__(self, data_path=None):
        """
        Initialize DataProcessor.
        
        Args:
            data_path (str, optional): Path to the data file
        """
        self.raw_data = None
        self.processed_data = None
        
        if data_path:
            self.load_data(data_path)
    
    def load_data(self, data_path):
        """
        Load experimental data from a file.
        
        Args:
            data_path (str): Path to the data file
        """
        self.raw_data = pd.read_csv(data_path)
    
    def preprocess(self):
        """
        Perform initial data preprocessing.
        
        Raises:
            ValueError: If no data has been loaded
        """
        if self.raw_data is None:
            raise ValueError("No data loaded. Use load_data() first.")
        
        # Add preprocessing steps specific to PSU experimental data
        self.processed_data = self.raw_data.copy()
    
    def clean_data(self, remove_outliers=True):
        """
        Clean the processed data.
        
        Args:
            remove_outliers (bool): Whether to remove statistical outliers
        
        Returns:
            pd.DataFrame: Cleaned data
        """
        if self.processed_data is None:
            self.preprocess()
        
        # Implement data cleaning logic
        if remove_outliers:
            # Example outlier removal (modify as needed)
            for column in self.processed_data.select_dtypes(include=[np.number]).columns:
                Q1 = self.processed_data[column].quantile(0.25)
                Q3 = self.processed_data[column].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                self.processed_data = self.processed_data[
                    (self.processed_data[column] >= lower_bound) & 
                    (self.processed_data[column] <= upper_bound)
                ]
        
        return self.processed_data
    
    @staticmethod
    def voltage_to_strain(raw_voltage: float | np.ndarray[float]) -> float | np.ndarray[float]:
        """
        Convert raw voltage readings from a strain gauge circuit to strain.

        Args:
            raw_voltage (float): The measured voltage output from the Wheatstone bridge circuit (in volts).
            
        Constants:
            Vex  (float): Excitation voltage applied to the Wheatstone bridge (in volts). Default is 4.98 V.
            GF   (float): Gauge factor of the strain gauge (dimensionless). Default is 2.12.
            Rg   (float): Resistance of the strain gauge (in ohms). Default is 350 Ohm.
            Gain (float): Amplification factor of the signal (dimensionless). Default is 1000.
        
        Returns:
            float: Calculated strain (dimensionless).
        """
        Vex = 4.98    # Excitation voltage in volts
        GF = 2.12     # Gauge factor
        Rg = 350      # Resistance of strain gauge in ohms (not directly used)
        Gain = 1000   # Amplification factor
        
        strain = raw_voltage / Vex / Gain * 2 / GF
        return strain

    @staticmethod
    def shear_strain_to_stress(E: float, poisson_ratio: float, strain: float | np.ndarray[float]) -> float | np.ndarray[float]:
        """
        Calculate stress from shear strain by converting Young's modulus (E) to shear modulus (G).
        
        Args:
            E (float): Young's modulus (elastic modulus) in units of stress (e.g., Pa).
            poisson_ratio (float): Poisson's ratio (dimensionless).
            strain (float): Shear strain (dimensionless).
            
        Returns:
            float: Shear stress in the same units as Young's modulus.
        """
        G = E / (2 * (1 + poisson_ratio))
        stress = G * strain
        return stress
    
    @staticmethod
    def stress_to_strain(E: float, poisson_ratio: float, sigma_xx: float | np.ndarray[float], sigma_xy: float | np.ndarray[float], sigma_yy: float | np.ndarray[float]) -> float | np.ndarray[float]:
        """
        Calculate stress from shear strain by converting Young's modulus (E) to shear modulus (G).
        
        Args:
            E (float): Young's modulus (elastic modulus) in units of stress (e.g., Pa).
            poisson_ratio (float): Poisson's ratio (dimensionless).
            strain (float): Shear strain (dimensionless).
            
        Returns:
            float: Shear stress in the same units as Young's modulus.
        """
        epsilon_xx = (sigma_xx - poisson_ratio * sigma_yy) / E
        epsilon_yy = (sigma_yy - poisson_ratio * sigma_xx) / E
        epsilon_xy = (1 + poisson_ratio) / E * sigma_xy
        return epsilon_xx, epsilon_xy, epsilon_yy

    # @staticmethod
    # def highpass_filter(data, cutoff, fs, order=4):
    #     """
    #     Apply a highpass Butterworth filter to the data.
        
    #     Args:
    #         data: Input data to filter
    #         cutoff: Cutoff frequency
    #         fs: Sampling frequency
    #         order: Filter order (default=4)
            
    #     Returns:
    #         numpy.ndarray: Filtered data
    #     """
    #     nyquist = 0.5 * fs
    #     normal_cutoff = cutoff / nyquist
    #     b, a = scipy.signal.butter(order, normal_cutoff, btype='high', analog=False)
    #     filtered_data = scipy.signal.filtfilt(b, a, data)
    #     return filtered_data

    # @staticmethod
    # def fitting_function(X_c: float, C_f: float, Gamma: float, x: float | np.ndarray, y: float) -> float:
    #     """
    #     Cohesive zone model fitting function.
        
    #     Args:
    #         X_c (float): Critical distance
    #         C_f (float): Fracture speed
    #         Gamma (float): Fracture energy
    #         x (float | np.ndarray): Position
    #         y (float): y-coordinate
            
    #     Returns:
    #         float: Calculated stress
    #     """
    #     E = 51e9      # Young's modulus (Pa)
    #     nu = 0.25     # Poisson's ratio
    #     C_s = 2760    # Shear wave speed (m/s)
    #     C_d = 4790    # Longitudinal wave speed (m/s)
        
    #     return CohesiveCrack.delta_sigma_xy(x, y, X_c, C_f, C_s, C_d, nu, Gamma, E)