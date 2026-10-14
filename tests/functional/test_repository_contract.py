from inspect import isabstract

from townplanning.modules.regulations.repositories import (
    RegulationRepository,
)


def test_repository_contract():

    assert isabstract(RegulationRepository)

    methods = {

        "save",

        "get",

        "get_by_number",

        "list",

        "delete",

    }

    implemented = {

        name

        for name in RegulationRepository.__dict__

        if callable(RegulationRepository.__dict__[name])

    }

    assert methods.issubset(implemented)