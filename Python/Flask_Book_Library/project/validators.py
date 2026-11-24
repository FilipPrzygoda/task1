import re
from datetime import date


class ValidationError(ValueError):
    """Raised when a value fails model validation."""


def _validate_text(value, field, max_length=64):
    if not isinstance(value, str):
        raise ValidationError(f'{field} must be text')

    value = value.strip()
    if not value:
        raise ValidationError(f'{field} cannot be empty')
    if '<' in value or '>' in value:
        raise ValidationError('Input contains invalid characters.')
    if len(value) > max_length:
        raise ValidationError(
            f'{field} cannot be longer than {max_length} characters'
        )

    return value


def validate_person_name(value, field='Name'):
    return _validate_text(value, field)


def validate_book_title(value, field='Book name'):
    return _validate_text(value, field)


def validate_city(value, field='City'):
    return _validate_text(value, field)


def validate_int(value, field, min_value, max_value):
    if isinstance(value, bool):
        raise ValidationError(f'{field} must be an integer')

    if isinstance(value, int):
        parsed_value = value
    elif isinstance(value, str) and re.fullmatch(r'[+-]?\d+', value.strip()):
        parsed_value = int(value.strip())
    else:
        raise ValidationError(f'{field} must be an integer')

    if not min_value <= parsed_value <= max_value:
        raise ValidationError(
            f'{field} must be between {min_value} and {max_value}'
        )

    return parsed_value


def validate_year(value, field='Year'):
    return validate_int(value, field, 1, date.today().year)


def validate_choice(value, field, choices):
    if not isinstance(value, str):
        raise ValidationError(f'{field} must be one of: {", ".join(choices)}')

    value = value.strip()
    if value not in choices:
        raise ValidationError(f'{field} must be one of: {", ".join(choices)}')

    return value
