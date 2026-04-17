"""Submodules for the physics layer of the Coagulation flocculation hybrid model.

All modules are based on DLVO theory and will calculate probability of the collision
between two particles leading to an aggregation event.

Contains classes for calculating:
- Dielectric constant
- Bjerrum length
- Debye length
- Colloidal charge
- Collision efficiency "plakkans"
"""

import tensorflow as tf

class DielectricConstantCalculator:
    """
    Gets the dielectric constant for a given temperature. Looks it up from a talbe, and interprets intermediate input temperatures.
    Table obtained from Malmberg et al., J. Res. Natl. Bur. Stand. (U. S.), (1956), 56, 1
    """

    def __init__(self, temperature):

        self.temperature = temperature

    def get_result(self):
        interpolated_lut = tf.constant([
            87.73999786,
            87.34459839,
            86.94919891,
            86.55379944,
            86.15839996,
            85.76300049,
            85.37680054,
            84.99060059,
            84.60440063,
            84.21820068,
            83.83200073,
            83.45480042,
            83.0776001,
            82.70039978,
            82.32319946,
            81.94599915,
            81.57739868,
            81.20879822,
            80.84019775,
            80.47159729,
            80.10299683,
            79.74319763,
            79.38339844,
            79.02359924,
            78.66380005,
            78.30400085,
            77.95240021,
            77.60079956,
            77.24919891,
            76.89759827,
            76.54599762,
            76.20239868,
            75.85879974,
            75.51520081,
            75.17160187,
            74.82800293,
            74.49260254,
            74.15720215,
            73.82180176,
            73.48640137,
            73.15100098,
            72.82320099,
            72.495401,
            72.16760101,
            71.83980103,
            71.51200104,
            71.19160156,
            70.87120209,
            70.55080261,
            70.23040314,
            69.91000366,
            69.59700317,
            69.28400269,
            68.9710022,
            68.65800171,
            68.34500122,
            68.03900146,
            67.73300171,
            67.42700195,
            67.1210022,
            66.81500244,
            66.515802,
            66.21660156,
            65.91740112,
            65.61820068,
            65.31900024,
            65.02659988,
            64.73419952,
            64.44179916,
            64.1493988,
            63.85699844,
            63.57099838,
            63.28499832,
            62.99899826,
            62.7129982,
            62.42699814,
            62.1469986,
            61.86699905,
            61.58699951,
            61.30699997,
            61.02700043,
            60.75340042,
            60.47980042,
            60.20620041,
            59.9326004,
            59.6590004,
            59.39100037,
            59.12300034,
            58.85500031,
            58.58700027,
            58.31900024,
            58.05660019,
            57.79420013,
            57.53180008,
            57.26940002,
            57.00699997,
            56.74960022,
            56.49220047,
            56.23480072,
            55.97740097,
            55.72000122
        ], dtype=tf.float32)

        look_up_index = tf.math.round(self.temperature)
        look_up_index = tf.cast(look_up_index, dtype=tf.int32)
        look_up_index = tf.where(look_up_index <= 0, 0, look_up_index)
        look_up_index = tf.where(look_up_index >= 100, 100, look_up_index)

        dielectric_constant = tf.gather(interpolated_lut, look_up_index)

        return dielectric_constant


class BjerrumLengthCalculator:
    """Calculates the Bjerrum length based on the dielectric constant and temperature.

    The Bjerrum length is the distance at which the electrostatic
    interaction between two charges is comparable to the thermal energy.
    """

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
    """Calculates the Debye length based on the dielectric constant, temperature, and salt concentration.

    The Debye length is a measure of a charge carrier's net electrostatic effect in a medium.
    """

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
    """Calculates the effective surface charge of a colloidal particle.

    The effective surface charge is a measure of the zeta potential and
    is affected by the ionic strength of the medium.
    """

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
    """Calculates the probability that two particles that collide, aggregate.

    Wraps all the above functions together and calculates the height
    of the energy barrier for aggregation. Then, use the Arrhenius equation
    to calculate the collision efficiency given that there are only
    thermal energetic forces causing aggregation.
    
    This latter assumption is incorrect, as kinetic energy is probably more dominant
    in causing aggregation. This is a point for expansion, also in the coagulation-
    flocculation model from the BTO.
    """

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
        Wrapping method to get the collision efficiency according to the above DLVO theory.
        Gives a zero-dimensional collision efficiency.
        """

        first_column = tf.reshape(full_dlvo[:, 1] - full_dlvo[:, 0], (-1, 1))
        last_column = tf.reshape(full_dlvo[:, -1] - full_dlvo[:, -2], (-1, 1))
        intermediate_columns = (full_dlvo[:, 2:] - full_dlvo[:, :-2]) / 2

        complete_gradients = tf.concat([first_column, intermediate_columns, last_column], axis=1)
        negative_mask = tf.less(complete_gradients, 0.)
        first_negative_index = tf.argmax(tf.cast(negative_mask, tf.int32), axis=1)

        """
        Een betere oplossing is als volgt. Omdat ik zeker wil weten dat ik de juiste max pak.
        Uitkomst: driedimensionale tensor
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
