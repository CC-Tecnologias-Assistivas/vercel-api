class PayloadApiError(Exception):
    pass


class PayloadTooLargeError(PayloadApiError):
    pass


class InvalidPayloadError(PayloadApiError):
    pass


class PayloadNotFoundError(PayloadApiError):
    pass
