from decimal import Decimal, ROUND_HALF_UP

def half_round(number):
    decimal_number = Decimal(number)
    rounded_number = decimal_number.quantize(Decimal('1'), rounding=ROUND_HALF_UP)
    return int(rounded_number)