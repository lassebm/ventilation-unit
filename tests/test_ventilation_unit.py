import argparse
import unittest

import ventilation_unit as vu


class RegisterParsingTest(unittest.TestCase):
    def test_known_register_name(self):
        register = vu.parse_register("humidity_boost_threshold")

        self.assertEqual(register.addr, 0x72)
        self.assertTrue(register.readable)
        self.assertTrue(register.writable)

    def test_unknown_register_requires_force(self):
        register = vu.parse_register("0x99")

        self.assertEqual(register.addr, 0x99)
        self.assertEqual(register.access, "?")
        self.assertFalse(register.readable)
        self.assertFalse(register.writable)
        self.assertTrue(register.force_required)

    def test_parse_number_rejects_non_finite_values(self):
        with self.assertRaisesRegex(argparse.ArgumentTypeError, "finite"):
            vu.parse_number("nan")


class WriteValueTest(unittest.TestCase):
    def test_setpoint_write_uses_percent_by_default(self):
        register = vu.REGISTER_BY_ADDR[0x11]

        self.assertEqual(
            vu.coerce_write_value(register, 40, force=False, raw=False),
            400,
        )
        self.assertEqual(
            vu.coerce_write_value(register, 40.5, force=False, raw=False),
            405,
        )

        with self.assertRaisesRegex(vu.VentError, "<= 100"):
            vu.coerce_write_value(register, 100.1, force=False, raw=False)

        with self.assertRaisesRegex(vu.VentError, "fractional raw"):
            vu.coerce_write_value(register, 40.55, force=True, raw=False)

        self.assertEqual(
            vu.coerce_write_value(register, 1001, force=True, raw=True),
            1001,
        )

    def test_filter_interval_is_written_as_hours_by_default(self):
        register = vu.REGISTER_BY_ADDR[0x55]

        self.assertEqual(
            vu.coerce_write_value(register, 9999, force=False, raw=False),
            59994,
        )

        with self.assertRaisesRegex(vu.VentError, ">= 1 hours"):
            vu.coerce_write_value(register, 0, force=False, raw=False)

    def test_raw_filter_interval_value_is_bounded(self):
        register = vu.REGISTER_BY_ADDR[0x55]

        self.assertEqual(
            vu.coerce_write_value(register, 600, force=False, raw=True),
            600,
        )
        with self.assertRaisesRegex(vu.VentError, ">= 6"):
            vu.coerce_write_value(register, 0, force=False, raw=True)

    def test_integer_human_register_rejects_fractional_values(self):
        register = vu.REGISTER_BY_ADDR[0x72]

        with self.assertRaisesRegex(vu.VentError, "must be an integer"):
            vu.coerce_write_value(register, 50.5, force=False, raw=False)

    def test_unknown_register_write_requires_force(self):
        register = vu.parse_register("0x99")

        with self.assertRaisesRegex(vu.VentError, "--raw"):
            vu.coerce_write_value(register, 1, force=True, raw=False)

        with self.assertRaisesRegex(vu.VentError, "--force"):
            vu.coerce_write_value(register, 1, force=False, raw=True)

        self.assertEqual(
            vu.coerce_write_value(register, 1, force=True, raw=True),
            1,
        )


class DecodeValueTest(unittest.TestCase):
    def test_humidity_input_decodes_like_official_app(self):
        decoded = vu.decode_value(0x50, 333, ppr=1)

        self.assertAlmostEqual(decoded["voltage"], 1.0)
        self.assertAlmostEqual(decoded["humidity_percent"], 333 / 33)

    def test_rpm_honors_ppr(self):
        decoded = vu.decode_value(0x40, 50, ppr=2)

        self.assertEqual(decoded["rpm"], 1500)


if __name__ == "__main__":
    unittest.main()
