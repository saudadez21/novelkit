class ParseError(Exception):
    """Generic parsing failure."""


class EmptyContent(ParseError):
    """Indicates that the content is intentionally or meaningfully empty."""


class RestrictedContent(ParseError):
    """Indicates that access is restricted (login/paywall)."""
