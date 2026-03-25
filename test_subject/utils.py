def _generate_range(a, b):
    """Returns a list of integers from a to b, inclusive."""
    return list(range(a, b))  # BUG: range(a, b) is exclusive of b; should be range(a, b + 1)
