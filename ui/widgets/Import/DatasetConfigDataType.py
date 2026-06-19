from typing import TypedDict

class DatasetConfigData(TypedDict):
    """Data structure configuration definition mapping local tracking properties for datasets.

    Attributes:
        path (str):
            The absolute or relative system disk directory location pointing to the media asset folder.
        name (str):
            The custom alphanumeric tracking designation tag tracking the dataset collection.
        status (bool):
            Activation flag defining the processing eligibility state of the dataset.

    """
    path: str
    name: str
    status: bool