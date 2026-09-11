import pytest
from pathlib import Path
from labirynt_studio.model.models import Project, ProjectResources, Screen, ObjectInstance, Labyrinth
from labirynt_studio.io.project_io import save_project_to_yaml, load_project_from_yaml


def test_project_save_and_load(tmp_path):
    proj_path = tmp_path / "test_project.yaml"

    orig_proj = Project(
        name="TestJabberwocky",
        resources=ProjectResources(
            objects="world/objects.yaml",
            colors="world/colors.yaml",
            charset="fonts/game.fnt"
        ),
        screens=[
            Screen(
                id="FOREST_01",
                objects=[
                    ObjectInstance(code=4, x=0, y=0),
                    ObjectInstance(code=3, x=38, y=10)
                ]
            ),
            Screen(
                id="CAVE_01",
                objects=[
                    ObjectInstance(code=5, x=10, y=6)
                ]
            )
        ],
        labyrinths=[
            Labyrinth(id="LEVEL_01", name="Poziom 1", screens=["FOREST_01", "CAVE_01"])
        ]
    )

    # Zapis
    success, err = save_project_to_yaml(orig_proj, proj_path)
    assert success is True
    assert err is None
    assert proj_path.exists()

    # Odczyt
    loaded_proj, err = load_project_from_yaml(proj_path)
    assert err is None
    assert loaded_proj is not None

    assert loaded_proj.name == "TestJabberwocky"
    assert len(loaded_proj.screens) == 2
    assert loaded_proj.screens[0].id == "FOREST_01"
    assert len(loaded_proj.screens[0].objects) == 2
    
    # Weryfikacja współrzędnych i kodów
    obj0 = loaded_proj.screens[0].objects[0]
    assert obj0.code == 4
    assert obj0.x == 0
    assert obj0.y == 0

    obj1 = loaded_proj.screens[0].objects[1]
    assert obj1.code == 3
    assert obj1.x == 38
    assert obj1.y == 10

    assert len(loaded_proj.labyrinths) == 1
    assert loaded_proj.labyrinths[0].id == "LEVEL_01"
    assert loaded_proj.labyrinths[0].name == "Poziom 1"
    assert loaded_proj.labyrinths[0].screens == ["FOREST_01", "CAVE_01"]
