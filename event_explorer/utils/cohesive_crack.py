"""Cohesive crack analytical calculations module."""
import numpy as np
import matplotlib.pyplot as plt

class CohesiveCrack:
    """
    Analytical calculations for cohesive crack models.
    
    Attributes:
        params (dict): Configuration parameters for cohesive crack analysis
    """
    
    def __init__(self, params=None):
        """
        Initialize CohesiveCrack with default or provided parameters.
        
        Args:
            params (dict, optional): Configuration parameters
        """
        self.default_params = {
            'Gamma': 0.21,   # Fracture energy (J/m^2)
            'E': 51e9,       # Young's modulus (Pa)
            'nu': 0.25,      # Poisson's ratio
            'C_f': 2404,     # Rupture speed (m/s)
            'C_s': 2760,     # Shear wave speed (m/s)
            'C_d': 4790,     # Longitudinal wave speed (m/s)
            'X_c': 13.8e-3   # Cohesive zone size (m)
        }
        self.params = {**self.default_params, **(params or {})}
    
    def alpha_s(self, C_f, C_s):
        return np.sqrt(1 - (C_f / C_s) ** 2)

    def alpha_d(self, C_f, C_d):
        return np.sqrt(1 - (C_f / C_d) ** 2)

    def D(self, alpha_s, alpha_d):
        return 4 * alpha_s * alpha_d - (1 + alpha_s ** 2) ** 2

    def compute_A2(self, C_f, C_s, nu, D_value):
        alpha_s_value = self.alpha_s(C_f, C_s)
        psfactor = 1 / (1 - nu)
        return (C_f ** 2 * alpha_s_value * psfactor) / (C_s ** 2 * D_value)

    def compute_K2(self, Gamma, E, nu, A2):
        return np.sqrt((Gamma * E) / ((1 - nu ** 2) * A2))

    def compute_tau_p(self, K2, X_c):
        return K2 * np.sqrt(9 * np.pi / (32 * X_c))

    def delta_sigma_xy(self, x, y, X_c=None, C_f=None, C_s=None, C_d=None, nu=None, Gamma=None, E=None):
        # Use provided parameters or fall back to default
        X_c = X_c or self.params['X_c']
        C_f = C_f or self.params['C_f']
        C_s = C_s or self.params['C_s']
        C_d = C_d or self.params['C_d']
        nu = nu or self.params['nu']
        Gamma = Gamma or self.params['Gamma']
        E = E or self.params['E']

        alpha_s_value = self.alpha_s(C_f, C_s)
        alpha_d_value = self.alpha_d(C_f, C_d)
        D_value = self.D(alpha_s_value, alpha_d_value)
        A2 = self.compute_A2(C_f, C_s, nu, D_value)
        K2 = self.compute_K2(Gamma, E, nu, A2)
        tau_p = self.compute_tau_p(K2, X_c)
        
        z_d_value = x + 1j * alpha_d_value * y
        z_s_value = x + 1j * alpha_s_value * y
        
        M_z_d = self._M_of_z(tau_p, X_c, z_d_value)
        M_z_s = self._M_of_z(tau_p, X_c, z_s_value)
        
        Sxx_tmp, Syy_tmp, Sxy_tmp = self._compute_stress_components(M_z_d, M_z_s, alpha_s_value, alpha_d_value)
        
        Sxx, Syy, Sxy = self._compute_stresses(Sxx_tmp, Syy_tmp, Sxy_tmp, alpha_s_value, D_value)
        
        return Sxy

    def plot_stress_fluctuation(self, output_path='./Plot/example_xx.pdf', stress_func=None):
        """
        Plot stress fluctuation with configurable parameters and output function
        
        Args:
            output_path (str): Path to save the output plot
            stress_func (callable): Function to compute stress fluctuation
        """
        stress_func = stress_func or self.delta_sigma_xy
        y_values = [1e-8, 0.1e-3, 0.5e-3, 1.0e-3, 2.0e-3, 5e-3, 10e-3, 15e-3]

        x = np.linspace(-50e-3, 50e-3, 8192)

        plt.figure(figsize=(8, 6))
        for i, y in enumerate(y_values):
            delta_sigma = stress_func(x, y)
            plt.plot(x * 1000, delta_sigma / 1e5 + i * 5, '-.', label=f'y = {y * 1e3:.1f} mm')

        plt.xlabel('Rupture tip position x (mm)')
        plt.ylabel('Stress fluctuation (MPa)')
        plt.title('Stress fluctuation along the fault')
        plt.axvline(0, color='k', linestyle='--', linewidth=1)
        plt.legend()
        plt.grid()
        plt.tight_layout()
        plt.savefig(output_path, dpi=900)
        plt.close()

    def _M_of_z(self, tau_p, X_c, z):
        return (2 / np.pi) * tau_p * ((1 + z / X_c) * np.arctan(1 / np.sqrt(z / X_c)) - np.sqrt(z / X_c))

    def _compute_stress_components(self, M_z_d, M_z_s, alpha_s_value, alpha_d_value):
        Sxx_tmp = (1 + 2 * alpha_d_value ** 2 - alpha_s_value ** 2) * M_z_d - (1 + alpha_s_value ** 2) * M_z_s
        Syy_tmp = M_z_d - M_z_s
        Sxy_tmp = 4 * alpha_s_value * alpha_d_value * M_z_d - (1 + alpha_s_value ** 2) ** 2 * M_z_s
        return Sxx_tmp, Syy_tmp, Sxy_tmp

    def _compute_stresses(self, Sxx_tmp, Syy_tmp, Sxy_tmp, alpha_s_value, D_value):
        Sxx = 2 * alpha_s_value / D_value * Sxx_tmp.imag
        Syy = -2 * alpha_s_value * (1 + alpha_s_value ** 2) / D_value * Syy_tmp.imag
        Sxy = Sxy_tmp.real / D_value
        return Sxx, Syy, Sxy

def main():
    """Example usage of CohesiveCrack"""
    crack = CohesiveCrack()
    crack.plot_stress_fluctuation()

if __name__ == "__main__":
    main()