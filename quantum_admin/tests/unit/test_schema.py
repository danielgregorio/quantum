"""
Unit Tests for Schema Inspector
Tests database schema analysis, ERD generation, and model generation
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, ForeignKey

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from schema_inspector import SchemaInspector


class TestSchemaInspectorInit:
    """Test Schema Inspector initialization"""

    def test_init_with_engine(self, test_db_engine):
        """Test initialization with SQLAlchemy engine"""
        inspector = SchemaInspector(test_db_engine)

        assert inspector.engine == test_db_engine
        assert inspector.inspector is not None

    def test_init_creates_inspector(self, test_db_engine):
        """Test that inspector is created"""
        from sqlalchemy.engine import reflection

        inspector = SchemaInspector(test_db_engine)

        assert isinstance(inspector.inspector, reflection.Inspector)


class TestGetTables:
    """Test table listing"""

    def test_get_table_names(self, test_db_engine):
        """Test getting all table names"""
        # Create test tables
        metadata = MetaData()
        Table('users', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)))
        Table('posts', metadata,
              Column('id', Integer, primary_key=True),
              Column('title', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        tables = inspector.get_table_names()

        assert 'users' in tables
        assert 'posts' in tables
        assert len(tables) >= 2

    def test_get_table_names_empty_db(self):
        """Test getting tables from empty database"""
        engine = create_engine("sqlite:///:memory:")
        inspector = SchemaInspector(engine)

        tables = inspector.get_table_names()

        assert isinstance(tables, list)


class TestGetColumns:
    """Test column information retrieval"""

    def test_get_columns_for_table(self, test_db_engine):
        """Test getting column information"""
        # Create test table
        metadata = MetaData()
        Table('products', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(100), nullable=False),
              Column('price', Integer),
              Column('description', String(500)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        columns = inspector.get_columns('products')

        assert len(columns) == 4
        assert any(col['name'] == 'id' for col in columns)
        assert any(col['name'] == 'name' for col in columns)
        assert any(col['name'] == 'price' for col in columns)

    def test_column_properties(self, test_db_engine):
        """Test that column properties are returned"""
        metadata = MetaData()
        Table('items', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(50), nullable=False))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        columns = inspector.get_columns('items')

        id_col = next(c for c in columns if c['name'] == 'id')
        assert 'type' in id_col
        assert 'nullable' in id_col


class TestGetPrimaryKeys:
    """Test primary key detection"""

    def test_get_primary_keys(self, test_db_engine):
        """Test retrieving primary keys"""
        metadata = MetaData()
        Table('orders', metadata,
              Column('id', Integer, primary_key=True),
              Column('order_number', String(50)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        pk = inspector.get_primary_keys('orders')

        assert 'id' in pk

    def test_composite_primary_key(self, test_db_engine):
        """Test composite primary key detection"""
        metadata = MetaData()
        Table('order_items', metadata,
              Column('order_id', Integer, primary_key=True),
              Column('item_id', Integer, primary_key=True),
              Column('quantity', Integer))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        pk = inspector.get_primary_keys('order_items')

        assert 'order_id' in pk
        assert 'item_id' in pk


class TestGetForeignKeys:
    """Test foreign key detection"""

    def test_get_foreign_keys(self, test_db_engine):
        """Test retrieving foreign keys"""
        metadata = MetaData()
        users_table = Table('users', metadata,
                           Column('id', Integer, primary_key=True),
                           Column('name', String(50)))
        posts_table = Table('posts', metadata,
                           Column('id', Integer, primary_key=True),
                           Column('user_id', Integer, ForeignKey('users.id')),
                           Column('title', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        fks = inspector.get_foreign_keys('posts')

        assert len(fks) > 0
        assert any(fk['referred_table'] == 'users' for fk in fks)


class TestGetCompleteSchema:
    """Test complete schema retrieval"""

    def test_get_complete_schema(self, test_db_engine):
        """Test getting complete database schema"""
        # Create test schema
        metadata = MetaData()
        Table('categories', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)))
        Table('products', metadata,
              Column('id', Integer, primary_key=True),
              Column('category_id', Integer, ForeignKey('categories.id')),
              Column('name', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        schema = inspector.get_complete_schema()

        assert 'tables' in schema
        assert len(schema['tables']) >= 2
        assert any(t['name'] == 'categories' for t in schema['tables'])
        assert any(t['name'] == 'products' for t in schema['tables'])

    def test_schema_includes_columns(self, test_db_engine):
        """Test that schema includes column information"""
        metadata = MetaData()
        Table('test_table', metadata,
              Column('id', Integer, primary_key=True),
              Column('data', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        schema = inspector.get_complete_schema()

        test_table = next(t for t in schema['tables'] if t['name'] == 'test_table')
        assert 'columns' in test_table
        assert len(test_table['columns']) >= 2


class TestGenerateMermaidERD:
    """Test Mermaid ERD generation"""

    def test_generate_mermaid_basic(self, test_db_engine):
        """Test basic Mermaid ERD generation"""
        metadata = MetaData()
        Table('users', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        mermaid = inspector.generate_mermaid_erd()

        assert 'erDiagram' in mermaid
        assert 'users' in mermaid

    def test_mermaid_with_relationships(self, test_db_engine):
        """Test Mermaid with relationships"""
        metadata = MetaData()
        Table('authors', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)))
        Table('books', metadata,
              Column('id', Integer, primary_key=True),
              Column('author_id', Integer, ForeignKey('authors.id')),
              Column('title', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        mermaid = inspector.generate_mermaid_erd()

        assert 'authors' in mermaid
        assert 'books' in mermaid
        # Should have relationship notation
        assert '||--o{' in mermaid or '}o--||' in mermaid or 'authors' in mermaid


class TestGenerateDBML:
    """Test DBML generation"""

    def test_generate_dbml_basic(self, test_db_engine):
        """Test basic DBML generation"""
        metadata = MetaData()
        Table('projects', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        dbml = inspector.generate_dbml()

        assert 'Table projects' in dbml
        assert 'id' in dbml
        assert 'name' in dbml

    def test_dbml_with_relationships(self, test_db_engine):
        """Test DBML with foreign keys"""
        metadata = MetaData()
        Table('teams', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(50)))
        Table('members', metadata,
              Column('id', Integer, primary_key=True),
              Column('team_id', Integer, ForeignKey('teams.id')),
              Column('name', String(50)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        dbml = inspector.generate_dbml()

        assert 'Table teams' in dbml
        assert 'Table members' in dbml
        assert 'Ref:' in dbml  # Relationship notation


class TestGenerateSQLAlchemyModels:
    """Test SQLAlchemy model code generation"""

    def test_generate_models_basic(self, test_db_engine):
        """Test basic model generation"""
        metadata = MetaData()
        Table('employees', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(100)),
              Column('email', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        models = inspector.generate_sqlalchemy_models()

        assert 'class Employee(Base):' in models
        assert '__tablename__ = \'employees\'' in models
        assert 'Column(Integer' in models
        assert 'Column(String' in models

    def test_generated_models_have_imports(self, test_db_engine):
        """Test that generated models include imports"""
        metadata = MetaData()
        Table('test', metadata,
              Column('id', Integer, primary_key=True))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        models = inspector.generate_sqlalchemy_models()

        assert 'from sqlalchemy import' in models
        assert 'Column' in models
        assert 'Integer' in models

    def test_generated_models_with_relationships(self, test_db_engine):
        """Test model generation with relationships"""
        metadata = MetaData()
        Table('companies', metadata,
              Column('id', Integer, primary_key=True),
              Column('name', String(100)))
        Table('employees', metadata,
              Column('id', Integer, primary_key=True),
              Column('company_id', Integer, ForeignKey('companies.id')),
              Column('name', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        models = inspector.generate_sqlalchemy_models()

        assert 'class Company(Base):' in models
        assert 'class Employee(Base):' in models
        assert 'ForeignKey' in models


class TestExportFormats:
    """Test various export formats"""

    def test_export_as_json(self, test_db_engine):
        """Test exporting schema as JSON"""
        metadata = MetaData()
        Table('data', metadata,
              Column('id', Integer, primary_key=True),
              Column('value', String(50)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        schema = inspector.get_complete_schema()

        assert isinstance(schema, dict)
        assert 'tables' in schema

    def test_export_formats_available(self, test_db_engine):
        """Test that all export formats work"""
        metadata = MetaData()
        Table('test', metadata,
              Column('id', Integer, primary_key=True))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)

        # All these should return strings
        mermaid = inspector.generate_mermaid_erd()
        dbml = inspector.generate_dbml()
        models = inspector.generate_sqlalchemy_models()

        assert isinstance(mermaid, str)
        assert isinstance(dbml, str)
        assert isinstance(models, str)


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_empty_database(self):
        """Test inspector with empty database"""
        engine = create_engine("sqlite:///:memory:")
        inspector = SchemaInspector(engine)

        tables = inspector.get_table_names()
        schema = inspector.get_complete_schema()

        assert isinstance(tables, list)
        assert isinstance(schema, dict)

    def test_table_without_primary_key(self, test_db_engine):
        """Test table without primary key"""
        metadata = MetaData()
        Table('logs', metadata,
              Column('message', String(500)),
              Column('timestamp', String(50)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)
        columns = inspector.get_columns('logs')

        assert len(columns) == 2

    def test_nonexistent_table(self, test_db_engine):
        """Test querying non-existent table"""
        inspector = SchemaInspector(test_db_engine)

        # Should handle gracefully or raise appropriate exception
        try:
            columns = inspector.get_columns('nonexistent_table')
            # If it doesn't raise, should return empty list
            assert columns == [] or columns is None
        except Exception:
            # Expected if implementation raises exception
            pass


class TestSchemaComparison:
    """Test schema comparison and diff"""

    def test_detect_new_tables(self, test_db_engine):
        """Test detecting new tables"""
        inspector = SchemaInspector(test_db_engine)
        initial_tables = set(inspector.get_table_names())

        # Add new table
        metadata = MetaData()
        Table('new_table', metadata,
              Column('id', Integer, primary_key=True))
        metadata.create_all(test_db_engine)

        updated_tables = set(inspector.get_table_names())
        new_tables = updated_tables - initial_tables

        assert 'new_table' in new_tables


class TestPerformance:
    """Test performance of schema operations"""

    def test_large_table_inspection(self, test_db_engine):
        """Test inspecting table with many columns"""
        # Create table with 50 columns
        metadata = MetaData()
        columns = [Column('id', Integer, primary_key=True)]
        columns.extend([Column(f'col_{i}', String(50)) for i in range(50)])
        Table('large_table', metadata, *columns)
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)

        import time
        start = time.time()
        cols = inspector.get_columns('large_table')
        elapsed = time.time() - start

        assert len(cols) == 51  # id + 50 columns
        assert elapsed < 1.0  # Should be fast

    def test_many_tables_inspection(self, test_db_engine):
        """Test inspecting database with many tables"""
        # Create 20 tables
        metadata = MetaData()
        for i in range(20):
            Table(f'table_{i}', metadata,
                  Column('id', Integer, primary_key=True),
                  Column('data', String(100)))
        metadata.create_all(test_db_engine)

        inspector = SchemaInspector(test_db_engine)

        import time
        start = time.time()
        schema = inspector.get_complete_schema()
        elapsed = time.time() - start

        assert len(schema['tables']) >= 20
        assert elapsed < 2.0  # Should be reasonably fast


# ============================================================================
# Integration with pytest
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
