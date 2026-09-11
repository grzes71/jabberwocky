import pytest
from labirynt_studio.io.objects_loader import ObjectsLibrary
from labirynt_studio.model.models import Project, Screen, ObjectInstance, Labyrinth
from labirynt_studio.validation.validator import ProjectValidator


@pytest.fixture
def objects_lib():
    lib = ObjectsLibrary()
    lib.load("world/objects.yaml")
    return lib


def test_validator_detects_out_of_bounds(objects_lib):
    validator = ProjectValidator(objects_lib)

    # TREE_2 (code 4) ma rozmiar 2x2.
    # Jeśli umieścimy go na y=10, to y+h = 12 > 11 -> przekroczenie!
    screen = Screen(id="TEST_OOB", objects=[
        ObjectInstance(code=4, x=38, y=10)
    ])
    issues = validator.validate_screen(screen)
    assert any("wychodzi poza granice" in i.message for i in issues)

    # Jeśli x=38, y=8 -> x+w=40 <= 40, y+h=10 <= 11 -> mieści się!
    screen_ok = Screen(id="TEST_OK", objects=[
        ObjectInstance(code=4, x=38, y=8)
    ])
    issues_ok = validator.validate_screen(screen_ok)
    assert len([i for i in issues_ok if i.severity == "ERROR"]) == 0


def test_validator_detects_unknown_code(objects_lib):
    validator = ProjectValidator(objects_lib)
    screen = Screen(id="TEST_UNK", objects=[
        ObjectInstance(code=999, x=0, y=0)
    ])
    issues = validator.validate_screen(screen)
    assert any("Nieznany kod" in i.message for i in issues)


def test_validator_detects_duplicate_screens_and_invalid_labyrinth(objects_lib):
    validator = ProjectValidator(objects_lib)
    project = Project(
        screens=[
            Screen(id="SCR_1", objects=[]),
            Screen(id="SCR_1", objects=[]),  # Duplikat!
        ],
        labyrinths=[
            Labyrinth(id="LAB_1", name="Lab 1", screens=["SCR_1", "NON_EXISTENT"])
        ]
    )
    issues = validator.validate_project(project)
    assert any("Zduplikowane ID ekranu" in i.message for i in issues)
    assert any("odwołuje się do nieznanego ekranu 'NON_EXISTENT'" in i.message for i in issues)


def test_validator_detects_blocking_collision(objects_lib):
    validator = ProjectValidator(objects_lib)
    # TREE_2 (code 4) jest blocking=True
    screen = Screen(id="TEST_COLL", objects=[
        ObjectInstance(code=4, x=4, y=4),
        ObjectInstance(code=4, x=4, y=4),  # Ta sama pozycja!
    ])
    issues = validator.validate_screen(screen)
    assert any("Kolizja obiektów blokujących" in i.message for i in issues)
