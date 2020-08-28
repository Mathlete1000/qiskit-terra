# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2020.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests Uhrig Dynamical Decoupling (UDD) Pass"""

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import UDDPass
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeAlmaden
from numpy import pi, sin

class TestUDD(QiskitTestCase):
    """Test the UDD pass."""

    def setUp(self):
        self.backend = FakeAlmaden()
        self.backend_prop = self.backend.properties()
        self.gate_length = self.backend_prop._gates['u3'][(0,)]['gate_length'][0]

    def test_udd_2(self):
        """Test that the pass replaces large enough delay blocks with UDD_2 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(5e-7, 0, unit='s')
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(UDDPass(2, self.backend_prop))
        actual = pass_manager.run(circuit)

        tau_step_total = 4e-7 - 2 * self.gate_length

        t_i = [tau_step_total * (sin(pi * i / 6)) ** 2 for i in range(4)]

        tau_steps = [t_i[i] - t_i[i-1] for i in range(1, 4)]

        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(5e-8, 0, unit='s')
        expected.delay(tau_steps[0], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[1], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[2], 0, unit='s')
        expected.delay(5e-8, 0, unit='s')
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_udd_3(self):
        """Test that the pass replaces large enough delay blocks with UDD_3 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.delay(8e-7, 0, unit='s')
        circuit.h(0)
        circuit.delay(6e-7, 0, unit='s')
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(UDDPass(3, self.backend_prop))
        actual = pass_manager.run(circuit)

        tau_step_total = 6e-7 - 3 * self.gate_length

        t_i = [tau_step_total * (sin(pi * i / 8)) ** 2 for i in range(5)]

        tau_steps = [t_i[i] - t_i[i-1] for i in range(1, 5)]

        expected = QuantumCircuit(1)
        expected.delay(8e-7, 0, unit='s')
        expected.h(0)
        expected.delay(tau_steps[0], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[1], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[2], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[3], 0, unit='s')
        expected.h(0)

        self.assertEqual(actual, expected)

    def test_udd_4(self):
        """Test that the pass replaces large enough delay blocks with UDD_4 sequences.
        """
        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(1e-7, 0, unit='s')
        circuit.x(0)
        circuit.delay(8e-7, 0, unit='s')
        circuit.h(0)

        pass_manager = PassManager()
        pass_manager.append(UDDPass(4, self.backend_prop))
        actual = pass_manager.run(circuit)

        tau_step_total = 8e-7 - 4 * self.gate_length

        t_i = [tau_step_total * (sin(pi * i / 10)) ** 2 for i in range(6)]

        tau_steps = [t_i[i] - t_i[i-1] for i in range(1, 6)]
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(1e-7, 0, unit='s')
        expected.x(0)
        expected.delay(tau_steps[0], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[1], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[2], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[3], 0, unit='s')
        expected.u3(pi, pi/2, pi/2, 0)
        expected.delay(tau_steps[4], 0, unit='s')
        expected.h(0)

        self.assertEqual(actual, expected)
