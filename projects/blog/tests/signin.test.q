<!-- The sign-in form, through the real actions: the first visit creates the
     admin account (its password is hashed), then the account signs in. -->

<q:test name="the first visit creates the admin once" page="/login">
  <test:visit />
  <test:expect text="Create the admin account" />
  <test:submit action="setup" username="ana" display_name="Ana"
               password="a-long-test-password" password2="a-long-test-password" />
  <test:expect redirect="/login" flash="Account created. Sign in." />
  <test:expect table="users" count="1" where="username = 'ana' AND password_hash LIKE '$2%'" />
  <test:expect no-text="Create the admin account" />
  <!-- once a user exists, the action refuses a second one -->
  <test:submit action="setup" username="eve" display_name="Eve"
               password="a-long-test-password" password2="a-long-test-password" />
  <test:expect flash="The blog already has an admin." />
  <test:expect table="users" count="1" />
</q:test>

<q:test name="the passwords must match" page="/login">
  <test:submit action="setup" username="ana" display_name="Ana"
               password="a-long-test-password" password2="another-long-password" />
  <test:expect flash="The passwords do not match." />
  <test:expect table="users" count="0" />
</q:test>

<q:test name="sign in, and a wrong password does not get in" page="/login">
  <test:submit action="setup" username="ana" display_name="Ana"
               password="a-long-test-password" password2="a-long-test-password" />
  <test:submit action="signIn" username="ana" password="wrong-wrong" />
  <test:expect redirect="/login" flash="Wrong username or password." />
  <test:visit path="/admin" />
  <test:expect redirect="/login" />

  <test:submit action="signIn" username="ana" password="a-long-test-password" />
  <test:expect redirect="/admin" />
  <test:expect text="Signed in as Ana" />
</q:test>

<q:test name="sign out" page="/admin">
  <test:as user="Ana" role="admin" id="1" />
  <test:visit path="/logout" />
  <test:expect redirect="/" />
  <test:expect text="You are signed out" />
  <test:visit path="/admin" />
  <test:expect redirect="/login" />
</q:test>
