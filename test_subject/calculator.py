from test_subject.utils import _generate_range


def sum_range(a, b):
    """Returns the sum of all integers from a to b, inclusive."""
    numbers = _generate_range(a, b)
    return sum(numbers)
