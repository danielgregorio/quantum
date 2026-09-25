CREATE TABLE posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL
);

-- 23 posts: "Post 1" … "Post 23".
WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 23)
INSERT INTO posts (title) SELECT 'Post ' || i FROM n;
