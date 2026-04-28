from bug import compute_discount


def test_high_value_member_with_coupon_gets_max_discount() -> None:
    assert compute_discount(250, True, True) == 25


def test_high_value_member_without_coupon_keeps_member_discount() -> None:
    assert compute_discount(250, True, False) == 20


def test_mid_value_member_with_coupon_uses_combined_branch() -> None:
    assert compute_discount(150, True, True) == 15
