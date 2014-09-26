# -*- coding: utf8 -*-

__all__ = ['is_valid', 'generate']


def is_valid(number):
    return checksum(number) == 0


def generate(number):
    check_digit = checksum(int(number) * 10)
    check_digit = 0 if check_digit == 0 else 10 - check_digit
    return int(number) * 10 + check_digit


def checksum(number):
    summed = 0
    even = False
    for digit in reversed(digits_of(number)):
        summed += sum(digits_of(digit * 2)) if even else digit
        even = not even
    return summed % 10


def digits_of(number):
    return [int(d) for d in str(number)]


if __name__ == '__main__':
    n = 1234567897854949393
    
    print '{} / {} / {}'.format(
        n,
        generate(n),
        is_valid(generate(n)),
    )
