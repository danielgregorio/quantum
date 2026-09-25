-- Rows that already exist get the default.
ALTER TABLE products ADD COLUMN stock INTEGER NOT NULL DEFAULT 0;

UPDATE products SET stock = 12 WHERE name = 'Mug';
