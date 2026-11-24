import pytest

from project.books.models import BOOK_STATUSES, BOOK_TYPES, Book


def make_book(**overrides):
    values = {
        'name': 'Władca Pierścieni',
        'author': 'J.R.R. Tolkien',
        'year_published': 1954,
        'book_type': BOOK_TYPES[0],
        'status': BOOK_STATUSES[0],
    }
    values.update(overrides)
    return Book(**values)


def test_book_accepts_valid_values():
    book = make_book()

    assert book.name == 'Władca Pierścieni'
    assert book.author == 'J.R.R. Tolkien'
    assert book.year_published == 1954
    assert book.book_type == BOOK_TYPES[0]
    assert book.status == BOOK_STATUSES[0]


@pytest.mark.parametrize(
    'field',
    ('name', 'author', 'year_published', 'book_type', 'status'),
)
@pytest.mark.parametrize(
    'payload',
    (
        '<script>alert(1)</script>',
        '<img src=x onerror=alert(1)>',
    ),
)
def test_book_rejects_xss_input(field, payload):
    with pytest.raises(ValueError):
        make_book(**{field: payload})
