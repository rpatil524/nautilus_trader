# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2020 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------

import sys
import unittest

from nautilus_trader.indicators.hilbert_transform import HilbertTransform


class HilbertTransformTests(unittest.TestCase):

    def setUp(self):
        # Fixture Setup
        self.ht = HilbertTransform()

    def test_name_returns_expected_name(self):
        # Act
        # Assert
        self.assertEqual("HilbertTransform", self.ht.name)

    def test_str_returns_expected_string(self):
        # Act
        # Assert
        self.assertEqual("HilbertTransform(7)", str(self.ht))
        self.assertEqual("HilbertTransform(7)", repr(self.ht))

    def test_period_returns_expected_value(self):
        # Act
        # Assert
        self.assertEqual(7, self.ht.period)

    def test_initialized_without_inputs_returns_false(self):
        # Act
        # Assert
        self.assertEqual(False, self.ht.initialized)

    def test_initialized_with_required_inputs_returns_true(self):
        # Act
        for _i in range(10):
            self.ht.update_raw(1.00000)

        # Assert
        self.assertEqual(True, self.ht.initialized)

    def test_value_with_no_inputs_returns_none(self):
        # Act
        # Assert
        self.assertEqual(0.0, self.ht.value_in_phase)
        self.assertEqual(0.0, self.ht.value_quad)

    def test_value_with_epsilon_inputs_returns_expected_value(self):
        # Arrange
        for _i in range(100):
            self.ht.update_raw(sys.float_info.epsilon)

        # Act
        # Assert
        self.assertEqual(0.0, self.ht.value_in_phase)
        self.assertEqual(0.0, self.ht.value_quad)

    def test_value_with_ones_inputs_returns_expected_value(self):
        # Arrange
        for _i in range(100):
            self.ht.update_raw(1.00000)

        # Act
        # Assert
        self.assertEqual(0.0, self.ht.value_in_phase)
        self.assertEqual(0.0, self.ht.value_quad)

    def test_value_with_seven_inputs_returns_expected_value(self):
        # Arrange
        high = 1.00010
        low = 1.00000

        # Act
        for _i in range(9):
            high += 0.00010
            low += 0.00010
            self.ht.update_raw((high + low) / 2)

        # Assert
        self.assertEqual(0.0, self.ht.value_in_phase)
        self.assertEqual(0.0, self.ht.value_quad)

    def test_value_with_close_on_high_returns_expected_value(self):
        # Arrange
        high = 1.00010
        low = 1.00000

        # Act
        for _i in range(1000):
            high += 0.00010
            low += 0.00010
            self.ht.update_raw((high + low) / 2)

        # Assert
        self.assertEqual(0.001327272727272581, self.ht.value_in_phase)
        self.assertEqual(0.0005999999999999338, self.ht.value_quad)

    def test_value_with_close_on_low_returns_expected_value(self):
        # Arrange
        high = 1.00010
        low = 1.00000

        # Act
        for _i in range(1000):
            high -= 0.00010
            low -= 0.00010
            self.ht.update_raw((high + low) / 2)

        # Assert
        self.assertEqual(-0.001327272727272581, self.ht.value_in_phase)
        self.assertEqual(-0.0005999999999999338, self.ht.value_quad)

    def test_reset_successfully_returns_indicator_to_fresh_state(self):
        # Arrange
        for _i in range(1000):
            self.ht.update_raw(1.00000)

        # Act
        self.ht.reset()

        # Assert
        self.assertEqual(0., self.ht.value_in_phase)  # No assertion errors.
        self.assertEqual(0., self.ht.value_quad)
