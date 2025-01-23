"""Data processor for PSU experimental data."""

import numpy as np
import pandas as pd

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