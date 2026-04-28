def compute_discount(total, is_member, has_coupon):
    if total >= 200:
        if is_member:
            if has_coupon:
                return 15
            return 20
        if has_coupon:
            return 10
        return 5

    if total >= 100:
        if is_member and has_coupon:
            return 15
        if is_member:
            return 10
        if has_coupon:
            return 5
        return 0

    return 0
