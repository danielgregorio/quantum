CREATE TABLE faq (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
);

INSERT INTO faq (question, answer) VALUES
    ('Can I change my password?', 'Passwords are changed on the Account page, under Security.'),
    ('How do I export my invoices?', 'Invoices are exported as PDF from the Billing page, one per month.'),
    ('Is there a mobile app?', 'There is no mobile app; the site works on phones.');
