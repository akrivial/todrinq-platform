# import keras
# import numpy as np
# import pandas as pd
import tensorflow as tf

"""
Flow of the CoagFloc Model:
- initialize main table
- initialize dlvo calculator
- initialize collision calculator
- initialize breakage calculator
- initialize breakage probability calculator

"""


class DielectricConstantCalculator:

    def __init__(self, temperature):

        self.temperature = temperature

    def get_result(self):
        """
        Gets the dielectric constant for a given temperature. Looks it up from a talbe, and interprets intermediate input temperatures.
        Table obtained from Malmberg et al., J. Res. Natl. Bur. Stand. (U. S.), (1956), 56, 1
        # """
        look_up_table = tf.constant([
            87.740,
            85.763,
            83.832,
            81.946,
            80.103,
            78.304,
            76.546,
            74.828,
            73.151,
            71.512,
            69.910,
            68.345,
            66.815,
            65.319,
            63.857,
            62.427,
            61.027,
            59.659,
            58.319,
            57.007,
            55.720
        ], dtype=tf.float32)

        x_new = tf.cast(tf.range(101), tf.float32)
        n_ref = tf.cast(tf.shape(look_up_table)[0] - 1, tf.float32)
        pos = x_new / 100.0 * n_ref
        lower_idx = tf.clip_by_value(tf.cast(tf.floor(pos), tf.int32), 0, tf.shape(look_up_table)[0] - 2)
        upper_idx = lower_idx + 1
        alpha = pos - tf.cast(lower_idx, tf.float32)
        interpolated_lut = tf.gather(look_up_table, lower_idx) + alpha * (tf.gather(look_up_table, upper_idx) - tf.gather(look_up_table, lower_idx))

        look_up_index = tf.math.round(self.temperature)
        look_up_index = tf.cast(look_up_index, dtype=tf.int32)
        look_up_index = tf.where(look_up_index <= 0, 0, look_up_index)
        look_up_index = tf.where(look_up_index >= 100, 100, look_up_index)

        dielectric_constant = tf.gather(interpolated_lut, look_up_index)

        return dielectric_constant


class BjerrumLengthCalculator:

    def __init__(self, dielectric_constant, temperature):

        self.dielectric_constant_water = dielectric_constant
        self.temperature = temperature

        self.temperature = tf.where(self.temperature <= 0., 0., self.temperature)
        self.temperature = tf.where(self.temperature >= 100., 100., self.temperature)

        self.temperature += 273.15

        self.elementary_charge = 1.602E-19
        self.pi = 3.141592
        self.free_space_permittivity = 8.854E-12
        self.boltzmann_constant = 1.380649E-23

    def get_result(self):
        """
        Calculates the Bjerrum length
        """
        numerator = self.elementary_charge**2
        denominator = 4 * self.pi * self.free_space_permittivity * self.dielectric_constant_water * self.boltzmann_constant * self.temperature
        bjerrum_length = numerator / denominator
        return bjerrum_length


class DebyeLengthCalculator:

    def __init__(self,
                 dielectric_constant,
                 temperature,
                 salt_concentration):

        self.dielectric_constant_water = dielectric_constant
        self.temperature = temperature
        self.salt_concentration = salt_concentration

        self.temperature = tf.where(self.temperature <= 0., 0., self.temperature)
        self.temperature = tf.where(self.temperature >= 100., 100., self.temperature)
        self.temperature += 273.15
        self.salt_concentration = tf.where(self.salt_concentration <= 1.E-7, 1.E-7, self.salt_concentration)

        self.free_space_permittivity = 8.854E-12
        self.boltzmann_constant = 1.380649E-23
        self.elementary_charge = 1.602E-19
        self.avogadro_constant = 6.022E23

    def get_result(self):
        """
        Calculates the Debye length
        """
        numerator = self.free_space_permittivity * self.dielectric_constant_water * self.boltzmann_constant * self.temperature
        denominator = 2 * (self.elementary_charge)**2 * self.avogadro_constant * self.salt_concentration
        inverse_debye_length = (numerator / denominator)**(.5)
        return inverse_debye_length


class ColloidalChargeCalculator:

    def __init__(self,
                 dielectric_constant,
                 temperature,
                 salt_concentration,
                 zeta_potential):

        self.dielectric_constant = dielectric_constant
        self.salt_concentration = salt_concentration
        self.temperature = temperature
        self.zeta_potential = zeta_potential

        self.temperature = tf.where(self.temperature <= 0., 0., self.temperature)
        self.temperature = tf.where(self.temperature >= 100., 100., self.temperature)
        self.temperature += 273.15
        self.salt_concentration = tf.where(self.salt_concentration <= 1.E-7, 1.E-7, self.salt_concentration)
        self.zeta_potential = tf.where(self.zeta_potential <= 0., 0., self.zeta_potential)

        self.avogadro_constant = 6.022E23
        self.free_space_permittivity = 8.854E-12
        self.boltzmann_constant = 1.380649E-23
        self.elementary_charge = 1.602E-19

    def get_result(self):
        """
        Calculates the Bjerrum length
        """
        below_square_root = 8 * self.salt_concentration * self.avogadro_constant * \
            self.free_space_permittivity * self.dielectric_constant * \
            self.boltzmann_constant * self.temperature
        sinh_numerator = self.elementary_charge * self.zeta_potential
        sinh_denominator = 2 * self.boltzmann_constant * self.temperature
        sinh_term = sinh_numerator / sinh_denominator

        sinh_term = tf.where(sinh_term <= -50., -50., sinh_term)
        sinh_term = tf.where(sinh_term >= 50., 50., sinh_term)
        sinh_term = tf.where(tf.math.is_nan(sinh_term), 50., sinh_term)

        effective_surface_charge = (below_square_root)**.5 * tf.math.sinh(sinh_term)

        return effective_surface_charge


class CollisionEfficiencyCalculator:

    def __init__(self,
                 dielectric_constant,
                 temperature,
                 zeta_potential,
                 inverse_debye_length):

        self.dielectric_constant = dielectric_constant
        self.temperature = temperature
        self.zeta_potential = zeta_potential
        self.inverse_debye_length = inverse_debye_length

        self.temperature = tf.where(self.temperature <= 0., 0., self.temperature)
        self.temperature = tf.where(self.temperature >= 100., 100., self.temperature)
        self.temperature += 273.15

        self.zeta_potential = tf.where(self.zeta_potential <= 0., 0., self.zeta_potential)

        self.pi = 3.141592
        self.free_space_permittivity = 8.854E-12
        self.particle_diameter = 5.E-9
        self.boltzmann_constant = 1.380649E-23
        self.elementary_charge = 1.602E-19
        self.euler_number = 2.7182818
        self.hamaker_constant = 2.E-20

        self.distance_matrix = tf.linspace(
            5. * self.particle_diameter / 10000.,
            5. * self.particle_diameter,
            num=10000,
            axis=0)

    def get_yukawa(self):
        term1 = 64 * self.pi * self.free_space_permittivity * self.dielectric_constant
        term2 = self.particle_diameter / 4
        term3 = self.boltzmann_constant * self.temperature / self.elementary_charge
        term4 = tf.math.tanh(self.elementary_charge * self.zeta_potential / 4 / self.boltzmann_constant / self.temperature)
        term5 = self.euler_number**(-self.distance_matrix / self.inverse_debye_length)

        combined_preterms = term1 * term2 * term3**2 * term4**2
        full_yukawa = tf.reshape(combined_preterms, [-1, 1]) * term5
        return full_yukawa

    def get_vanderwaals(self):

        preconstant = self.hamaker_constant / 6
        term1_numerator = 2 * (self.particle_diameter / 2)**2
        term1_denominator = self.distance_matrix * ((2 * self.particle_diameter) + self.distance_matrix)
        term2_numerator = term1_numerator
        term2_denominator = (self.particle_diameter + self.distance_matrix)**2
        term3_numerator = term1_denominator
        term3_denominator = term2_denominator

        full_vanderWaals = - preconstant * (
            (term1_numerator / term1_denominator) +
            (term2_numerator / term2_denominator) +
            tf.math.log(term3_numerator / term3_denominator)
        )
        return full_vanderWaals

    def get_collision_efficiency(self, full_dlvo):

        """
        Wrapping method to get the collision efficiency according to the above DLVO theory. Gives a zero-dimensional collision efficiency.
        """

        first_column = tf.reshape(full_dlvo[:, 1] - full_dlvo[:, 0], (-1, 1))
        last_column = tf.reshape(full_dlvo[:, -1] - full_dlvo[:, -2], (-1, 1))
        intermediate_columns = (full_dlvo[:, 2:] - full_dlvo[:, :-2]) / 2

        complete_gradients = tf.concat([first_column, intermediate_columns, last_column], axis=1)
        negative_mask = tf.less(complete_gradients, 0.)
        first_negative_index = tf.argmax(tf.cast(negative_mask, tf.int32), axis=1)

        """
        De eigenlijke betere oplossing is als volgt. Omdat ik zeker wil weten dat ik de juiste max pak.
        driedimensionale tensor
        dimensie 1: input, dwz de zeven input parameters
        dimensie 2: range
        dimensie 3: x-2 x-1 x x+1 x+2
        tf.gather_nd(full_dlvo, driedimensionale tensor)
        """
        row_indices = tf.range(tf.shape(full_dlvo)[0], dtype=first_negative_index.dtype)
        indices_scalarized = tf.stack([row_indices, first_negative_index], axis=1)
        maximum_values = tf.gather_nd(full_dlvo, indices_scalarized)

        condition_mask = tf.less_equal(maximum_values, 0.)
        collision_efficiency_positive = self.euler_number ** (-maximum_values / self.boltzmann_constant / self.temperature)
        collision_efficiency_negative = tf.zeros(tf.shape(collision_efficiency_positive), dtype=tf.float32)

        collision_efficiency = tf.where(condition_mask,
                                        collision_efficiency_negative,
                                        collision_efficiency_positive
                                        )

        return collision_efficiency

    def get_result(self):

        yukawa = self.get_yukawa()
        vanderwaals = self.get_vanderwaals()
        full_dlvo = yukawa + vanderwaals
        collision_efficiency = self.get_collision_efficiency(full_dlvo)
        return collision_efficiency
