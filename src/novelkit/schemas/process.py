from typing import TypedDict


class ExecutedStageMeta(TypedDict):
    """Metadata describing an executed stage of the processing pipeline.

    Attributes:
        processed_at: ISO 8601 timestamp of when the stage completed.
        depends_on: List of stage names this stage depends on.
        config_hash: Hash representing the configuration used for the stage.
    """

    processed_at: str  # ISO 8601 timestamp
    depends_on: list[str]
    config_hash: str


class PipelineMeta(TypedDict):
    """Metadata describing the execution state of a processing pipeline.

    Attributes:
        pipeline: Ordered list of processing stage names.
        executed: Mapping of executed stage names to their execution metadata.
    """

    pipeline: list[str]
    executed: dict[str, ExecutedStageMeta]
