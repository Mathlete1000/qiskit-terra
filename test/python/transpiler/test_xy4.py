# -*- coding: utf-8 -*-

# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2018.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Tests XY4 DD Pass"""

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager
from qiskit.transpiler.passmanager_config import PassManagerConfig
from qiskit.transpiler.passes import XY4Pass
from qiskit.test import QiskitTestCase
from qiskit.test.mock import FakeAlmaden

from math import pi


class TestXY4(QiskitTestCase):
    """Test the XY4 DD pass."""

    def test_xy4(self):
        """Test the XY4 DD pass.

        It should replace large enough delay blocks with XY4 DD sequences.
        """
        backend = FakeAlmaden()

        circuit = QuantumCircuit(1)
        circuit.h(0)
        circuit.delay(2000)
        circuit.h(0)

        dt_in_sec = backend.configuration().dt
        backend_prop = backend.properties()
        pass_manager = PassManager()
        pass_manager.append(XY4Pass(backend_prop, dt_in_sec))
        actual = pass_manager.run(circuit)
        
        expected = QuantumCircuit(1)
        expected.h(0)
        expected.delay(247, 0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(45, 0)
        expected.x(0)
        expected.delay(45, 0)
        expected.y(0)
        expected.delay(293, 0)
        expected.h(0)

        self.assertEqual(actual, expected)
