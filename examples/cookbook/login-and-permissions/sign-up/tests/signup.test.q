<q:test name="the account keeps a bcrypt hash, not the password" page="/">
  <test:submit action="register" name="Bia" email="bia@example.com" password="a long passphrase" />
  <test:expect redirect="/" flash="Account created for Bia." />
  <test:expect table="users" count="1" where="email = 'bia@example.com' AND password_hash LIKE '$2b$%'" />
  <test:expect table="users" count="0" where="password_hash = 'a long passphrase'" />
</q:test>

<q:test name="a short password is refused on its field" page="/">
  <test:submit action="register" name="Bia" email="bia@example.com" password="short" />
  <test:expect error="password" message="Must be at least 12 characters" />
  <test:expect table="users" count="0" />
</q:test>

<q:test name="an address that already has an account is refused" page="/">
  <test:given table="users" email="bia@example.com" name="Bia" password_hash="x" />
  <test:submit action="register" name="Bia Again" email="bia@example.com" password="a long passphrase" />
  <test:expect redirect="/" flash="There is already an account for bia@example.com." />
  <test:expect table="users" count="1" />
</q:test>
