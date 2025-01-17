import numpy as np
import scipy.signal

from src import cohesive_crack as CohesiveCrack

def voltage_to_strain(raw_voltage: float|np.ndarray[float]) -> float|np.ndarray[float]:
    '''
    Convert raw voltage readings from a strain gauge circuit to strain.

    The function assumes a Wheatstone bridge circuit with a strain gauge 
    and uses the following relationship:
    
    strain = (raw_voltage / Vex / Gain) * (2 / GF)
    
    Args:
        raw_voltage (float): The measured voltage output from the Wheatstone bridge circuit (in volts).
        
    Constants:
        Vex  (float): Excitation voltage applied to the Wheatstone bridge (in volts). Default is 4.98 V.
        GF   (float): Gauge factor of the strain gauge (dimensionless). Default is 2.12.
        Rg   (float): Resistance of the strain gauge (in ohms). Default is 350 Ohm.
        Gain (float): Amplification factor of the signal (dimensionless). Default is 1000.
    
    Returns:
        float: Calculated strain (dimensionless).
    
    Example:
        >>> voltage_to_strain(0.002)
        1.9178082191780822e-06
    '''
    Vex = 4.98    # Excitation voltage in volts
    GF = 2.12     # Gauge factor
    Rg = 350      # Resistance of strain gauge in ohms (not directly used)
    Gain = 1000   # Amplification factor
    
    strain = raw_voltage / Vex / Gain * 2 / GF
    
    return strain


def shear_strain_to_stress(E: float, poisson_ratio: float, strain: float|np.ndarray[float]) -> float|np.ndarray[float]:
    '''
    Calculate stress from shear strain by converting Young's modulus (E) to shear modulus (G).
    
    Args:
        E (float): Young's modulus (elastic modulus) in units of stress (e.g., Pa).
        strain (float): Shear strain (dimensionless).
        poisson_ratio (float): Poisson's ratio (dimensionless).
        
    Returns:
        float: Shear stress in the same units as Young's modulus.
    '''
    
    G = E / (2 * (1 + poisson_ratio))
    stress = G * strain
    
    return stress

def highpass_filter(data, cutoff, fs, order=4):
    nyquist = 0.5 * fs
    normal_cutoff = cutoff / nyquist
    b, a = scipy.signal.butter(order, normal_cutoff, btype = 'high', analog=False)
    filtered_data = scipy.signal.filtfilt(b, a, data)
    return filtered_data

def fitting_function(X_c: float, C_f: float, Gamma: float, x: float|np.ndarray, y:float) -> float:
    
    # Gamma = 0.21  # Fracture energy (J/m^2)
    E = 51e9      # Young's modulus (Pa)
    nu = 0.25     # Poisson's ratio
    C_s = 2760    # Shear wave speed (m/s)
    C_d = 4790    # Longitudinal wave speed (m/s)
    
    return CohesiveCrack.delta_sigma_xy(x, y, X_c, C_f, C_s, C_d, nu, Gamma, E)

def chi_square(X_c: float, Gamma: float, C_f: float, X: np.ndarray, Y: np.ndarray):
    '''
    X_c and Gamma are the parameters to be fitted
    '''
    MODEL = fitting_function(X_c, C_f, Gamma, X, Y) / 10**6
    
    # chi2 = sum( (data_i - model_i)^2 / sigma_i^2 )
    chi2 = np.sum((Y - MODEL)**2)
    return chi2