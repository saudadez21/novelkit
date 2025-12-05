from dataclasses import dataclass
from typing import Literal


@dataclass
class LoginField:
    """Represents a UI-level login field used by site authentication forms.

    Attributes:
        name: Internal field name used for submission.
        label: Human-readable field label displayed to the user.
        type: Field input type ("text", "password", or "cookie").
        required: Whether the field must be provided for login.
        default: Optional default value.
        placeholder: Placeholder text displayed in UI fields.
        description: Additional descriptive text for the field.
    """

    name: str
    label: str
    type: Literal["text", "password", "cookie"]
    required: bool
    default: str = ""
    placeholder: str = ""
    description: str = ""
