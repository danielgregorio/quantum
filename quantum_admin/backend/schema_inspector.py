"""
Quantum Admin - Database Schema Inspector
Analyzes database structure and generates visual representations
"""

from typing import Dict, List, Any, Optional
from sqlalchemy import inspect, MetaData, Table, Column
from sqlalchemy.engine import Engine
from sqlalchemy.types import (
    Integer, String, Text, Boolean, DateTime, Date, Time,
    Float, Numeric, DECIMAL, SmallInteger, BigInteger,
    JSON, ARRAY
)
import json


class SchemaInspector:
    """Inspect database schema and extract metadata"""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.inspector = inspect(engine)
        self.metadata = MetaData()
        self.metadata.reflect(bind=engine)

    def get_all_tables(self) -> List[str]:
        """Get list of all table names"""
        return self.inspector.get_table_names()

    def get_table_info(self, table_name: str) -> Dict[str, Any]:
        """Get detailed information about a table"""
        columns = self.inspector.get_columns(table_name)
        pk_constraint = self.inspector.get_pk_constraint(table_name)
        foreign_keys = self.inspector.get_foreign_keys(table_name)
        indexes = self.inspector.get_indexes(table_name)
        unique_constraints = self.inspector.get_unique_constraints(table_name)

        return {
            "name": table_name,
            "columns": columns,
            "primary_key": pk_constraint,
            "foreign_keys": foreign_keys,
            "indexes": indexes,
            "unique_constraints": unique_constraints
        }

    def get_complete_schema(self) -> Dict[str, Any]:
        """Get complete database schema"""
        tables = {}

        for table_name in self.get_all_tables():
            tables[table_name] = self.get_table_info(table_name)

        return {
            "tables": tables,
            "table_count": len(tables),
            "database_type": self.engine.dialect.name
        }

    def get_relationships(self) -> List[Dict[str, Any]]:
        """Extract all relationships between tables"""
        relationships = []

        for table_name in self.get_all_tables():
            foreign_keys = self.inspector.get_foreign_keys(table_name)

            for fk in foreign_keys:
                relationships.append({
                    "from_table": table_name,
                    "to_table": fk["referred_table"],
                    "from_columns": fk["constrained_columns"],
                    "to_columns": fk["referred_columns"],
                    "constraint_name": fk.get("name")
                })

        return relationships

    def generate_mermaid_erd(self) -> str:
        """Generate Mermaid ER Diagram syntax"""
        schema = self.get_complete_schema()

        mermaid = ["erDiagram"]

        # Add tables and columns
        for table_name, table_info in schema["tables"].items():
            # Table definition
            for column in table_info["columns"]:
                col_type = self._get_simple_type(column["type"])
                pk_marker = "PK" if column["name"] in table_info["primary_key"].get("constrained_columns", []) else ""
                nullable = "" if column["nullable"] else "NOT NULL"

                mermaid.append(f"    {table_name} {{")
                mermaid.append(f"        {col_type} {column['name']} {pk_marker} {nullable}")
                mermaid.append(f"    }}")

        # Add relationships
        relationships = self.get_relationships()
        for rel in relationships:
            # Mermaid relationship syntax: Table1 ||--o{ Table2 : "relationship"
            mermaid.append(
                f"    {rel['from_table']} }}o--|| {rel['to_table']} : \"{rel['constraint_name'] or 'references'}\""
            )

        return "\n".join(mermaid)

    def generate_dbml(self) -> str:
        """Generate DBML (Database Markup Language) for dbdiagram.io"""
        schema = self.get_complete_schema()

        dbml = []

        # Add tables
        for table_name, table_info in schema["tables"].items():
            dbml.append(f"Table {table_name} {{")

            for column in table_info["columns"]:
                col_type = self._get_simple_type(column["type"])

                # Build column attributes
                attrs = []
                if column["name"] in table_info["primary_key"].get("constrained_columns", []):
                    attrs.append("pk")
                if not column["nullable"]:
                    attrs.append("not null")
                if column.get("default"):
                    attrs.append(f"default: {column['default']}")

                attr_str = f" [{', '.join(attrs)}]" if attrs else ""
                dbml.append(f"  {column['name']} {col_type}{attr_str}")

            dbml.append("}\n")

        # Add relationships
        relationships = self.get_relationships()
        for rel in relationships:
            from_cols = ", ".join(rel["from_columns"])
            to_cols = ", ".join(rel["to_columns"])
            dbml.append(f"Ref: {rel['from_table']}.{from_cols} > {rel['to_table']}.{to_cols}")

        return "\n".join(dbml)

    def generate_graphviz_dot(self) -> str:
        """Generate Graphviz DOT format for ERD"""
        schema = self.get_complete_schema()

        dot = ["digraph ERD {"]
        dot.append("  rankdir=LR;")
        dot.append("  node [shape=record];")

        # Add tables as nodes
        for table_name, table_info in schema["tables"].items():
            columns = []
            for column in table_info["columns"]:
                col_type = self._get_simple_type(column["type"])
                pk_marker = "🔑 " if column["name"] in table_info["primary_key"].get("constrained_columns", []) else ""
                columns.append(f"{pk_marker}{column['name']}: {col_type}")

            label = f"{table_name}|" + "|".join(columns)
            dot.append(f'  {table_name} [label="{{{label}}}"];')

        # Add relationships as edges
        relationships = self.get_relationships()
        for rel in relationships:
            dot.append(f'  {rel["from_table"]} -> {rel["to_table"]};')

        dot.append("}")
        return "\n".join(dot)

    def generate_json_schema(self) -> str:
        """Generate JSON representation of schema"""
        schema = self.get_complete_schema()

        # Convert types to strings for JSON serialization
        for table_name, table_info in schema["tables"].items():
            for column in table_info["columns"]:
                column["type"] = str(column["type"])

        return json.dumps(schema, indent=2)

    def generate_sqlalchemy_models(self) -> str:
        """Generate SQLAlchemy model classes from database schema"""
        schema = self.get_complete_schema()

        models = [
            '"""',
            'Auto-generated SQLAlchemy models',
            'Generated by Quantum Admin Schema Inspector',
            '"""',
            '',
            'from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON',
            'from sqlalchemy.orm import relationship',
            'from sqlalchemy.ext.declarative import declarative_base',
            '',
            'Base = declarative_base()',
            ''
        ]

        for table_name, table_info in schema["tables"].items():
            # Convert to PascalCase for class name
            class_name = self._to_pascal_case(table_name)

            models.append(f'class {class_name}(Base):')
            models.append(f'    """Model for {table_name} table"""')
            models.append(f'    __tablename__ = "{table_name}"')
            models.append('')

            # Add columns
            for column in table_info["columns"]:
                col_def = self._generate_column_definition(column, table_info)
                models.append(f'    {col_def}')

            # Add relationships
            for fk in table_info["foreign_keys"]:
                ref_table = fk["referred_table"]
                ref_class = self._to_pascal_case(ref_table)
                rel_name = ref_table  # Could be more sophisticated

                models.append(f'    {rel_name} = relationship("{ref_class}", back_populates="{table_name}")')

            models.append('')

        return '\n'.join(models)

    def _get_simple_type(self, sql_type) -> str:
        """Convert SQLAlchemy type to simple string"""
        type_str = str(sql_type)

        # Map to simple types
        type_mapping = {
            'INTEGER': 'int',
            'VARCHAR': 'string',
            'TEXT': 'text',
            'BOOLEAN': 'boolean',
            'DATETIME': 'datetime',
            'DATE': 'date',
            'TIME': 'time',
            'FLOAT': 'float',
            'NUMERIC': 'decimal',
            'JSON': 'json'
        }

        for sql_type_name, simple_name in type_mapping.items():
            if sql_type_name in type_str.upper():
                return simple_name

        return type_str.lower()

    def _to_pascal_case(self, snake_str: str) -> str:
        """Convert snake_case to PascalCase"""
        return ''.join(word.capitalize() for word in snake_str.split('_'))

    def _generate_column_definition(self, column: Dict, table_info: Dict) -> str:
        """Generate SQLAlchemy column definition"""
        col_name = column["name"]
        col_type = self._map_to_sqlalchemy_type(column["type"])

        # Check if primary key
        is_pk = col_name in table_info["primary_key"].get("constrained_columns", [])

        # Build column definition
        parts = [col_name, "=", "Column("]

        # Add type
        parts.append(col_type)

        # Add constraints
        if is_pk:
            parts.append(", primary_key=True")

        if not column["nullable"]:
            parts.append(", nullable=False")

        if column.get("default"):
            parts.append(f", default={column['default']}")

        # Check for foreign keys
        for fk in table_info["foreign_keys"]:
            if col_name in fk["constrained_columns"]:
                ref_table = fk["referred_table"]
                ref_col = fk["referred_columns"][0]
                parts.append(f", ForeignKey('{ref_table}.{ref_col}')")

        parts.append(")")

        return ''.join(parts)

    def _map_to_sqlalchemy_type(self, sql_type) -> str:
        """Map SQL type to SQLAlchemy type"""
        type_str = str(sql_type).upper()

        if 'INT' in type_str:
            return 'Integer'
        elif 'VARCHAR' in type_str or 'CHAR' in type_str:
            return 'String'
        elif 'TEXT' in type_str:
            return 'Text'
        elif 'BOOL' in type_str:
            return 'Boolean'
        elif 'DATETIME' in type_str or 'TIMESTAMP' in type_str:
            return 'DateTime'
        elif 'DATE' in type_str:
            return 'DateTime'
        elif 'FLOAT' in type_str or 'DOUBLE' in type_str:
            return 'Float'
        elif 'JSON' in type_str:
            return 'JSON'
        else:
            return 'String'


# ============================================================================
# Utility Functions
# ============================================================================

def inspect_database(connection_string: str) -> SchemaInspector:
    """Create schema inspector from connection string"""
    from sqlalchemy import create_engine
    engine = create_engine(connection_string)
    return SchemaInspector(engine)


def export_schema(inspector: SchemaInspector, format: str = "json") -> str:
    """Export schema in various formats"""
    formats = {
        "json": inspector.generate_json_schema,
        "mermaid": inspector.generate_mermaid_erd,
        "dbml": inspector.generate_dbml,
        "dot": inspector.generate_graphviz_dot,
        "models": inspector.generate_sqlalchemy_models
    }

    if format not in formats:
        raise ValueError(f"Unknown format: {format}. Available: {', '.join(formats.keys())}")

    return formats[format]()
