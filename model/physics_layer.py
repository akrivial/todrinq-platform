"""This file creates the PhysicsLayer class, which contains the physics-based
neural network layer.

This layer fits between two other tensorflow layers and calculates the physics-based
properties of the coagulation-flocculation process. The details of the model are
described in the report: BTO Coagulation-Flocculation by
Jasper Immink and Martin Korevaar.

The current layer only calculates the repulsive energy between two particles
as predicted by the DLVO theory.

To make sure neural-network based outputs can be ported into a physics-based model,
the PhysicsLayer has certain limits in place to force the inputs within a certain range.
It does this by a soft penalty to the loss function if these values are outside these limits.

This layer is called as a custom Keras layer, currently in use by physics_model_wrapper.py.
"""

import tensorflow as tf

from model.physics_models import \
    DielectricConstantCalculator, \
    BjerrumLengthCalculator, \
    DebyeLengthCalculator, \
    ColloidalChargeCalculator, \
    CollisionEfficiencyCalculator


@tf.keras.utils.register_keras_serializable()
class PhysicsLayer(tf.keras.layers.Layer):
    """Custom physics-based layer for calculating properties of coagulation-flocculation.

    PARAMETERS
    ----------
    units : int
        Number of input units for the layer. Default is 6.
    bins : int
        Number of bins for the population balance model. Default is 50.
        Currently not implemented.
    lower_limit_temperature : float
        Lower limit for the temperature input. Degrees celsius. Default is 5.0.
    upper_limit_temperature : float
        Upper limit for the temperature input. Degrees celsius. Default is 20.0.
    lower_limit_salt_concentration : float
        Lower limit for the salt concentration input. In units of mol per liter. Default is 1.e-7.
    upper_limit_salt_concentration : float
        Upper limit for the salt concentration input. In units of mol per liter. Default is 1.e-0.
    lower_limit_zetapotential : float
        Lower limit for the zeta potential input. In units of volts. Default is 0.
    upper_limit_zetapotential : float
        Upper limit for the zeta potential input. In units of volts. Default is 1.e-2.
    flag_couple_temperature : bool
        If True, the temperature input for the physics model is equal to
        the data input temperature. Default is True.
    name : str
        Name of the layer. Default is 'physics_layer'.

    EXAMPLE USAGE
    -------------
    multi_branch_output_1 = PhysicsLayer(units=6, flag_couple_temperature=flag_couple_temperature)([multi_branch_input, inputs])

    """

    def __init__(self,
                 units=6,
                 bins=50,
                 lower_limit_temperature=5.,
                 upper_limit_temperature=20.,
                 lower_limit_salt_concentration=1.e-7,
                 upper_limit_salt_concentration=1.e-0,
                 lower_limit_zetapotential=0.,
                 upper_limit_zetapotential=1.e-2,
                 flag_couple_temperature=True,
                 name='physics_layer',
                 **kwargs):

        super().__init__(**kwargs)
        self.units = units
        self.bins = bins
        self.name = name

        self.lower_limit_temperature = lower_limit_temperature
        self.upper_limit_temperature = upper_limit_temperature
        self.lower_limit_salt_concentration = lower_limit_salt_concentration
        self.upper_limit_salt_concentration = upper_limit_salt_concentration
        self.lower_limit_zetapotential = lower_limit_zetapotential
        self.upper_limit_zetapotential = upper_limit_zetapotential

        self.flag_couple_temperature = flag_couple_temperature

    def get_config(self):
        base_config = super().get_config()
        return {**base_config}

    @classmethod
    def from_config(cls, config):
        return cls(**config)

    def build(self, input_shape):

        w_init = tf.random_normal_initializer()
        self.w = self.add_weight(name=f"{self.name}_weights",
                                 initializer=w_init,
                                 shape=(input_shape[0][-1], self.units),
                                 dtype='float32',
                                 trainable=True)

        b_init = tf.zeros_initializer()
        self.b = self.add_weight(name=f"{self.name}_biases",
                                 initializer=b_init,
                                 shape=(self.units,),
                                 dtype='float32',
                                 trainable=True)

    def upper_loss(self, temperature_value, upper_limit):
        return tf.nn.relu(temperature_value - upper_limit) ** 2.

    def lower_loss(self, temperature_value, lower_limit):
        return tf.nn.relu(lower_limit - temperature_value) ** 2.

    def combined_loss(self, temperature_value, lower_limit, upper_limit):
        lower_loss_value = self.lower_loss(temperature_value, lower_limit)
        upper_loss_value = self.upper_loss(temperature_value, upper_limit)
        return lower_loss_value + upper_loss_value

    def call(self, inputs_combined):
        """
        The inputs are ported to the layer, and the unit that corresponds to
        the specific physics value is as follows:
        training_results[:, 0] == temperature (optionally)
        training_results[:, 1] == salt_concentration
        training_results[:, 2] == zeta_potential
        """

        inputs = inputs_combined[0]

        training_results = tf.matmul(inputs, self.w) + self.b
        self.training_results = training_results

        if self.flag_couple_temperature:
            temperature = inputs_combined[1][:, 1]
        else:
            temperature = training_results[:, 0]

        self.add_loss(self.combined_loss(training_results[:, 0],
                                         self.lower_limit_temperature,
                                         self.upper_limit_temperature)
                      )
        self.add_loss(self.combined_loss(training_results[:, 1],
                                         self.lower_limit_salt_concentration,
                                         self.upper_limit_salt_concentration)
                      )
        self.add_loss(self.combined_loss(training_results[:, 2],
                                         self.lower_limit_zetapotential,
                                         self.upper_limit_zetapotential)
                      )
        # tf.print("Contribution temperature")

        dielectric_calculator = DielectricConstantCalculator(temperature)
        dielectric_results = dielectric_calculator.get_result()
        dielectric_results = tf.reshape(dielectric_results, [-1, 1])
        # output = dielectric_results
        # output = tf.concat([training_results, dielectric_results], axis=1)

        bjerrum_calculator = BjerrumLengthCalculator(dielectric_results[:, 0], temperature)
        bjerrum_length = bjerrum_calculator.get_result()
        bjerrum_length = tf.reshape(bjerrum_length, [-1, 1])
        # output = tf.concat([output, bjerrum_length], axis=1)

        debye_calculator = DebyeLengthCalculator(dielectric_results[:, 0], temperature, training_results[:, 1])
        inverse_debye_length = debye_calculator.get_result()
        inverse_debye_length = tf.reshape(inverse_debye_length, [-1, 1])
        # output = tf.concat([output, inverse_debye_length], axis=1)

        colloidal_charge_calculator = ColloidalChargeCalculator(dielectric_results[:, 0], temperature, training_results[:, 1], training_results[:, 2])
        colloidal_charge = colloidal_charge_calculator.get_result()
        colloidal_charge = tf.reshape(colloidal_charge, [-1, 1])
        output = colloidal_charge
        # output = tf.concat([output, colloidal_charge], axis=1)

        collision_efficiency_calculator = CollisionEfficiencyCalculator(dielectric_results[:, 0], temperature, training_results[:, 2], inverse_debye_length)
        collision_efficiency = collision_efficiency_calculator.get_result()
        collision_efficiency = tf.reshape(collision_efficiency, [-1, 1])
        output = tf.concat([output, collision_efficiency], axis=1)

        # tf.print(output)

        return output

@tf.keras.utils.register_keras_serializable()
class ModifiedBatchNormalization(tf.keras.layers.BatchNormalization):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def build(self, input_shape):
        super().build(input_shape)

    def call(self, inputs):
        # tf.print('\n')
        # tf.print(tf.shape(inputs))
        # tf.print(inputs)
        output = super().call(inputs)
        # tf.print('\n')
        # tf.print(tf.shape(output))
        # tf.print(output)
        return output
