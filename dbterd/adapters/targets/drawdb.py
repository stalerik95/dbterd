import json
from typing import List, Tuple

from dbterd.adapters import adapter
from dbterd.adapters.meta import Table
from dbterd.types import Catalog, Manifest


def run(manifest: Manifest, catalog: Catalog, **kwargs) -> Tuple[str, str]:
    """Parse dbt artifacts and export DDB file

    Args:
        manifest (dict): Manifest json
        catalog (dict): Catalog json

    Returns:
        Tuple(str, str): File name and the DDB (json) content
    """
    output_file_name = kwargs.get("output_file_name") or "output.ddb"
    return (output_file_name, parse(manifest, catalog, **kwargs))


def parse(manifest: Manifest, catalog: Catalog, **kwargs) -> str:
    """Get the DDB content from dbt artifacts

    Args:
        manifest (dict): Manifest json
        catalog (dict): Catalog json

    Returns:
        str: DDB (json) content
    """

    algo_module = adapter.load_algo(name=kwargs["algo"])
    tables, relationships = algo_module.parse(
        manifest=manifest, catalog=catalog, **kwargs
    )

    # Build DDB content
    graphic_tables = get_graphic_tables(tables=tables)
    drawdb = dict(
        author="dbterd",
        title=kwargs.get("output_file_name") or "Generated by dbterd",
        date=str(manifest.metadata.generated_at),
        tables=[
            dict(
                id=idx,
                name=x.name,
                x=graphic_tables.get(x.name, {}).get("x"),
                y=graphic_tables.get(x.name, {}).get("y"),
                comment=x.description,
                indices=[],
                color="#175e7a",
                fields=[
                    dict(
                        id=idc,
                        name=c.name,
                        type=c.data_type,
                        default="",
                        check="",
                        primary=False,  # TODO
                        unique=False,  # TODO
                        notNull=False,  # TODO
                        increment=False,
                        comment=c.description,
                    )
                    for idc, c in enumerate(x.columns)
                ],
            )
            for idx, x in enumerate(tables)
        ],
        relationships=[
            dict(
                id=idx,
                name=f"fk__{x.table_map[1]}_{x.table_map[0]}__{x.column_map[1]}",
                cardinality=get_rel_symbol(x.type),
                startTableId=graphic_tables.get(x.table_map[1], {}).get("id"),
                endTableId=graphic_tables.get(x.table_map[0], {}).get("id"),
                startFieldId=(
                    graphic_tables.get(x.table_map[1], {})
                    .get("fields")
                    .get(x.column_map[1], {})
                    .get("id")
                ),
                endFieldId=(
                    graphic_tables.get(x.table_map[0], {})
                    .get("fields")
                    .get(x.column_map[0], {})
                    .get("id")
                ),
                updateConstraint="No action",
                deleteConstraint="No action",
            )
            for idx, x in enumerate(relationships)
        ],
        notes=[],
        subjectAreas=[],
        database="generic",
        types=[],
    )

    return json.dumps(drawdb)


def get_y(
    tables: List[Table], idx: int, graphic_tables: dict, column_size: int = 4
) -> float:
    """Get y value of a table

    `y = S x (T's no of columns) + (T's y value if any)`

    - T: the prev table in the same graph column
    - S: the height value of a graphic column, default = 50

    Args:
        tables (List[Table]): Parsed tables
        idx (int): Current table index
        graphic_tables (dict): Mutable caculated graphic tables dict
        column_size (int): Graphic column size, default = 4

    Returns:
        float: y value
    """
    if idx < column_size:
        return 0

    col_len = len(tables[idx - column_size].columns) + 1  # plus title row
    y = (50 * col_len) * int(0 if idx < column_size else 1)

    if idx - column_size >= 0:
        prev_table_name = tables[idx - column_size].name
        y += graphic_tables[prev_table_name].get("y", 0)

    return y


def get_graphic_tables(tables: List[Table]) -> dict:
    """Return the indexed and pre-layouted tables

    Args:
        tables (List[Table]): List of parsed tables

    Returns:
        dict: Indexed and Layouted tables
    """
    graphic_tables = dict()
    for idx, x in enumerate(tables):
        idx_fields = dict()
        graphic_tables[x.name] = dict(
            id=idx,
            x=500 * (idx % 4),
            y=get_y(tables, idx, graphic_tables),
            fields=idx_fields,
        )
        for idc, c in enumerate(x.columns):
            idx_fields[c.name] = dict(id=idc)

    return graphic_tables


def get_rel_symbol(relationship_type: str) -> str:
    """Get DDB relationship symbol

    Args:
        relationship_type (str): relationship type

    Returns:
        str: Relation symbol supported in DDB
    """
    if relationship_type in ["01", "11"]:
        return "One to one"
    if relationship_type in ["0n", "1n"]:
        return "One to many"
    if relationship_type in ["nn"]:
        return "Many to many"
    return "Many to one"  # n1