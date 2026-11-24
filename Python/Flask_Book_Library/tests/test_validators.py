import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'project'))

from validators import (
    ValidationError,
    validate_book_title,
    validate_choice,
    validate_city,
    validate_int,
    validate_person_name,
    validate_year,
)


class ValidateTextTests(unittest.TestCase):
    def test_person_name_strips_surrounding_whitespace(self):
        self.assertEqual(validate_person_name('  Ada Lovelace  '), 'Ada Lovelace')

    def test_book_title_strips_surrounding_whitespace(self):
        self.assertEqual(validate_book_title('  A Book  '), 'A Book')

    def test_city_strips_surrounding_whitespace(self):
        self.assertEqual(validate_city('  London  '), 'London')

    def test_custom_field_label_is_used_in_error(self):
        with self.assertRaisesRegex(ValidationError, 'Customer name cannot be empty'):
            validate_person_name('  ', 'Customer name')

    def test_rejects_non_text_values(self):
        for validator in (validate_person_name, validate_book_title, validate_city):
            with self.subTest(validator=validator.__name__):
                with self.assertRaises(ValidationError):
                    validator(123)

    def test_rejects_text_longer_than_64_characters(self):
        for validator in (validate_person_name, validate_book_title, validate_city):
            with self.subTest(validator=validator.__name__):
                with self.assertRaisesRegex(ValidationError, '64 characters'):
                    validator('a' * 65)

    def test_accepts_text_of_64_characters(self):
        value = 'a' * 64
        self.assertEqual(validate_person_name(value), value)


class ValidateIntTests(unittest.TestCase):
    def test_accepts_integer(self):
        self.assertEqual(validate_int(42, 'Age', 1, 120), 42)

    def test_converts_integer_string(self):
        self.assertEqual(validate_int('  +42  ', 'Age', 1, 120), 42)

    def test_accepts_minimum_and_maximum(self):
        self.assertEqual(validate_int(1, 'Age', 1, 120), 1)
        self.assertEqual(validate_int(120, 'Age', 1, 120), 120)

    def test_rejects_values_outside_range(self):
        for value in (0, 121):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValidationError, 'between 1 and 120'):
                    validate_int(value, 'Age', 1, 120)

    def test_rejects_non_integer_values(self):
        for value in (True, False, 1.5, '1.5', 'not a number', None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValidationError, 'must be an integer'):
                    validate_int(value, 'Age', 1, 120)


class ValidateYearTests(unittest.TestCase):
    def test_accepts_first_and_current_year(self):
        self.assertEqual(validate_year(1), 1)
        self.assertEqual(validate_year(date.today().year), date.today().year)

    def test_rejects_year_before_year_one(self):
        with self.assertRaisesRegex(ValidationError, 'between 1 and'):
            validate_year(0)

    def test_rejects_future_year(self):
        with self.assertRaisesRegex(ValidationError, 'between 1 and'):
            validate_year(date.today().year + 1)

    def test_uses_custom_field_label(self):
        with self.assertRaisesRegex(ValidationError, 'Year published must be an integer'):
            validate_year('invalid', 'Year published')


class ValidateChoiceTests(unittest.TestCase):
    def setUp(self):
        self.choices = ('2days', '5days', '10days')

    def test_accepts_choice_and_strips_whitespace(self):
        self.assertEqual(
            validate_choice('  5days  ', 'Book type', self.choices),
            '5days',
        )

    def test_rejects_value_not_in_choices(self):
        with self.assertRaisesRegex(ValidationError, 'Book type must be one of'):
            validate_choice('1day', 'Book type', self.choices)

    def test_rejects_non_text_value(self):
        with self.assertRaises(ValidationError):
            validate_choice(5, 'Book type', self.choices)


if __name__ == '__main__':
    unittest.main()
